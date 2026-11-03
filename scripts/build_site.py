"""Build a static site around exact Catalogue bytes in a selected output directory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import marketplace
from publication import canonical, digest, git


def build_site(
  root: Path, output: Path, content: bytes, site: dict, release: dict | None = None
) -> Path:
  """Validate the rendering contract and keep snapshot/site/event coordinates apart."""
  catalog = json.loads(content)
  if catalog.get("schema-version") != "bcgov-marketplace/v1" or not isinstance(
    catalog.get("extensions"), list
  ):
    raise ValueError("Site requires the bcgov-marketplace/v1 Catalogue contract")
  authored = root / "docs"
  output.mkdir(parents=True, exist_ok=True)
  if output.resolve() != authored.resolve():
    for source in authored.rglob("*"):
      relative = source.relative_to(authored)
      if not source.is_file() or source.is_symlink():
        continue
      if (
        (len(relative.parts) == 1 and source.suffix == ".html")
        or relative.parts[0] == "_generated"
        or relative.as_posix()
        in {
          "assets/catalog.json",
          "assets/search-index.json",
          "assets/site-build.json",
          "assets/contribute.json",
        }
      ):
        continue
      target = output / relative
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copyfile(source, target)
  assets = output / "assets"
  assets.mkdir(exist_ok=True)
  (assets / "catalog.json").write_bytes(content)
  metadata = {
    "catalogue": {
      "tag": catalog["version"],
      "source": catalog["revision"],
      "asset-digest": digest(content),
      "release": release,
    },
    "site": site,
  }
  (assets / "site-build.json").write_bytes(canonical(metadata))
  generated = output / "_generated"
  generated.mkdir(exist_ok=True)
  (generated / "catalog-cards.html").write_text(
    marketplace.render_catalog_cards(catalog),
    encoding="utf-8",
  )
  browser = root / "scripts/browser_contribution.py"
  if browser.exists():
    subprocess.run(
      [
        "uv",
        "run",
        "python",
        str(browser),
        "--root",
        str(root),
        "--output",
        str(assets / "contribute.json"),
      ],
      check=True,
      cwd=root,
    )
  for script in ("build-pages.js", "generate-search-index.js"):
    subprocess.run(["node", str(root / "docs" / script), str(output)], check=True)
  if (assets / "catalog.json").read_bytes() != content:
    raise ValueError("Site build altered immutable Catalogue bytes")
  return output


def main() -> None:
  """Build a local preview or render a selected immutable Catalogue asset."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
  parser.add_argument("--output", type=Path)
  parser.add_argument("--catalog", type=Path)
  args = parser.parse_args()
  root = args.root.resolve()
  content = (
    args.catalog.read_bytes()
    if args.catalog
    else canonical(marketplace.build_catalog(root)[0])
  )
  build_site(
    root,
    (args.output or root / "docs").resolve(),
    content,
    {"source": git(root, "rev-parse", "HEAD").strip(), "run": "local"},
  )


if __name__ == "__main__":
  main()
