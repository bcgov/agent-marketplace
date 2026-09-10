#!/usr/bin/env python3
"""Validate, scan, and deterministically generate the agent marketplace."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import stat
import sys
import unicodedata
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "bcgov-extension/v1alpha1"
POLICY_VERSION = "bcgov-marketplace-policy/1.0"
MANIFEST_NAME = "bcgov-extension.yaml"
ROOT_FILES = {"SKILL.md", MANIFEST_NAME}
RESOURCE_DIRECTORIES = {"assets", "references", "scripts"}
MAX_FILES = 100
MAX_FILE_BYTES = 512 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
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
ARCHIVE_SUFFIXES = {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".zip"}
BLOCKED_FILENAMES = {
  ".mcp.json",
  "hooks.json",
  "mcp.json",
  "package-lock.json",
  "package.json",
}
BIDI_CODEPOINTS = {
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


class MarketplaceError(Exception):
  """Represent one or more user-correctable marketplace validation failures."""


class StrictSafeLoader(yaml.SafeLoader):
  """Load safe YAML while rejecting aliases and duplicate mapping keys."""

  def compose_node(self, parent, index):
    """Reject aliases before composing a YAML node."""
    if self.check_event(yaml.AliasEvent):
      event = self.peek_event()
      raise yaml.constructor.ConstructorError(
        None, None, f"YAML aliases are not allowed: *{event.anchor}", event.start_mark
      )
    return super().compose_node(parent, index)


def _construct_mapping(loader, node, deep=False):
  """Construct a mapping and reject duplicate keys."""
  mapping = {}
  for key_node, value_node in node.value:
    key = loader.construct_object(key_node, deep=deep)
    if key in mapping:
      raise yaml.constructor.ConstructorError(
        "while constructing a mapping",
        node.start_mark,
        f"duplicate key: {key}",
        key_node.start_mark,
      )
    mapping[key] = loader.construct_object(value_node, deep=deep)
  return mapping


StrictSafeLoader.add_constructor(
  yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml(path: Path) -> dict:
  """Load a UTF-8 YAML mapping with the strict safe loader."""
  try:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictSafeLoader)
  except (OSError, UnicodeError, yaml.YAMLError) as exc:
    raise MarketplaceError(f"{path}: invalid YAML: {exc}") from exc
  if not isinstance(value, dict):
    raise MarketplaceError(f"{path}: top-level YAML value must be a mapping")
  return value


def load_schema(root: Path) -> dict:
  """Load the repository's marketplace manifest JSON Schema."""
  path = root / "schemas" / "bcgov-extension-v1alpha1.schema.json"
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise MarketplaceError(f"{path}: invalid JSON Schema: {exc}") from exc


def manifest_paths(root: Path) -> list[Path]:
  """Return hosted marketplace manifests in stable package-name order.

  Canonical packages live under either the generic community bucket or a named
  specialty area. The legacy flat layout is intentionally unsupported and is
  excluded from the generated catalog.
  """
  candidates = []
  skills_root = root / "skills"
  candidates.extend(sorted(skills_root.glob(f"community/*/{MANIFEST_NAME}")))
  candidates.extend(sorted(skills_root.glob(f"security/*/{MANIFEST_NAME}")))
  seen = set()
  unique = []
  for path in candidates:
    if path not in seen:
      seen.add(path)
      unique.append(path)
  return sorted(unique, key=lambda item: item.relative_to(root).as_posix())


def validate_manifest(path: Path, schema: dict) -> tuple[dict | None, list[str]]:
  """Validate one author-controlled manifest and package identity."""
  try:
    manifest = load_yaml(path)
  except MarketplaceError as exc:
    return None, [str(exc)]
  validator = Draft202012Validator(schema, format_checker=FormatChecker())
  errors = []
  for error in sorted(
    validator.iter_errors(manifest), key=lambda item: list(item.path)
  ):
    location = ".".join(str(part) for part in error.path) or "<root>"
    errors.append(f"{path}: {location}: {error.message}")
  expected_id = f"bcgov-public/{path.parent.name}"
  if manifest.get("id") != expected_id:
    errors.append(f"{path}: id must be {expected_id!r}")
  skill_path = path.parent / "SKILL.md"
  if not skill_path.is_file():
    errors.append(f"{path.parent}: missing SKILL.md")
  return manifest, errors


