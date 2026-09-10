#!/usr/bin/env python3
"""Search and install immutable Agent Skills with local receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import yaml

POLICY_VERSION = "bcgov-finder-policy/1.0"
MARKETPLACE_REVISION = "842241b962849ad239e1e9c90589b6bc9c881e53"
DEFAULT_CATALOG = (
  "https://raw.githubusercontent.com/bcgov/agent-marketplace/main/catalog/catalog.json"
)
PINNED_CATALOG = (
  "https://raw.githubusercontent.com/bcgov/agent-marketplace/"
  f"{MARKETPLACE_REVISION}/catalog/catalog.json"
)
LOCAL_CATALOG = Path(__file__).resolve().parents[1] / "catalog" / "catalog.json"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 100
ACTIVE_EXTENSION_TYPES = {"skill"}
KNOWN_EXTENSION_TYPES = {"skill", "prompt", "instructions", "agent", "hook", "mcp"}
ROOT_FILES = {"SKILL.md"}
RESOURCE_DIRECTORIES = {"assets", "references", "scripts"}
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
  if source == DEFAULT_CATALOG:
    candidates.extend([str(LOCAL_CATALOG), PINNED_CATALOG])
  failures = []
  for candidate in candidates:
    try:
      if candidate.startswith("https://"):
        content = _download(candidate).decode("utf-8")
      else:
        content = Path(candidate).read_text(encoding="utf-8")
      catalog = json.loads(content)
      if catalog.get("schema-version") != "bcgov-marketplace-catalog/v1alpha1":
        raise FinderError(f"unsupported catalog schema in {candidate}")
      if (
        candidate == PINNED_CATALOG and catalog.get("revision") != MARKETPLACE_REVISION
      ):
        raise FinderError("pinned catalog revision does not match the companion")
      if candidate != source:
        print(
          f"WARNING: using fallback catalog {candidate} after {failures[-1]}",
          file=sys.stderr,
        )
      return catalog
    except (FinderError, OSError, UnicodeError, json.JSONDecodeError) as exc:
      failures.append(str(exc))
  raise FinderError(f"cannot load catalog {source}: {'; '.join(failures)}")


def _tokens(value: str) -> set[str]:
  """Return normalized search terms used by deterministic ranking."""
  return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}


def search(catalog: dict, query: str, extension_type: str | None = None) -> list[dict]:
  """Return at most three active records in deterministic rank order."""
  if extension_type is not None and extension_type not in KNOWN_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  query_tokens = _tokens(query)
  ranked = []
  for record in catalog["extensions"]:
    if record["lifecycle"] != "active":
      continue
    if extension_type is not None and record.get("type") != extension_type:
      continue
    name_tokens = _tokens(record["id"] + " " + record["display-name"])
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
    if score:
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
  repository: str, revision: str, package_path: str, target: Path
) -> None:
  """Extract only one package path from an immutable GitHub archive."""
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
  if not (target / "SKILL.md").is_file():
    raise FinderError("resolved package does not contain SKILL.md")


def inventory(package: Path) -> list[dict]:
  """Inventory regular package files in path order."""
  result = []
  for path in sorted(package.rglob("*")):
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


def scan_staged(package: Path, capabilities: dict | None = None) -> dict:
  """Apply deterministic local policy without executing staged content."""
  findings = []
  total = 0
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
    if (len(parts) == 1 and relative not in ROOT_FILES) or (
      len(parts) > 1 and (len(parts) != 2 or parts[0] not in RESOURCE_DIRECTORIES)
    ):
      findings.append(_finding("blocking", "nested-resource", relative, 0))
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
  skill_text = (package / "SKILL.md").read_text(encoding="utf-8", errors="replace")
  if not re.match(
    r"^---\s*\n(?:(?!\n---\s*$).)*\n---\s*\n", skill_text, re.DOTALL | re.MULTILINE
  ):
    findings.append(_finding("blocking", "malformed-skill-metadata", "SKILL.md", 1))
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


def _install_copy(staged: Path, target: Path, expected_digest: str) -> None:
  """Atomically install staged bytes and verify the post-copy digest."""
  if target.exists():
    existing = tree_digest(inventory(target))
    if existing == expected_digest:
      return
    raise FinderError(f"destination exists with different bytes: {target}")
  target.parent.mkdir(parents=True, exist_ok=True)
  temporary = target.with_name(f".{target.name}.installing")
  if temporary.exists():
    shutil.rmtree(temporary)
  shutil.copytree(staged, temporary)
  if tree_digest(inventory(temporary)) != expected_digest:
    shutil.rmtree(temporary)
    raise FinderError("post-copy digest mismatch")
  temporary.replace(target)


def _receipt_path(project: Path, name: str) -> Path:
  """Return the local receipt path for an installed package."""
  return project / ".github" / "agent-marketplace" / "receipts" / f"{name}.json"


def _write_receipt(project: Path, name: str, receipt: dict) -> Path:
  """Write a stable, project-local installation receipt."""
  path = _receipt_path(project, name)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
  )
  return path


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
    stage_package(args.repository, args.revision, args.path, staged)
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
      "scan": scan_staged(staged, capabilities),
    }


def _retry_registration(args) -> dict:
  """Retry registration from a complete local installation receipt."""
  try:
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    source = receipt["source"]
    namespace = argparse.Namespace(
      discovery_catalog=receipt["discovery-catalog"],
      repository=source["repository"],
      revision=source["revision"],
      path=source["path"],
      registration_repository=args.registration_repository,
    )
    registration = _register_candidate(
      namespace,
      receipt["package-tree-digest"],
      receipt["declared-capabilities"],
    )
  except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
    raise FinderError(f"invalid receipt {args.receipt}: {exc}") from exc
  receipt["registration"] = registration
  args.receipt.write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
  )
  return registration


def _reviewed_install(args, catalog: dict) -> dict:
  """Install one marketplace-reviewed package from its catalog record."""
  record = next((item for item in catalog["extensions"] if item["id"] == args.id), None)
  if record is None:
    raise FinderError(f"catalog has no extension {args.id!r}")
  if record["lifecycle"] != "active":
    raise FinderError(
      f"extension lifecycle is {record['lifecycle']}; new installs are blocked"
    )
  extension_type = record.get("type", "skill")
  if extension_type not in ACTIVE_EXTENSION_TYPES:
    raise FinderError(
      f"extension type is {extension_type!r}; installation is not active for this type"
    )
  project = args.project.resolve()
  name = record["id"].split("/", 1)[1]
  target = project / ".github" / "skills" / name
  print(
    json.dumps(
      {
        "id": record["id"],
        "type": extension_type,
        "publisher": record["publisher"],
        "source": record["source"],
        "digest": record["content-digest"],
        "capabilities": record["capabilities"],
        "review": record["review"],
        "target": str(target),
      },
      indent=2,
      sort_keys=True,
    )
  )
  _confirm("Install this reviewed skill into the current project?", args.yes)
  with tempfile.TemporaryDirectory(prefix="bcgov-marketplace-") as directory:
    staged = Path(directory) / "package"
    staged.mkdir()
    source = record["source"]
    stage_package(source["repository"], source["revision"], source["path"], staged)
    staged_inventory = inventory(staged)
    if staged_inventory != record["files"]:
      raise FinderError("downloaded file inventory does not match the catalog")
    digest = tree_digest(staged_inventory)
    if digest != record["content-digest"]:
      raise FinderError("downloaded package digest does not match the catalog")
    _install_copy(staged, target, digest)
  receipt = {
    "package-id": record["id"],
    "extension-type": extension_type,
    "source": record["source"],
    "package-tree-digest": record["content-digest"],
    "scan": record["policy"],
    "declared-capabilities": record["capabilities"],
    "granted-capabilities": record["capabilities"],
    "install-target": str(target),
    "scope": "project",
    "installed-at": _now(),
    "trust": "Marketplace reviewed",
    "review": record["review"],
    "registration": None,
  }
  receipt_path = _write_receipt(project, name, receipt)
  return {
    "installed": str(target),
    "receipt": str(receipt_path),
    "digest": record["content-digest"],
  }


def _third_party_install(args) -> dict:
  """Stage, scan, install, receipt, and register an immutable third-party package."""
  project = args.project.resolve()
  if args.extension_type not in ACTIVE_EXTENSION_TYPES:
    raise FinderError(
      f"extension type is {args.extension_type!r}; third-party "
      "installation is not active"
    )
  name = args.name or PurePosixPath(args.path).name
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
    raise FinderError("installed skill name must be kebab-case")
  capabilities = _capabilities(args)
  with tempfile.TemporaryDirectory(prefix="bcgov-candidate-") as directory:
    staged = Path(directory) / "package"
    staged.mkdir()
    stage_package(args.repository, args.revision, args.path, staged)
    scan = scan_staged(staged, capabilities)
    digest = tree_digest(inventory(staged))
    preview = {
      "discovery-catalog": args.discovery_catalog,
      "source": {
        "repository": args.repository,
        "revision": args.revision,
        "path": args.path,
      },
      "extension-type": args.extension_type,
      "digest": digest,
      "scan": scan,
      "capabilities": capabilities,
      "target": str(project / ".github" / "skills" / name),
      "registration-repository": args.registration_repository,
    }
    print(json.dumps(preview, indent=2, sort_keys=True))
    if scan["outcome"] == "blocked":
      raise FinderError("candidate has blocking findings; installation is not allowed")
    if (
      any(item["severity"] == "advisory" for item in scan["findings"])
      and not args.acknowledge_advisories
    ):
      raise FinderError("advisory findings require --acknowledge-advisories")
    _confirm(
      "Install this locally scanned candidate and register it for review?", args.yes
    )
    target = project / ".github" / "skills" / name
    _install_copy(staged, target, digest)
  registration = _register_candidate(args, digest, capabilities)
  receipt = {
    "package-id": name,
    "extension-type": args.extension_type,
    "discovery-catalog": args.discovery_catalog,
    "source": {
      "repository": args.repository,
      "revision": args.revision,
      "path": args.path,
    },
    "package-tree-digest": digest,
    "scan": scan,
    "declared-capabilities": capabilities,
    "granted-capabilities": capabilities,
    "install-target": str(target),
    "scope": "project",
    "installed-at": _now(),
    "trust": "Locally scanned - not BC Gov reviewed",
    "registration": registration,
  }
  receipt_path = _write_receipt(project, name, receipt)
  result = {
    "installed": str(target),
    "receipt": str(receipt_path),
    "registration": registration,
  }
  if registration["status"] == "failed":
    result["retry"] = f"python {Path(__file__).name} register --receipt {receipt_path}"
  return result


def _now() -> str:
  """Return a stable UTC installation timestamp."""
  return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _verify(project: Path) -> list[dict]:
  """Verify every project receipt against currently installed bytes."""
  results = []
  receipt_dir = project.resolve() / ".github" / "agent-marketplace" / "receipts"
  for path in sorted(receipt_dir.glob("*.json")):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    target = Path(receipt["install-target"])
    actual = tree_digest(inventory(target)) if target.is_dir() else None
    results.append(
      {
        "receipt": str(path),
        "expected": receipt["package-tree-digest"],
        "actual": actual,
        "valid": actual == receipt["package-tree-digest"],
      }
    )
  return results


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
  third_party = commands.add_parser("install-third-party")
  third_party.add_argument("--discovery-catalog", required=True)
  third_party.add_argument("--repository", required=True)
  third_party.add_argument("--revision", required=True)
  third_party.add_argument("--path", required=True)
  third_party.add_argument("--extension-type", default="skill")
  third_party.add_argument("--name")
  third_party.add_argument("--project", type=Path, default=Path.cwd())
  third_party.add_argument(
    "--registration-repository", default="bcgov/agent-marketplace"
  )
  third_party.add_argument("--acknowledge-advisories", action="store_true")
  third_party.add_argument("--yes", action="store_true")
  _add_capability_arguments(third_party)
  verify_parser = commands.add_parser("verify")
  verify_parser.add_argument("--project", type=Path, default=Path.cwd())
  scan_source = commands.add_parser("scan-source")
  scan_source.add_argument("--repository", required=True)
  scan_source.add_argument("--revision", required=True)
  scan_source.add_argument("--path", required=True)
  scan_source.add_argument("--extension-type", default="skill")
  _add_capability_arguments(scan_source)
  register_parser = commands.add_parser("register")
  register_parser.add_argument("--receipt", type=Path, required=True)
  register_parser.add_argument(
    "--registration-repository", default="bcgov/agent-marketplace"
  )
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
    elif args.command == "install-third-party":
      result = _third_party_install(args)
    elif args.command == "scan-source":
      if args.extension_type not in ACTIVE_EXTENSION_TYPES:
        raise FinderError(
          f"extension type is {args.extension_type!r}; scanning is not active"
        )
      result = _scan_source(args)
    elif args.command == "register":
      result = _retry_registration(args)
    else:
      result = _verify(args.project)
    print(json.dumps(result, indent=2, sort_keys=True))
  except FinderError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
