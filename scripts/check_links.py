"""Check internal file and anchor links in maintained Markdown and built HTML."""

from __future__ import annotations

import argparse
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Document(HTMLParser):
  """Read real HTML links and explicit anchors without executing scripts."""

  def __init__(self, content: str):
    """Parse one document into links and anchors."""
    super().__init__()
    self.links = []
    self.anchors = set()
    self.feed(content)

  def handle_starttag(self, tag, attrs):
    """Collect explicit IDs and resource destinations."""
    values = dict(attrs)
    if values.get("id"):
      self.anchors.add(values["id"])
    if tag == "a" and values.get("name"):
      self.anchors.add(values["name"])
    for key in ("href", "src"):
      if values.get(key):
        self.links.append(values[key])


def read_document(path: Path) -> Document:
  """Extract links and GitHub-style Markdown heading anchors."""
  content = path.read_text(encoding="utf-8")
  if path.suffix == ".md":
    content = re.sub(r"^```.*?^```[^\n]*", "", content, flags=re.M | re.S)
    headings = re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", content, re.M)
    content = re.sub(r"`[^`\n]+`", "", content)
  document = Document(content)
  if path.suffix == ".md":
    document.links.extend(
      match.group(1) or match.group(2)
      for match in re.finditer(
        r"!?\[[^\]\n]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)", content
      )
    )
    references = dict(re.findall(r"^\[([^]]+)\]:\s*<?([^\s>]+)>?", content, re.M))
    for label, reference in re.findall(r"\[([^]]+)\]\[([^]]*)\]", content):
      if (reference or label) in references:
        document.links.append(references[reference or label])
    counts = {}
    for heading in headings:
      slug = re.sub(r"[^\w\- ]", "", unescape(heading).lower()).replace(" ", "-")
      count = counts.get(slug, 0)
      counts[slug] = count + 1
      document.anchors.add(f"{slug}-{count}" if count else slug)
  return document


def main() -> int:
  """Report all local link errors and return a failing exit status."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("root", type=Path)
  parser.add_argument("--site", action="store_true", help="Check built site HTML only")
  args = parser.parse_args()
  root = args.root.resolve()
  if not root.is_dir():
    parser.error("root must be an existing directory")
  documents = {}
  for path in root.rglob("*"):
    relative = path.relative_to(root)
    if any(part.startswith(".") for part in relative.parts):
      continue
    # Archives preserve historical source, including intentionally obsolete links.
    archived = (
      relative.parts[:2] == ("docs", "research") or relative.parts[0] == "research"
    )
    if archived and path.name not in {"README.md", "ref-cleanup.md"}:
      continue
    if path.is_file() and path.suffix in ({".html"} if args.site else {".md"}):
      if args.site and relative.parts[0] in {"_pages", "_partials", "_generated"}:
        continue
      documents[path] = read_document(path)
  failures = []
  checked = 0
  for path, document in documents.items():
    for link in document.links:
      parts = urlsplit(link)
      if parts.scheme or parts.netloc:
        continue
      checked += 1
      target = (
        (root / unquote(parts.path).lstrip("/"))
        if parts.path.startswith("/")
        else (path.parent / unquote(parts.path))
      )
      target = target.resolve() if parts.path else path
      if not target.exists():
        failures.append(f"{path.relative_to(root)}: {link}: missing file")
      elif parts.fragment and target.suffix in {".md", ".html"}:
        other = documents.get(target) or read_document(target)
        if unquote(parts.fragment) not in other.anchors:
          failures.append(f"{path.relative_to(root)}: {link}: missing anchor")
  for failure in failures:
    print(failure)
  print(f"Checked {checked} internal links; {len(failures)} broken")
  return int(bool(failures))


if __name__ == "__main__":
  raise SystemExit(main())