def _finding(
  severity: str,
  code: str,
  path: str,
  message: str,
  line: int | None = None,
) -> dict:
  """Create a stable scanner finding record."""
  result = {"severity": severity, "code": code, "path": path, "message": message}
  if line is not None:
    result["line"] = line
  return result


def _regular_files(package_dir: Path) -> tuple[list[Path], list[dict]]:
  """Enumerate regular package files without following links."""
  files = []
  findings = []
  seen_names = {}
  seen_inodes = {}
  for path in sorted(package_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
    relative = path.relative_to(package_dir).as_posix()
    folded = relative.casefold()
    if folded in seen_names and seen_names[folded] != relative:
      findings.append(
        _finding(
          "blocking",
          "case-collision",
          relative,
          f"name collides with {seen_names[folded]!r} on case-insensitive filesystems",
        )
      )
    seen_names[folded] = relative
    try:
      status = path.lstat()
      mode = status.st_mode
    except OSError as exc:
      findings.append(_finding("blocking", "unreadable-path", relative, str(exc)))
      continue
    if stat.S_ISLNK(mode):
      findings.append(
        _finding("blocking", "symlink", relative, "symbolic links are not allowed")
      )
    elif stat.S_ISDIR(mode):
      continue
    elif not stat.S_ISREG(mode):
      findings.append(
        _finding("blocking", "special-file", relative, "only regular files are allowed")
      )
    else:
      inode = (status.st_dev, status.st_ino)
      if status.st_nlink > 1 or inode in seen_inodes:
        findings.append(
          _finding(
            "blocking",
            "hard-link",
            relative,
            "hard-linked files are not allowed",
          )
        )
      seen_inodes[inode] = relative
      files.append(path)
  return files, findings


def _scan_text(relative: str, text: str, manifest: dict) -> list[dict]:
  """Scan decoded package text for deterministic blocking and advisory rules."""
  findings = []
  declared_network = set(manifest.get("capabilities", {}).get("network", []))
  declared_env = set(
    manifest.get("capabilities", {}).get("environment-variables", [])
  ) | set(manifest.get("capabilities", {}).get("secret-names", []))
  for line_number, line in enumerate(text.splitlines(), start=1):
    hidden = [
      char
      for char in line
      if char in BIDI_CODEPOINTS or unicodedata.category(char) == "Cf"
    ]
    if hidden:
      codepoints = ", ".join(f"U+{ord(char):04X}" for char in sorted(set(hidden)))
      findings.append(
        _finding(
          "blocking",
          "hidden-unicode",
          relative,
          f"hidden or bidirectional Unicode is not allowed ({codepoints})",
          line_number,
        )
      )
    for code, pattern in SECRET_PATTERNS.items():
      if pattern.search(line):
        findings.append(
          _finding(
            "blocking",
            code,
            relative,
            "possible credential or secret value",
            line_number,
          )
        )
    for host in NETWORK_COMMAND_RE.findall(line):
      if host not in declared_network and "*" not in declared_network:
        findings.append(
          _finding(
            "blocking",
            "undeclared-network",
            relative,
            f"network command targets undeclared host {host!r}",
            line_number,
          )
        )
    for match in ENVIRONMENT_RE.finditer(line):
      name = next(group for group in match.groups() if group)
      if name not in declared_env and "*" not in declared_env:
        findings.append(
          _finding(
            "blocking",
            "undeclared-environment-variable",
            relative,
            f"references undeclared environment variable {name!r}",
            line_number,
          )
        )
    for code, pattern in ADVISORY_PATTERNS.items():
      if pattern.search(line):
        findings.append(
          _finding(
            "advisory",
            code,
            relative,
            "instruction requires human review",
            line_number,
          )
        )
  return findings


def scan_package(package_dir: Path, manifest: dict) -> dict:
  """Scan package bytes without importing or executing contributed content."""
  files, findings = _regular_files(package_dir)
  declared_commands = set(manifest.get("capabilities", {}).get("commands", []))
  total_bytes = 0
  if len(files) > MAX_FILES:
    findings.append(
      _finding("blocking", "file-count", ".", f"package exceeds {MAX_FILES} files")
    )
  for path in files:
    relative = path.relative_to(package_dir).as_posix()
    parts = Path(relative).parts
    size = path.stat().st_size
    total_bytes += size
    if any(part.startswith(".") for part in parts):
      findings.append(
        _finding("blocking", "hidden-path", relative, "hidden paths are not allowed")
      )
    if (len(parts) == 1 and relative not in ROOT_FILES) or (
      len(parts) > 1 and (len(parts) != 2 or parts[0] not in RESOURCE_DIRECTORIES)
    ):
      findings.append(
        _finding(
          "blocking",
          "nested-resource",
          relative,
          "resources must be flat files under assets, references, or scripts",
        )
      )
    if path.name.lower() in BLOCKED_FILENAMES:
      findings.append(
        _finding(
          "blocking",
          "blocked-extension-type",
          relative,
          "hooks, MCP, and package lifecycle configuration are not supported",
        )
      )
    if path.suffix.lower() in ARCHIVE_SUFFIXES:
      findings.append(
        _finding("blocking", "archive", relative, "archives are not allowed")
      )
    elif path.suffix.lower() not in ALLOWED_SUFFIXES:
      findings.append(
        _finding(
          "blocking", "unsupported-file-type", relative, "file type is not allowed"
        )
      )
    if size > MAX_FILE_BYTES:
      findings.append(
        _finding(
          "blocking", "file-size", relative, f"file exceeds {MAX_FILE_BYTES} bytes"
        )
      )
    if path.stat().st_mode & 0o111:
      findings.append(
        _finding(
          "blocking", "executable-bit", relative, "executable bits are not allowed"
        )
      )
    if relative.startswith("scripts/") and not (
      path.name in declared_commands or "*" in declared_commands
    ):
      findings.append(
        _finding(
          "blocking",
          "undeclared-script",
          relative,
          "script filename is not declared in capabilities.commands",
        )
      )
    try:
      text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
      findings.append(
        _finding(
          "blocking", "binary-file", relative, "package files must be UTF-8 text"
        )
      )
      continue
    findings.extend(_scan_text(relative, text, manifest))
  if total_bytes > MAX_PACKAGE_BYTES:
    findings.append(
      _finding(
        "blocking", "package-size", ".", f"package exceeds {MAX_PACKAGE_BYTES} bytes"
      )
    )
  findings.sort(
    key=lambda item: (
      item["severity"],
      item["path"],
      item.get("line", 0),
      item["code"],
    )
  )
  return {
    "policy-version": POLICY_VERSION,
    "outcome": "blocked"
    if any(item["severity"] == "blocking" for item in findings)
    else "passed",
    "findings": findings,
  }


def package_inventory(package_dir: Path) -> list[dict]:
  """Return stable file hashes and sizes for a regular-file package tree."""
  files, findings = _regular_files(package_dir)
  if findings:
    raise MarketplaceError("cannot inventory a package with non-regular paths")
  return _inventory_regular_files(package_dir, files)


def _inventory_regular_files(package_dir: Path, files: list[Path]) -> list[dict]:
  """Hash the regular files discovered while inspecting one package tree."""
  inventory = []
  for path in files:
    content = path.read_bytes()
    inventory.append(
      {
        "path": path.relative_to(package_dir).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
      }
    )
  return inventory


def package_digest(inventory: list[dict]) -> str:
  """Calculate a deterministic package-tree digest from an inventory."""
  digest = hashlib.sha256()
  for item in inventory:
    digest.update(item["path"].encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(item["size"]).encode("ascii"))
    digest.update(b"\0")
    digest.update(item["sha256"].encode("ascii"))
    digest.update(b"\n")
  return f"sha256:{digest.hexdigest()}"


def analyze_submission(root: Path, package_dir: Path) -> dict:
  """Analyze one submitted package without executing any of its content."""
  package_dir = package_dir.resolve()
  try:
    prospective_path = package_dir.relative_to(root.resolve()).as_posix()
  except ValueError as exc:
    raise MarketplaceError("submission package must be inside the marketplace") from exc
  manifest, errors = validate_manifest(package_dir / MANIFEST_NAME, load_schema(root))
  if errors or manifest is None:
    raise MarketplaceError("\n".join(errors))
  parts = prospective_path.split("/")
  if (
    len(parts) != 3
    or parts[0] != "skills"
    or parts[1]
    not in {
      "community",
      "security",
    }
  ):
    raise MarketplaceError("submission package must use a canonical skill path")
  scan = scan_package(package_dir, manifest)
  files, structural_findings = _regular_files(package_dir)
  inventory = _inventory_regular_files(package_dir, files)
  return {
    "classification": "blocked" if scan["outcome"] == "blocked" else "needs-review",
    "prospective-path": prospective_path,
    "specialty": parts[1],
    "reviewers": load_marketplace_config(root)["reviewers"],
    "package-tree-digest": package_digest(inventory),
    "files": inventory,
    "inventory-complete": not structural_findings,
    "scan": scan,
  }


def load_marketplace_config(root: Path) -> dict:
  """Load and validate centrally controlled release and review metadata."""
  path = root / "config" / "marketplace.yaml"
  config = load_yaml(path)
  allowed = {
    "schema-version",
    "release-state",
    "repository",
    "revision",
    "installer-version",
    "reviewers",
    "approved-discovery-sources",
  }
  unexpected = sorted(set(config) - allowed)
  if unexpected:
    raise MarketplaceError(f"{path}: unexpected keys: {', '.join(unexpected)}")
  required = allowed - {"approved-discovery-sources"}
  missing = sorted(required - set(config))
  if missing:
    raise MarketplaceError(f"{path}: missing keys: {', '.join(missing)}")
  if config["schema-version"] != "bcgov-marketplace/v1alpha1":
    raise MarketplaceError(f"{path}: unsupported schema-version")
  if config["release-state"] not in {"development", "published"}:
    raise MarketplaceError(f"{path}: release-state must be development or published")
  if not re.fullmatch(r"[0-9a-f]{40}", str(config["revision"])):
    raise MarketplaceError(f"{path}: revision must be a full lowercase commit SHA")
  if config["repository"] != "https://github.com/bcgov/agent-marketplace":
    raise MarketplaceError(f"{path}: repository must use the canonical post-clone name")
  sources = config.get("approved-discovery-sources", [])
  if not isinstance(sources, list):
    raise MarketplaceError(f"{path}: approved-discovery-sources must be a list")
  extension_types = {"skill", "prompt", "instructions", "agent", "hook", "mcp"}
  source_ids = set()
  for source in sources:
    if not isinstance(source, dict):
      raise MarketplaceError(
        f"{path}: each approved discovery source must be a mapping"
      )
    required_source_keys = {
      "id",
      "name",
      "status",
      "extension-types",
      "repository",
      "catalog",
    }
    missing_source_keys = sorted(required_source_keys - set(source))
    if missing_source_keys:
      raise MarketplaceError(
        f"{path}: discovery source missing keys: {', '.join(missing_source_keys)}"
      )
    source_id = source["id"]
    if not isinstance(source_id, str) or not re.fullmatch(
      r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id
    ):
      raise MarketplaceError(f"{path}: discovery source id must be kebab-case")
    if source_id in source_ids:
      raise MarketplaceError(f"{path}: duplicate discovery source id: {source_id}")
    source_ids.add(source_id)
    if source["status"] not in {"active", "inactive"}:
      raise MarketplaceError(f"{path}: invalid discovery source status: {source_id}")
    declared_types = source["extension-types"]
    if not isinstance(declared_types, list) or not declared_types:
      raise MarketplaceError(
        f"{path}: discovery source types must be a non-empty list: {source_id}"
      )
    unknown_types = sorted(set(declared_types) - extension_types)
    if unknown_types:
      raise MarketplaceError(
        f"{path}: unknown discovery source types for {source_id}: "
        f"{', '.join(unknown_types)}"
      )
  return config


TYPE_DIRECTORIES = {
  "skills": "skill",
  "prompts": "prompt",
  "instructions": "instruction",
  "agents": "agent",
  "hooks": "hook",
  "mcp": "mcp",
}

# Ordered by how likely a reader is to meet the type, not alphabetically.
# Skills are the only publishable type today; prompts and instructions are
# inert content and closest behind; agents, hooks, and MCP servers execute and
# stay deferred until their runtime security models exist.
EXTENSION_TYPE_ORDER = ["skill", "prompt", "instruction", "agent", "hook", "mcp"]


def build_catalog(root: Path) -> tuple[dict, str]:
  """Build machine-readable and escaped HTML catalog projections."""
  schema = load_schema(root)
  config = load_marketplace_config(root)
  records = []
  errors = []
  for path in manifest_paths(root):
    manifest, manifest_errors = validate_manifest(path, schema)
    errors.extend(manifest_errors)
    if manifest is None or manifest_errors:
      continue
    package_dir = path.parent
    relative_path = package_dir.relative_to(root).as_posix()
    parts = relative_path.split("/")
    specialty = parts[1] if len(parts) > 1 and parts[0] == "skills" else "community"
    record = {
      **manifest,
      "type": TYPE_DIRECTORIES.get(parts[0], "skill"),
      "specialty": specialty,
      "source": {
        "repository": config["repository"],
        "revision": config["revision"],
        "path": relative_path,
      },
      "content-digest": "",
      "files": [],
      "policy": {},
      "review": {
        "status": "marketplace-reviewed",
        "reviewers": config["reviewers"],
        "revision": config["revision"],
      },
    }
    scan = scan_package(package_dir, manifest)
    blocking = [item for item in scan["findings"] if item["severity"] == "blocking"]
    if blocking:
      errors.extend(
        f"{package_dir}: {item['path']}: {item['code']}: {item['message']}"
        for item in blocking
      )
      continue
    inventory = package_inventory(package_dir)
    record["content-digest"] = package_digest(inventory)
    record["files"] = inventory
    record["policy"] = scan
    records.append(record)
  if not records:
    errors.append("no hosted marketplace manifests found")
  if errors:
    raise MarketplaceError("\n".join(errors))
  records.sort(key=lambda item: item["id"])
  catalog = {
    "schema-version": "bcgov-marketplace-catalog/v1alpha1",
    "release-state": config["release-state"],
    "repository": config["repository"],
    "revision": config["revision"],
    "installer-version": str(config["installer-version"]),
    "policy-version": POLICY_VERSION,
    "approved-discovery-sources": config.get("approved-discovery-sources", []),
    "count": len(records),
    "extensions": records,
  }
  cards = [_catalog_row(record) for record in records]
  # The page builds its facets from the rendered rows, so the canonical type
  # vocabulary travels with them. Types absent from the catalog still appear,
  # disabled, which shows the reader what this marketplace intends to carry.
  # Script content is raw text, so HTML escaping would survive into the parsed
  # string. Escaping "<" at the JSON level keeps it valid and cannot close the
  # element early.
  vocabulary = json.dumps(
    {"types": EXTENSION_TYPE_ORDER, "installer-version": str(config["installer-version"])},
    sort_keys=True,
  ).replace("<", "\\u003c")
  header = (
    '<script type="application/json" id="catalog-vocabulary">'
    f"{vocabulary}"
    "</script>"
  )
  return catalog, "\n\n".join([header, *cards]) + "\n"


TRUST_LABELS = {
  "marketplace-reviewed": "Reviewed",
  "domain-reviewed": "Domain reviewed",
  "locally-scanned-not-bc-gov-reviewed": "Scanned only",
  "unreviewed": "Unreviewed",
}

ACCESS_SIGNALS = (
  ("commands", "Commands", "runs commands"),
  ("network", "Network", "reaches the network"),
  ("writes", "Writes", "writes files"),
)


def _access_signals(capabilities: dict) -> dict[str, list[str]]:
  """Reduce declared capabilities to the three access facts users compare."""
  filesystem = capabilities.get("filesystem") or {}
  return {
    "commands": list(capabilities.get("commands") or []),
    "network": list(capabilities.get("network") or []),
    "writes": list(filesystem.get("write") or []),
  }


def _catalog_row(record: dict) -> str:
  """Render one catalog row, escaping every author-controlled value."""
  capabilities = record["capabilities"]
  signals = _access_signals(capabilities)
  active = [key for key, _label, _phrase in ACCESS_SIGNALS if signals[key]]
  status = (record.get("review") or {}).get("status") or "unreviewed"
  trust = TRUST_LABELS.get(status, "Unreviewed")
  specialty = record.get("specialty") or "community"

  granted = [phrase for key, _label, phrase in ACCESS_SIGNALS if signals[key]]
  withheld = [phrase for key, _label, phrase in ACCESS_SIGNALS if not signals[key]]
  sentence = f"Declared access: {_join_phrases(granted)}." if granted else (
    "Declares no commands, network, or file writes."
  )
  if granted and withheld:
    sentence += f" Does not declare that it {_join_phrases(withheld)}."

  haystack = " ".join(
    [
      record["display-name"],
      record["summary"],
      specialty,
      record.get("type") or "",
      " ".join(record.get("maintainers") or []),
      " ".join(signals["commands"]),
      " ".join(signals["network"]),
    ]
  ).lower()

  slots = []
  for key, label, _phrase in ACCESS_SIGNALS:
    state = "is-on" if signals[key] else "is-off"
    detail = ", ".join(signals[key][:6]) if signals[key] else "not declared"
    slots.append(
      f'    <li class="cat-slot {state}" data-signal="{key}" '
      f'title="{label}: {html.escape(detail, quote=True)}">{label}</li>'
    )

  return "\n".join(
    [
      f'<article class="cat-row" data-extension-id="{html.escape(record["id"], quote=True)}"',
      f'  data-type="{html.escape(record.get("type") or "", quote=True)}"',
      f'  data-specialty="{html.escape(specialty, quote=True)}"',
      f'  data-lifecycle="{html.escape(record.get("lifecycle") or "", quote=True)}"',
      f'  data-status="{html.escape(status, quote=True)}"',
      f'  data-access="{html.escape(" ".join(active), quote=True)}"',
      f'  data-haystack="{html.escape(haystack, quote=True)}">',
      '  <div class="cat-row-id">',
      f'    <h3><button type="button" class="cat-row-open">'
      f"{html.escape(record['display-name'])}</button></h3>",
      f'    <p class="cat-row-summary">{html.escape(record["summary"])}</p>',
      "  </div>",
      f'  <p class="cat-row-domain">{html.escape(specialty)}</p>',
      f'  <ul class="cat-slots" aria-label="{html.escape(sentence, quote=True)}">',
      *slots,
      "  </ul>",
      f'  <p class="cat-row-trust" data-status="{html.escape(status, quote=True)}">'
      f"{html.escape(trust)}</p>",
      "</article>",
    ]
  )


def _join_phrases(items: list[str]) -> str:
  """Join phrases into readable prose without Oxford-comma edge cases."""
  if len(items) <= 1:
    return "".join(items)
  return f"{', '.join(items[:-1])} and {items[-1]}"


def _serialized_catalog(catalog: dict) -> str:
  """Serialize the catalog in its canonical checked-in representation."""
  return json.dumps(catalog, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def generate(root: Path, check: bool = False) -> list[str]:
  """Write generated projections or report checked-in drift."""
  catalog, cards = build_catalog(root)
  serialized_catalog = _serialized_catalog(catalog)
  outputs = {
    root / "catalog" / "catalog.json": serialized_catalog,
    root / "docs" / "assets" / "catalog.json": serialized_catalog,
    root / "docs" / "_generated" / "catalog-cards.html": cards,
  }
  drift = []
  for path, expected in outputs.items():
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current != expected:
      drift.append(path.relative_to(root).as_posix())
      if not check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
  return drift


def validate(root: Path) -> None:
  """Validate all packages and ensure generated projections are current."""
  drift = generate(root, check=True)
  if drift:
    raise MarketplaceError(
      "generated output drift: " + ", ".join(drift) + "; run marketplace.py generate"
    )


def _parser() -> argparse.ArgumentParser:
  """Build the marketplace command-line parser."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
  subparsers = parser.add_subparsers(dest="command", required=True)
  subparsers.add_parser("validate", help="validate packages and generated output")
  generate_parser = subparsers.add_parser("generate", help="write generated output")
  generate_parser.add_argument("--check", action="store_true")
  scan_parser = subparsers.add_parser("scan", help="scan one package directory")
  scan_parser.add_argument("package", type=Path)
  analyze_parser = subparsers.add_parser(
    "analyze", help="analyze one submitted package and route it for review"
  )
  analyze_parser.add_argument("package", type=Path)
  return parser


def main(argv: list[str] | None = None) -> int:
  """Run the marketplace CLI and return a process exit status."""
  args = _parser().parse_args(argv)
  root = args.root.resolve()
  try:
    if args.command == "validate":
      validate(root)
    elif args.command == "generate":
      drift = generate(root, check=args.check)
      if args.check and drift:
        raise MarketplaceError("generated output drift: " + ", ".join(drift))
      for path in drift:
        print(f"generated {path}")
    elif args.command == "scan":
      manifest_path = args.package / MANIFEST_NAME
      manifest, errors = validate_manifest(manifest_path, load_schema(root))
      if errors or manifest is None:
        raise MarketplaceError("\n".join(errors))
      print(json.dumps(scan_package(args.package, manifest), indent=2, sort_keys=True))
    else:
      print(
        json.dumps(analyze_submission(root, args.package), indent=2, sort_keys=True)
      )
  except MarketplaceError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
