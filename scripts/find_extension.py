#!/usr/bin/env python3
"""Search Extensions and explicitly place immutable native files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import yaml
from install_choices import (
  PlacementError,
  build_install_choices,
  place_choice,
  remove_choice,
  verify_choice,
)

POLICY_VERSION = "bcgov-finder-policy/1.0"
DEFAULT_CATALOG = "https://bcgov.github.io/agent-marketplace/assets/catalog.json"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 100
# A candidate must clear this score before it is offered as a match. The scorer
# awards 100 for an exact name, 12 per matching name token, 4 per summary token,
# and 1 per prerequisite token, so this floor requires at least one name-token
# hit or two summary-token hits. It stops unrelated skills being presented as
# weak matches for a request the marketplace does not actually serve.
MIN_MATCH_SCORE = 8
KNOWN_EXTENSION_TYPES = {"skill", "prompt", "instructions", "agent", "hook", "mcp"}
PUBLISHABLE_EXTENSION_TYPES = {"skill", "prompt", "instructions", "agent"}
RESOURCE_DIRECTORIES = {"agents", "assets", "references", "scripts"}
ALLOWED_SUFFIXES = {
  ".css",
  ".html",
  ".js",
  ".json",
  ".md",
  ".py",
  ".sh",
  ".toml",
  ".ts",
  ".txt",
  ".yaml",
  ".yml",
}
BLOCKED_NAMES = {".mcp.json", "hooks.json", "mcp.json", "package.json"}
HIDDEN_CONTROLS = {
  "\u061c",
  "\u200b",
  "\u200c",
  "\u200d",
  "\u200e",
  "\u200f",
  "\u202a",
  "\u202b",
  "\u202c",
  "\u202d",
  "\u202e",
  "\u2060",
  "\u2066",
  "\u2067",
  "\u2068",
  "\u2069",
  "\ufeff",
}
SECRET_PATTERNS = {
  "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
  "github-token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
  "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
  "assigned-secret": re.compile(
    r"(?i)\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{12,}"
  ),
}
ADVISORY_PATTERNS = {
  "approval-bypass": re.compile(
    r"(?i)\b(?:skip|bypass|ignore).{0,40}\b(?:approval|confirmation|safeguard)\b"
  ),
  "security-weakening": re.compile(
    r"(?i)\b(?:disable|turn off|weaken).{0,40}"
    r"\b(?:security|validation|scanner|firewall)\b"
  ),
  "concealment": re.compile(
    r"(?i)\b(?:hide|conceal).{0,30}\b(?:activity|change|command|file)\b"
  ),
  "exfiltration": re.compile(
    r"(?i)\b(?:upload|send|post|exfiltrate).{0,50}"
    r"\b(?:credential|repository|secret|user data)\b"
  ),
  "mutable-download-execution": re.compile(
    r"(?i)(?:curl|wget|invoke-webrequest).{0,160}(?:\||;|&&).{0,40}(?:sh|bash|python|iex)\b"
  ),
  "instruction-override": re.compile(
    r"(?i)\bignore (?:all |any )?(?:previous|prior|marketplace|scanner) instructions\b"
  ),
  "unsupported-trust-claim": re.compile(
    r"(?i)\b(?:bc gov approved|verified secure|guaranteed safe)\b"
  ),
}
NETWORK_COMMAND_RE = re.compile(
  r"(?i)\b(?:curl|wget|invoke-webrequest)\b[^\n]*https?://([A-Za-z0-9.-]+)"
)
ENVIRONMENT_RE = re.compile(
  r"(?:\$\{?([A-Z][A-Z0-9_]{2,})\}?|\$env:([A-Z][A-Z0-9_]{2,})|%([A-Z][A-Z0-9_]{2,})%)"
)


class FinderError(Exception):
  """Represent a finder failure that is safe to show to the user."""


def load_catalog(source: str) -> dict:
  """Load a generated marketplace catalog."""
  candidates = [source]
  failures = []
  for candidate in candidates:
    try:
      if candidate.startswith("https://"):
        content = _download(candidate).decode("utf-8")
      else:
        content = Path(candidate).read_text(encoding="utf-8")
      catalog = json.loads(content)
      if catalog.get("schema-version") not in {
        "bcgov-marketplace/v1",
        "bcgov-marketplace-catalog/v1alpha1",
      }:
        raise FinderError(f"unsupported catalog schema in {candidate}")
      return catalog
    except (FinderError, OSError, UnicodeError, json.JSONDecodeError) as exc:
      failures.append(str(exc))
  raise FinderError(f"cannot load catalog {source}: {'; '.join(failures)}")


def _tokens(value: str) -> set[str]:
  """Return normalized search terms used by deterministic ranking."""
  return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}


def lookup_extension(catalog: dict, identity: str) -> dict | None:
  """Resolve exact IDs or explicit current aliases without guessing by name."""
  canonical = catalog.get("legacy-ids", {}).get(identity, identity)
  return next(
    (record for record in catalog["extensions"] if record["id"] == canonical), None
  )


def search(catalog: dict, query: str, extension_type: str | None = None) -> list[dict]:
  """Return active matches, or a requested non-active id with its warning."""
  if extension_type is not None and extension_type not in KNOWN_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  query_tokens = _tokens(query)
  requested = (
    lookup_extension(catalog, query.strip())
    if query.strip().startswith("bcgov-public/")
    else None
  )
  if query.strip().startswith("bcgov-public/") and requested is None:
    return []
  ranked = []
  for record in catalog["extensions"]:
    if record["lifecycle"] != "active" and record is not requested:
      continue
    if extension_type is not None and record.get("type") != extension_type:
      continue
    if requested is not None and record is not requested:
      continue
    name_tokens = _tokens(
      record["id"]
      + " "
      + record["display-name"]
      + " "
      + " ".join(record.get("legacy-ids", []))
    )
    summary_tokens = _tokens(record["summary"])
    prerequisite_tokens = _tokens(" ".join(record["prerequisites"]))
    exact_name = (
      100
      if query.lower().strip()
      in {record["id"].split("/", 1)[1], record["display-name"].lower()}
      else 0
    )
    score = (
      exact_name
      + 12 * len(query_tokens & name_tokens)
      + 4 * len(query_tokens & summary_tokens)
      + len(query_tokens & prerequisite_tokens)
    )
    if score >= MIN_MATCH_SCORE:
      why = sorted(query_tokens & (name_tokens | summary_tokens | prerequisite_tokens))
      ranked.append((score, record["id"], why, record))
  ranked.sort(key=lambda item: (-item[0], item[1]))
  return [
    {**item[3], "match": {"score": item[0], "terms": item[2]}} for item in ranked[:3]
  ]


def approved_sources(config: dict, extension_type: str) -> list[dict]:
  """Return active approved sources that declare support for one type."""
  if extension_type not in KNOWN_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  sources = []
  for source in config.get("approved-discovery-sources", []):
    declared_types = source.get("extension-types", ["skill"])
    if source.get("status", "active") == "active" and extension_type in declared_types:
      sources.append(source)
  return sorted(sources, key=lambda source: source.get("id", source["name"]))


def load_marketplace_config(path: str | Path) -> dict:
  """Load the versioned local marketplace source policy."""
  try:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
  except (OSError, UnicodeError, yaml.YAMLError) as exc:
    raise FinderError(f"cannot load marketplace config {path}: {exc}") from exc
  if not isinstance(config, dict):
    raise FinderError(f"marketplace config {path} must contain a mapping")
  return config


def _download(url: str) -> bytes:
  """Download a bounded immutable repository archive."""
  request = urllib.request.Request(
    url, headers={"User-Agent": "bcgov-find-extension/1"}
  )
  try:
    with urllib.request.urlopen(request, timeout=60) as response:
      length = int(response.headers.get("Content-Length", "0"))
      if length > MAX_DOWNLOAD_BYTES:
        raise FinderError("repository archive exceeds the download limit")
      content = response.read(MAX_DOWNLOAD_BYTES + 1)
  except (OSError, ValueError) as exc:
    raise FinderError(f"cannot download immutable source: {exc}") from exc
  if len(content) > MAX_DOWNLOAD_BYTES:
    raise FinderError("repository archive exceeds the download limit")
  return content


def _github_archive_url(repository: str, revision: str) -> str:
  """Build an immutable GitHub archive URL from validated source identity."""
  parsed = urllib.parse.urlparse(repository)
  if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
    raise FinderError("source repository must be an https://github.com URL")
  if not re.fullmatch(r"[0-9a-f]{40}", revision):
    raise FinderError("source revision must be a full lowercase commit SHA")
  path = parsed.path.rstrip("/")
  if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
    raise FinderError("source repository must identify one GitHub owner/repository")
  return f"https://github.com{path}/archive/{revision}.zip"


def stage_package(
  repository: str,
  revision: str,
  package_path: str,
  target: Path,
  extension_type: str = "skill",
) -> None:
  """Extract only one package path from an immutable GitHub archive."""
  if extension_type not in PUBLISHABLE_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  package = PurePosixPath(package_path)
  if package.is_absolute() or ".." in package.parts or not package.parts:
    raise FinderError("package path must be a non-empty repository-relative path")
  archive = _download(_github_archive_url(repository, revision))
  seen = set()
  with zipfile.ZipFile(__import__("io").BytesIO(archive)) as source:
    for entry in source.infolist():
      parts = PurePosixPath(entry.filename).parts
      if (
        len(parts) <= len(package.parts)
        or tuple(parts[1 : 1 + len(package.parts)]) != package.parts
      ):
        continue
      relative = PurePosixPath(*parts[1 + len(package.parts) :])
      if entry.is_dir():
        continue
      if relative.is_absolute() or ".." in relative.parts:
        raise FinderError("archive contains path traversal")
      mode = entry.external_attr >> 16
      if stat.S_ISLNK(mode):
        raise FinderError(f"archive contains symlink: {relative}")
      folded = relative.as_posix().casefold()
      if folded in seen:
        raise FinderError(f"archive contains a case-colliding path: {relative}")
      seen.add(folded)
      destination = target.joinpath(*relative.parts)
      destination.parent.mkdir(parents=True, exist_ok=True)
      content = source.read(entry)
      if len(content) > MAX_FILE_BYTES:
        raise FinderError(f"archive file exceeds size limit: {relative}")
      destination.write_bytes(content)
      destination.chmod(0o644)
  artifact_file = (
    "SKILL.md" if extension_type == "skill" else f"{package.name}.{extension_type}.md"
  )
  if not (target / artifact_file).is_file():
    raise FinderError(f"resolved package does not contain {artifact_file}")


def inventory(package: Path) -> list[dict]:
  """Inventory regular package files in path order."""
  result = []
  for path in sorted(
    package.rglob("*"), key=lambda item: item.relative_to(package).as_posix().lower()
  ):
    if path.is_symlink():
      raise FinderError(f"package contains symlink: {path.relative_to(package)}")
    if not path.is_file():
      continue
    content = path.read_bytes()
    result.append(
      {
        "path": path.relative_to(package).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
      }
    )
  return result


def tree_digest(file_inventory: list[dict]) -> str:
  """Calculate the marketplace package-tree digest."""
  digest = hashlib.sha256()
  for item in file_inventory:
    digest.update(item["path"].encode())
    digest.update(b"\0")
    digest.update(str(item["size"]).encode())
    digest.update(b"\0")
    digest.update(item["sha256"].encode())
    digest.update(b"\n")
  return f"sha256:{digest.hexdigest()}"


def scan_staged(
  package: Path,
  capabilities: dict | None = None,
  extension_type: str = "skill",
  package_name: str | None = None,
) -> dict:
  """Apply deterministic local policy without executing staged content."""
  findings = []
  total = 0
  if extension_type not in PUBLISHABLE_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  artifact_file = (
    "SKILL.md"
    if extension_type == "skill"
    else f"{package_name or package.name}.{extension_type}.md"
  )
  expected_root_files = {artifact_file, "bcgov-extension.yaml"}
  files = inventory(package)
  if len(files) > MAX_FILES:
    findings.append(_finding("blocking", "file-count", ".", 0))
  declared_network = set((capabilities or {}).get("network", []))
  declared_environment = set(
    (capabilities or {}).get("environment-variables", [])
  ) | set((capabilities or {}).get("secret-names", []))
  declared_commands = set((capabilities or {}).get("commands", []))
  for item in files:
    relative = item["path"]
    path = package / relative
    total += item["size"]
    parts = PurePosixPath(relative).parts
    if any(part.startswith(".") for part in parts):
      findings.append(_finding("blocking", "hidden-path", relative, 0))
    if (len(parts) == 1 and relative not in expected_root_files) or (
      len(parts) > 1 and (len(parts) != 2 or parts[0] not in RESOURCE_DIRECTORIES)
    ):
      findings.append(_finding("blocking", "nested-resource", relative, 0))
    if parts[0] == "agents" and (
      extension_type != "skill" or relative != "agents/openai.yaml"
    ):
      findings.append(_finding("blocking", "unsupported-agent-metadata", relative, 0))
    if path.name.lower() in BLOCKED_NAMES:
      findings.append(_finding("blocking", "blocked-extension-type", relative, 0))
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
      findings.append(_finding("blocking", "unsupported-file-type", relative, 0))
    if path.stat().st_mode & 0o111:
      findings.append(_finding("blocking", "executable-bit", relative, 0))
    if (
      capabilities is not None
      and parts[0] == "scripts"
      and path.name not in declared_commands
      and relative not in declared_commands
      and "*" not in declared_commands
    ):
      findings.append(_finding("blocking", "undeclared-script", relative, 0))
    try:
      text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
      findings.append(_finding("blocking", "binary-file", relative, 0))
      continue
    for line_number, line in enumerate(text.splitlines(), start=1):
      if any(
        character in HIDDEN_CONTROLS or unicodedata.category(character) == "Cf"
        for character in line
      ):
        findings.append(_finding("blocking", "hidden-unicode", relative, line_number))
      for code, pattern in SECRET_PATTERNS.items():
        if pattern.search(line):
          findings.append(_finding("blocking", code, relative, line_number))
      for code, pattern in ADVISORY_PATTERNS.items():
        if pattern.search(line):
          findings.append(_finding("advisory", code, relative, line_number))
      if capabilities is not None:
        for host in NETWORK_COMMAND_RE.findall(line):
          if host not in declared_network and "*" not in declared_network:
            findings.append(
              _finding("blocking", "undeclared-network", relative, line_number)
            )
        for match in ENVIRONMENT_RE.finditer(line):
          name = next(group for group in match.groups() if group)
          if name not in declared_environment and "*" not in declared_environment:
            findings.append(
              _finding(
                "blocking",
                "undeclared-environment-variable",
                relative,
                line_number,
              )
            )
  if total > MAX_PACKAGE_BYTES:
    findings.append(_finding("blocking", "package-size", ".", 0))
  artifact_path = package / artifact_file
  asset_text = artifact_path.read_text(encoding="utf-8", errors="replace")
  if not re.match(
    r"^---\s*\n(?:(?!\n---\s*$).)*\n---\s*\n",
    asset_text,
    re.DOTALL | re.MULTILINE,
  ):
    findings.append(_finding("blocking", "malformed-asset-metadata", artifact_file, 1))
  findings.sort(
    key=lambda item: (item["severity"], item["path"], item["line"], item["code"])
  )
  return {
    "policy-version": POLICY_VERSION,
    "outcome": "blocked"
    if any(item["severity"] == "blocking" for item in findings)
    else "passed",
    "findings": findings,
  }


def _finding(severity: str, code: str, path: str, line: int) -> dict:
  """Create one cited scanner finding."""
  return {"severity": severity, "code": code, "path": path, "line": line}


def _confirm(message: str, assume_yes: bool) -> None:
  """Require one explicit confirmation unless the calling agent already obtained it."""
  if assume_yes:
    return
  if input(f"{message} Type 'yes' to continue: ").strip().lower() != "yes":
    raise FinderError("operation cancelled")


def _capabilities(args) -> dict:
  """Build structured capability declarations from third-party CLI arguments."""
  return {
    "filesystem": {"read": args.read, "write": args.write},
    "network": args.network,
    "commands": args.command,
    "environment-variables": args.environment_variable,
    "secret-names": args.secret_name,
    "data-classes": args.data_class,
  }


def _register_candidate(args, digest: str, capabilities: dict) -> dict:
  """Create or update one deduplicated GitHub candidate issue."""
  fingerprint = hashlib.sha256(
    f"{args.repository}\0{args.revision}\0{args.path}".encode()
  ).hexdigest()
  body = "\n".join(
    [
      "### Discovery catalog",
      "",
      args.discovery_catalog,
      "",
      "### Source repository",
      "",
      args.repository,
      "",
      "### Full commit SHA",
      "",
      f"`{args.revision}`",
      "",
      "### Package path",
      "",
      f"`{args.path}`",
      "",
      "### Package-tree digest",
      "",
      f"`{digest}`",
      "",
      "### Declared capabilities",
      "",
      "```json",
      json.dumps(capabilities, indent=2, sort_keys=True),
      "```",
      "",
      "### Trust acknowledgement",
      "",
      "Unreviewed candidate - trusted CI and human review are pending",
      f"<!-- candidate-fingerprint:{fingerprint} -->",
    ]
  )
  try:
    found = subprocess.run(
      [
        "gh",
        "issue",
        "list",
        "--repo",
        args.registration_repository,
        "--state",
        "all",
        "--search",
        f'"candidate-fingerprint:{fingerprint}" in:body',
        "--json",
        "number,url",
      ],
      check=True,
      capture_output=True,
      text=True,
    )
    matches = json.loads(found.stdout)
    if matches:
      issue = matches[0]
      subprocess.run(
        [
          "gh",
          "issue",
          "comment",
          str(issue["number"]),
          "--repo",
          args.registration_repository,
          "--body",
          "Candidate re-registered with the same immutable fingerprint.",
        ],
        check=True,
        capture_output=True,
        text=True,
      )
      return {"status": "linked", "url": issue["url"], "fingerprint": fingerprint}
    created = subprocess.run(
      [
        "gh",
        "issue",
        "create",
        "--repo",
        args.registration_repository,
        "--title",
        f"Federated candidate: {PurePosixPath(args.path).name}",
        "--body",
        body,
      ],
      check=True,
      capture_output=True,
      text=True,
    )
    return {
      "status": "created",
      "url": created.stdout.strip(),
      "fingerprint": fingerprint,
    }
  except (
    FileNotFoundError,
    subprocess.CalledProcessError,
    json.JSONDecodeError,
  ) as exc:
    return {"status": "failed", "error": str(exc), "fingerprint": fingerprint}


def _scan_source(args) -> dict:
  """Independently stage and scan one immutable third-party source."""
  with tempfile.TemporaryDirectory(prefix="bcgov-rescan-") as directory:
    staged = Path(directory) / "package"
    staged.mkdir()
    stage_package(
      args.repository, args.revision, args.path, staged, args.extension_type
    )
    file_inventory = inventory(staged)
    capabilities = getattr(args, "capabilities", None)
    if capabilities is None and hasattr(args, "read"):
      capabilities = _capabilities(args)
    return {
      "source": {
        "repository": args.repository,
        "revision": args.revision,
        "path": args.path,
      },
      "package-tree-digest": tree_digest(file_inventory),
      "files": file_inventory,
      "scan": scan_staged(staged, capabilities, args.extension_type),
    }


def _selected_choice(
  catalog: dict, identity: str, allow_alias: bool = False, scope: str = "project"
) -> tuple[dict, dict]:
  """Resolve one explicit identity without treating aliases as placement authority."""
  record = lookup_extension(catalog, identity)
  if record is None:
    raise FinderError(f"catalog has no extension {identity!r}")
  if record["id"] != identity and not allow_alias:
    raise FinderError(
      f"legacy alias resolves to {record['id']}; "
      "explicitly use the canonical ID or --allow-alias"
    )
  options = record.get("install-options", [])
  if record.get("lifecycle") != "active" or not options:
    raise FinderError(
      "no tested install choice for this type/client or lifecycle; "
      "inspect the notice and source history"
    )
  choice = next((option for option in options if option["scope"] == scope), None)
  if choice is None:
    raise FinderError(f"no tested VS Code {scope} placement choice")
  return record, choice


def _placement_root(args) -> Path:
  """Select project or explicitly requested personal-home scope."""
  if getattr(args, "scope", "project") == "global":
    return args.home.resolve()
  return args.project.resolve()


def _selection(args, catalog: dict) -> tuple[dict, dict]:
  """Select the explicitly requested identity and scope."""
  return _selected_choice(
    catalog,
    args.id,
    getattr(args, "allow_alias", False),
    getattr(args, "scope", "project"),
  )


def _reviewed_install(args, catalog: dict) -> dict:
  """Verify Catalogue bytes and explicitly place the shared native client layout."""
  record, choice = _selection(args, catalog)
  project = _placement_root(args)
  previous = None
  if getattr(args, "previous_catalog", None):
    _, previous = _selected_choice(
      load_catalog(str(args.previous_catalog)), record["id"], scope=choice["scope"]
    )
  print(
    json.dumps(
      {
        "canonical-id": record["id"],
        "choice": choice,
        "checks": record.get("checks"),
        "capabilities": record.get("capabilities"),
        "lifecycle": record["lifecycle"],
        "destination-root": str(project),
        "publication": (
          "Catalogue source (preview)"
          if catalog.get("release-state") != "published"
          or catalog.get("version") == "source"
          else "latest published Catalogue source"
        ),
      },
      indent=2,
      sort_keys=True,
    )
  )
  with tempfile.TemporaryDirectory(prefix="bcgov-native-placement-") as directory:
    staged = Path(directory) / "package"
    staged.mkdir()
    source = record["source"]
    stage_package(
      source["repository"], source["revision"], source["path"], staged, record["type"]
    )
    downloaded = inventory(staged)
    if (
      downloaded != record["files"]
      or tree_digest(downloaded) != record["content-digest"]
    ):
      raise FinderError("downloaded bytes do not match the Catalogue inventory/digest")
    actual_choices = build_install_choices(record, staged)
    if choice not in actual_choices:
      raise FinderError(
        "Catalogue choice does not match actual native client requirements/layout"
      )
    _confirm(f"Copy native files into {project} ({choice['scope']})?", args.yes)
    return place_choice(
      choice,
      staged,
      project,
      confirmed=True,
      previous=previous,
      allow_migration=getattr(args, "allow_migration", False),
    )


def _verify_selected(args, catalog: dict) -> list[dict]:
  """Compare installed bytes directly with a selected Catalogue revision."""
  _, choice = _selection(args, catalog)
  return verify_choice(choice, _placement_root(args))


def _remove_selected(args, catalog: dict) -> dict:
  """Delete selected native files only after explicit consent and byte comparison."""
  _, choice = _selection(args, catalog)
  print(json.dumps(choice, indent=2, sort_keys=True))
  _confirm("Delete only these native files with matching installed bytes?", args.yes)
  return remove_choice(choice, _placement_root(args), confirmed=True)


def _add_capability_arguments(parser: argparse.ArgumentParser) -> None:
  """Add repeatable structured capability options to a parser."""
  parser.add_argument("--read", action="append", default=[])
  parser.add_argument("--write", action="append", default=[])
  parser.add_argument("--network", action="append", default=[])
  parser.add_argument("--command", action="append", default=[])
  parser.add_argument("--environment-variable", action="append", default=[])
  parser.add_argument("--secret-name", action="append", default=[])
  parser.add_argument(
    "--data-class",
    action="append",
    default=[],
    choices=["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
  )


def _parser() -> argparse.ArgumentParser:
  """Build the finder command-line interface."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--catalog", default=DEFAULT_CATALOG)
  commands = parser.add_subparsers(dest="command", required=True)
  search_parser = commands.add_parser("search")
  search_parser.add_argument("query", nargs="+")
  search_parser.add_argument("--extension-type", choices=sorted(KNOWN_EXTENSION_TYPES))
  sources_parser = commands.add_parser("sources")
  sources_parser.add_argument(
    "--extension-type", choices=sorted(KNOWN_EXTENSION_TYPES), default="skill"
  )
  install_parser = commands.add_parser("install")
  install_parser.add_argument("id")
  install_parser.add_argument("--project", type=Path, default=Path.cwd())
  install_parser.add_argument("--yes", action="store_true")
  install_parser.add_argument("--allow-alias", action="store_true")
  install_parser.add_argument("--allow-migration", action="store_true")
  install_parser.add_argument("--previous-catalog", type=Path)
  install_parser.add_argument(
    "--scope", choices=["project", "global"], default="project"
  )
  install_parser.add_argument("--home", type=Path, default=Path.home())
  for action in ("verify", "remove"):
    selected = commands.add_parser(action)
    selected.add_argument("id")
    selected.add_argument("--project", type=Path, default=Path.cwd())
    selected.add_argument("--allow-alias", action="store_true")
    selected.add_argument("--scope", choices=["project", "global"], default="project")
    selected.add_argument("--home", type=Path, default=Path.home())
    if action == "remove":
      selected.add_argument("--yes", action="store_true")
  scan_source = commands.add_parser("scan-source")
  scan_source.add_argument("--repository", required=True)
  scan_source.add_argument("--revision", required=True)
  scan_source.add_argument("--path", required=True)
  scan_source.add_argument(
    "--extension-type", choices=sorted(PUBLISHABLE_EXTENSION_TYPES), default="skill"
  )
  _add_capability_arguments(scan_source)
  commands.add_parser("list")
  return parser


def main(argv: list[str] | None = None) -> int:
  """Run the finder command and return a process exit status."""
  args = _parser().parse_args(argv)
  try:
    if args.command == "search":
      result = search(
        load_catalog(args.catalog), " ".join(args.query), args.extension_type
      )
    elif args.command == "sources":
      result = approved_sources(load_catalog(args.catalog), args.extension_type)
    elif args.command == "list":
      result = load_catalog(args.catalog)["extensions"]
    elif args.command == "install":
      result = _reviewed_install(args, load_catalog(args.catalog))
    elif args.command == "scan-source":
      result = _scan_source(args)
    elif args.command == "remove":
      result = _remove_selected(args, load_catalog(args.catalog))
    else:
      result = _verify_selected(args, load_catalog(args.catalog))
      if not all(item["valid"] for item in result):
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
  except (FinderError, PlacementError, OSError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
