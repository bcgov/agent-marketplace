#!/usr/bin/env python3
"""Search Extensions and explicitly place immutable native files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from install_choices import (
  PlacementError,
  build_install_choices,
  place_choice,
  remove_choice,
  verify_choice,
)
from jsonschema import Draft202012Validator

DEFAULT_CATALOG = "https://bcgov.github.io/agent-marketplace/assets/catalog.json"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 100
MIN_MATCH_SCORE = 8
KNOWN_EXTENSION_TYPES = {"skill", "prompt", "instructions", "agent"}
PUBLISHABLE_EXTENSION_TYPES = KNOWN_EXTENSION_TYPES


class FinderError(Exception):
  """Represent a finder failure that is safe to show to the user."""


def load_catalog(source: str, *, historical: bool = False) -> dict:
  """Load only the selected v1 Catalogue, failing closed without source fallback."""
  try:
    content = (
      _download(source).decode("utf-8")
      if source.startswith("https://")
      else Path(source).read_text(encoding="utf-8")
    )
    catalog = json.loads(content)
    legacy = (
      historical
      and isinstance(catalog, dict)
      and catalog.get("schema-version") == "bcgov-marketplace-catalog/v1alpha1"
    )
    source_schema = {
      "type": "object",
      "required": ["repository", "revision", "path"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        },
        "revision": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        "path": {"type": "string", "minLength": 1},
      },
    }
    file_schema = {
      "type": "object",
      "required": ["path", "sha256", "size"],
      "properties": {
        "path": {"type": "string", "minLength": 1},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "size": {"type": "integer", "minimum": 0},
      },
    }
    choice_schema = {
      "type": "object",
      "required": [
        "id",
        "extension-id",
        "scope",
        "source",
        "destination",
        "placements",
        "installer",
      ],
      "properties": {
        "id": {"type": "string"},
        "extension-id": {"type": "string"},
        "scope": {"enum": ["project", "global"]},
        "source": source_schema,
        "destination": {"type": "string"},
        "installer": {"type": "string"},
        "placements": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["source", "destination", "sha256"],
            "properties": {
              key: {"type": "string"} for key in ("source", "destination", "sha256")
            },
          },
        },
      },
    }
    schema = {
      "type": "object",
      "required": ["schema-version", "extensions"],
      "properties": {
        "schema-version": {"const": "bcgov-marketplace/v1"},
        "legacy-ids": {"type": "object", "additionalProperties": {"type": "string"}},
        "extensions": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "id",
              "type",
              "lifecycle",
              "display-name",
              "summary",
              "prerequisites",
            ],
            "properties": {
              "id": {
                "type": "string",
                "pattern": (
                  r"^bcgov-public/(skill|instructions|prompt|agent)/"
                  r"[a-z0-9]+(?:-[a-z0-9]+)*$"
                ),
              },
              "type": {"enum": sorted(KNOWN_EXTENSION_TYPES)},
              "lifecycle": {"enum": ["active", "quarantined", "removed"]},
              "display-name": {"type": "string"},
              "summary": {"type": "string"},
              "prerequisites": {"type": "array", "items": {"type": "string"}},
              "legacy-ids": {"type": "array", "items": {"type": "string"}},
              "maintainers": {"type": "array", "items": {"type": "string"}},
              "support": {"type": "string"},
              "notice": {"type": "string"},
              "moved-to": {"type": "string"},
              "install-options": {"type": "array", "items": choice_schema},
              "source": source_schema,
              "files": {"type": "array", "items": file_schema},
              "content-digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            },
            "if": {
              "required": ["install-options"],
              "properties": {"install-options": {"minItems": 1}},
            },
            "then": {"required": ["source", "files", "content-digest"]},
          },
        },
      },
    }
    if legacy:
      # Preserve historical identities/evidence. Only current finite aliases may
      # supply a canonical identity; legacy installer fields grant no authority.
      schema["properties"]["schema-version"] = {
        "const": "bcgov-marketplace-catalog/v1alpha1"
      }
      schema["properties"]["extensions"]["items"]["properties"]["id"] = {
        "type": "string",
        "pattern": r"^bcgov-public/[a-z0-9]+(?:-[a-z0-9]+)*$",
      }
    error = next(Draft202012Validator(schema).iter_errors(catalog), None)
    if error:
      raise FinderError("invalid catalog schema; obtain a published v1 Catalogue")
    records = catalog["extensions"]
    identities = {item["id"] for item in records}
    if len(identities) != len(records) or any(
      not legacy and item["id"].split("/")[1] != item["type"] for item in records
    ):
      raise FinderError("invalid catalog identities")
    if any(
      alias in identities or target not in identities
      for alias, target in catalog.get("legacy-ids", {}).items()
    ):
      raise FinderError("invalid catalog legacy alias mapping")
    if legacy:
      catalog = {
        **catalog,
        "historical-inspection-only": True,
        "extensions": [
          {**record, "install-options": [], "historical-inspection-only": True}
          for record in records
        ],
      }
    return catalog
  except (FinderError, OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise FinderError(f"cannot load catalog {source}: {exc}") from exc


def _tokens(value: str) -> set[str]:
  """Return normalized search terms used by deterministic ranking."""
  return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}


def lookup_extension(catalog: dict, identity: str) -> dict | None:
  """Resolve exact IDs or explicit current aliases without guessing by name."""
  canonical = catalog.get("legacy-ids", {}).get(identity, identity)
  record = next(
    (record for record in catalog["extensions"] if record["id"] == canonical), None
  )
  if record is None:
    return None
  resolution = {
    "requested-id": identity,
    "canonical-id": canonical,
    "alias": identity != canonical,
    "chain": [],
    "installable": record.get("lifecycle") == "active"
    and bool(record.get("install-options")),
  }
  current = record
  visited = set()
  by_id = {item["id"]: item for item in catalog["extensions"]}
  while True:
    if current["id"] in visited:
      resolution["error"] = "malformed replacement cycle; installation unavailable"
      break
    visited.add(current["id"])
    resolution["chain"].append(
      {
        key: current[key]
        for key in ("id", "lifecycle", "notice", "moved-to")
        if key in current
      }
    )
    target = current.get("moved-to")
    if not target:
      resolution["terminal"] = {
        "id": current["id"],
        "lifecycle": current.get("lifecycle", "unknown"),
      }
      break
    resolution["installable"] = False
    if target not in by_id:
      resolution["error"] = "replacement target unavailable; installation unavailable"
      break
    current = by_id[target]
  if "error" in resolution:
    resolution["installable"] = False
  status = record.get("current-status")
  if status and status.get("record"):
    if record.get("historical-inspection-only"):
      resolution["historical-id"] = canonical
      resolution["canonical-id"] = status["record"]["id"]
      resolution["alias"] = canonical != status["record"]["id"]
    current_resolution = status["record"]["resolution"]
    if not current_resolution["installable"]:
      resolution["installable"] = False
  return {**record, "resolution": resolution}


def check_current_notices(catalog: dict, current_source: str) -> dict:
  """Annotate a historical selection with current identity notices or uncertainty."""
  try:
    current = load_catalog(current_source)
    diagnostic = None
  except FinderError as exc:
    current = None
    diagnostic = (
      f"Current status unavailable: {exc}. Historical bytes are not current status."
    )
  records = []
  for record in catalog["extensions"]:
    latest = lookup_extension(current, record["id"]) if current else None
    status = {
      "available": latest is not None,
      "source": current_source,
      "diagnostic": diagnostic
      if current is None
      else (
        None
        if latest
        else "Current status unavailable: identity absent from current Catalogue."
      ),
    }
    if latest:
      status["record"] = {
        key: latest[key]
        for key in ("id", "lifecycle", "notice", "moved-to", "source", "resolution")
        if key in latest
      }
    records.append({**record, "current-status": status})
  return {**catalog, "extensions": records}


def _catalogue_selection(catalog: dict, source: str) -> dict:
  """Describe selected Catalogue evidence separately from package source bytes."""
  if catalog.get("historical-inspection-only"):
    label = "historical pre-v1 snapshot (inspection only)"
  elif (
    catalog.get("release-state") != "published" or catalog.get("version") == "source"
  ):
    label = "Catalogue source (preview)"
  elif source == DEFAULT_CATALOG:
    label = "latest published Catalogue source (full-SHA pin)"
  else:
    label = "selected published snapshot source (full-SHA pin)"
  return {
    "label": label,
    "source": source,
    "snapshot": catalog.get("version"),
    "schema-version": catalog["schema-version"],
  }


def search(catalog: dict, query: str, extension_type: str | None = None) -> list[dict]:
  """Return active matches, or a requested non-active id with its warning."""
  if extension_type is not None and extension_type not in KNOWN_EXTENSION_TYPES:
    raise FinderError(f"unsupported extension type: {extension_type}")
  query_tokens = _tokens(query)
  requested = lookup_extension(catalog, query.strip())
  if query.strip().startswith("bcgov-public/") and requested is None:
    return []
  ranked = []
  for record in catalog["extensions"]:
    is_requested = requested is not None and record["id"] == requested["id"]
    if record["lifecycle"] != "active" and not is_requested:
      continue
    current_record = record.get("current-status", {}).get("record")
    if not is_requested and (
      record.get("moved-to")
      or (
        current_record
        and (
          current_record["lifecycle"] != "active"
          or current_record.get("moved-to")
          or current_record["resolution"].get("error")
        )
      )
    ):
      continue
    if extension_type is not None and record.get("type") != extension_type:
      continue
    if requested is not None and not is_requested:
      continue
    name_tokens = _tokens(
      record["id"]
      + " "
      + record["display-name"]
      + " "
      + " ".join(record.get("legacy-ids", []))
      + " "
      + " ".join(record.get("maintainers", []))
      + " "
      + record.get("support", "")
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
    if score >= MIN_MATCH_SCORE or is_requested:
      why = sorted(query_tokens & (name_tokens | summary_tokens | prerequisite_tokens))
      ranked.append((score, record["id"], why, record))
  ranked.sort(key=lambda item: (-item[0], item[1]))
  return [
    {
      **lookup_extension(catalog, query.strip() if requested else item[1]),
      "match": {"score": item[0], "terms": item[2]},
    }
    for item in ranked[:3]
  ]


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
    raise FinderError(f"cannot download selected data: {exc}") from exc
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
  total = 0
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
      total += entry.file_size
      if (
        entry.file_size > MAX_FILE_BYTES
        or total > MAX_PACKAGE_BYTES
        or len(seen) > MAX_FILES
      ):
        raise FinderError("archive package exceeds bounded file/size limits")
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


def _confirm(message: str, assume_yes: bool) -> None:
  """Require one explicit confirmation unless the calling agent already obtained it."""
  if assume_yes:
    return
  if input(f"{message} Type 'yes' to continue: ").strip().lower() != "yes":
    raise FinderError("operation cancelled")


def _selected_choice(
  catalog: dict,
  identity: str,
  allow_alias: bool = False,
  scope: str = "project",
  *,
  installing: bool = True,
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
  status = record.get("current-status", {})
  current = status.get("record")
  if (
    installing
    and current
    and (
      current["lifecycle"] != "active"
      or current.get("moved-to")
      or current["resolution"].get("error")
    )
  ):
    raise FinderError(
      "current lifecycle prevents installation of this historical pin: "
      + json.dumps(current, sort_keys=True)
      + "; inspect replacement notices and explicitly select an active identity"
    )
  if installing and (record.get("moved-to") or record["resolution"].get("error")):
    raise FinderError(
      "replacement is lookup evidence only; explicitly select its canonical identity"
    )
  if record.get("lifecycle") != "active" or not options:
    raise FinderError(
      "no tested install choice for this type/client or lifecycle; "
      "inspect the notice and source history: "
      + json.dumps(record["resolution"], sort_keys=True)
    )
  choice = next((option for option in options if option["scope"] == scope), None)
  if choice is None:
    raise FinderError(f"no tested VS Code {scope} placement choice")
  if choice["extension-id"] != record["id"] or choice["source"] != record.get("source"):
    raise FinderError("install choice does not match selected identity/source")
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
    installing=getattr(args, "command", "install") == "install",
  )


def _reviewed_install(args, catalog: dict) -> dict:
  """Verify Catalogue bytes and explicitly place the shared native client layout."""
  record, choice = _selection(args, catalog)
  expected_revision = getattr(args, "expected_revision", None)
  if expected_revision and choice["source"]["revision"] != expected_revision:
    raise FinderError(
      "selected source revision changed; review the new plan before confirming"
    )
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
        "action": "overwrite" if previous else "install",
        "migration-approved": getattr(args, "allow_migration", False),
        "current-status": record.get("current-status"),
        "publication": _catalogue_selection(
          catalog, getattr(args, "catalog", DEFAULT_CATALOG)
        )["label"],
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
    action = (
      "Overwrite selected previous native files" if previous else "Install native files"
    )
    _confirm(
      f"{action}: {record['id']} at {choice['source']['revision']}; "
      f"scope={choice['scope']}; destination={project / choice['destination']}; "
      f"migration={getattr(args, 'allow_migration', False)}?",
      args.yes,
    )
    result = place_choice(
      choice,
      staged,
      project,
      confirmed=True,
      previous=previous,
      allow_migration=getattr(args, "allow_migration", False),
    )
    result["targets-exist"] = all(Path(path).is_file() for path in result["installed"])
    result["byte-verification"] = (
      "downloaded inventory/tree digest and installed SHA-256 compared"
    )
    return result


def _verify_selected(args, catalog: dict) -> list[dict]:
  """Compare installed bytes directly with a selected Catalogue revision."""
  _, choice = _selection(args, catalog)
  return verify_choice(choice, _placement_root(args))


def _remove_selected(args, catalog: dict) -> dict:
  """Delete selected native files only after explicit consent and byte comparison."""
  _, choice = _selection(args, catalog)
  print(json.dumps(choice, indent=2, sort_keys=True))
  _confirm(
    f"Delete matching native files at {choice['source']['revision']}; "
    f"scope={choice['scope']}; "
    f"destination={_placement_root(args) / choice['destination']}?",
    args.yes,
  )
  return remove_choice(choice, _placement_root(args), confirmed=True)


def _parser() -> argparse.ArgumentParser:
  """Build the finder command-line interface."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--catalog", default=DEFAULT_CATALOG)
  parser.add_argument("--current-catalog", default=DEFAULT_CATALOG)
  commands = parser.add_subparsers(dest="command", required=True)
  search_parser = commands.add_parser("search")
  search_parser.add_argument("query", nargs="+")
  search_parser.add_argument("--extension-type", choices=sorted(KNOWN_EXTENSION_TYPES))
  install_parser = commands.add_parser("install")
  install_parser.add_argument("id")
  install_parser.add_argument("--project", type=Path, default=Path.cwd())
  install_parser.add_argument("--yes", action="store_true")
  install_parser.add_argument("--allow-alias", action="store_true")
  install_parser.add_argument("--allow-migration", action="store_true")
  install_parser.add_argument("--previous-catalog", type=Path)
  install_parser.add_argument(
    "--expected-revision", help="Refuse a changed selected full source SHA"
  )
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
  commands.add_parser("list")
  return parser


def main(argv: list[str] | None = None) -> int:
  """Run the finder command and return a process exit status."""
  args = _parser().parse_args(argv)
  try:
    catalog = load_catalog(args.catalog, historical=args.catalog != DEFAULT_CATALOG)
    selection = _catalogue_selection(catalog, args.catalog)
    catalog = {
      **catalog,
      "extensions": [
        {**item, "catalogue-selection": selection} for item in catalog["extensions"]
      ],
    }
    if args.catalog != args.current_catalog:
      catalog = check_current_notices(catalog, args.current_catalog)
    if args.command == "search":
      result = search(catalog, " ".join(args.query), args.extension_type)
    elif args.command == "list":
      result = [lookup_extension(catalog, item["id"]) for item in catalog["extensions"]]
    elif args.command == "install":
      result = _reviewed_install(args, catalog)
    elif args.command == "remove":
      result = _remove_selected(args, catalog)
    else:
      result = _verify_selected(args, catalog)
      if not all(item["valid"] for item in result):
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
  except (FinderError, PlacementError, OSError, zipfile.BadZipFile, EOFError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
