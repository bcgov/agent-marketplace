"""Exercise the documentation link checker through its public command line."""

import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

CHECKER = Path(__file__).parents[1] / "scripts" / "check_links.py"


class Navigation(HTMLParser):
  """Collect primary navigation destinations from built product pages."""

  def __init__(self, content):
    """Parse the built document."""
    super().__init__()
    self.primary = False
    self.targets = []
    self.feed(content)

  def handle_starttag(self, tag, attrs):
    """Collect links only inside the primary navigation."""
    values = dict(attrs)
    if tag == "nav" and values.get("aria-label") == "Primary":
      self.primary = True
    if self.primary and tag == "a":
      self.targets.append(values.get("href"))

  def handle_endtag(self, tag):
    """Stop collecting at the navigation boundary."""
    if tag == "nav":
      self.primary = False


def test_checker_reports_missing_files_and_anchors(tmp_path):
  """A readable diagnostic identifies each broken local destination."""
  (tmp_path / "README.md").write_text(
    "[missing](gone.md)\n[section](guide.md#unknown)\n", encoding="utf-8"
  )
  (tmp_path / "guide.md").write_text("# Existing section\n", encoding="utf-8")
  result = subprocess.run(
    [sys.executable, str(CHECKER), str(tmp_path)], capture_output=True, text=True
  )
  assert result.returncode == 1
  assert "README.md: gone.md: missing file" in result.stdout
  assert "README.md: guide.md#unknown: missing anchor" in result.stdout


def test_checker_accepts_real_html_and_markdown_navigation(tmp_path):
  """Decoded links, repeated headings and HTML anchors resolve without network."""
  (tmp_path / "README.md").write_text(
    "[guide](guide%20one.md#same-1)\n[site](index.html#native)\n"
    "[external](https://example.invalid/remote)\n```md\n[example](absent)\n```\n",
    encoding="utf-8",
  )
  (tmp_path / "guide one.md").write_text("# Same\n# Same\n", encoding="utf-8")
  (tmp_path / "index.html").write_text(
    '<h1 id="native">Native</h1><a href="/README.md?view=1">Guide</a>',
    encoding="utf-8",
  )
  for option in ([], ["--site"]):
    result = subprocess.run(
      [sys.executable, str(CHECKER), str(tmp_path), *option],
      capture_output=True,
      text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken" in result.stdout


def test_build_exposes_three_guides_and_retains_catalogue(tmp_path):
  """A complete isolated build provides working guide navigation and data UI."""
  root = CHECKER.parents[1]
  subprocess.run(
    [sys.executable, str(root / "scripts/build_site.py"), "--output", str(tmp_path)],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
  )
  assert {path.name for path in tmp_path.glob("*.html")} == {
    "index.html",
    "catalog.html",
    "install.html",
    "contribute.html",
    "reference.html",
  }
  for page in ("install.html", "contribute.html", "reference.html", "catalog.html"):
    content = (tmp_path / page).read_text(encoding="utf-8")
    navigation = Navigation(content).targets
    assert navigation[:5] == [
      "index.html",
      "catalog.html",
      "install.html",
      "contribute.html",
      "reference.html",
    ]
  assert (tmp_path / "assets/catalog.json").is_file()
  assert (tmp_path / "assets/contribute.json").is_file()
  checked = subprocess.run(
    [sys.executable, str(CHECKER), str(tmp_path), "--site"],
    capture_output=True,
    text=True,
  )
  assert checked.returncode == 0, checked.stdout + checked.stderr
