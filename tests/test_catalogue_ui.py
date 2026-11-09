"""Catalogue filtering and detail rendering through the public static UI seam."""

import json
import shutil
import subprocess

from test_marketplace import ROOT, _package, _root, m


def ui(method, catalog, *args):
  """Call the same dependency-free renderer used by the browser."""
  result = subprocess.run(
    [
      "node",
      "-e",
      "const ui = require(process.argv[1]); "
      "const [method, ...args] = JSON.parse(process.argv[2]); "
      "console.log(JSON.stringify(ui[method](...args)));",
      str(ROOT / "docs/assets/catalogue.js"),
      json.dumps([method, catalog, *args]),
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=False,
  )
  assert result.returncode == 0, result.stderr
  return json.loads(result.stdout)


def record(name="water", **fields):
  """Provide an inert Catalogue record with known source-history dates."""
  return {
    "id": f"bcgov-public/skill/{name}",
    "display-name": name.title(),
    "summary": "Inspect watershed guidance",
    "maintainers": ["river-owner"],
    "legacy-ids": [f"legacy/{name}"],
    "type": "skill",
    "specialty": "water",
    "lifecycle": "active",
    "source": {"added": "2026-10-28T12:00:00Z", "updated": None},
    **fields,
  }


def test_search_and_combined_filters_use_source_history_and_explicit_ids():
  """Names, summary, canonical/legacy IDs and maintainers combine with filters."""
  catalog = {"extensions": [record(), record("old", lifecycle="removed")]}
  for query in (
    "WATER",
    "watershed",
    "bcgov-public/skill/water",
    "legacy/water",
    "river-owner",
  ):
    matches = ui(
      "filterCatalog",
      catalog,
      {"query": query, "type": "skill", "specialty": "water", "added": True},
      "2026-11-03T12:00:00Z",
    )
    assert matches[0]["id"] == "bcgov-public/skill/water"
  assert ui("filterCatalog", catalog, {}, "2026-11-03T12:00:00Z") == [record()]
  assert ui("filterCatalog", catalog, {"query": "legacy/old"}) == [
    record("old", lifecycle="removed")
  ]
  assert ui("filterCatalog", catalog, {"type": "prompt"}) == []
  for added in (None, "2026-10-27T11:59:59Z", "2026-11-04T00:00:00Z"):
    assert (
      ui(
        "filterCatalog",
        {"extensions": [record(source={"added": added})]},
        {"added": True},
        "2026-11-03T12:00:00Z",
      )
      == []
    )


def test_direct_alias_and_replacement_chain_keep_notices_without_installing():
  """Finite aliases and moved-to chains require explicit replacement navigation."""
  a, b, c = (f"bcgov-public/skill/{name}" for name in ("a", "b", "c"))
  catalog = {
    "legacy-ids": {"old/a": a},
    "extensions": [
      record("a", lifecycle="removed", notice="A was retired", **{"moved-to": b}),
      record("b", lifecycle="removed", notice="B changed identity", **{"moved-to": c}),
      record("c", lifecycle="quarantined", notice="C is under investigation"),
    ],
  }
  resolved = ui("resolveExtension", catalog, "old/a")
  assert [item["id"] for item in resolved["chain"]] == [a, b, c]
  assert resolved["terminal"]["lifecycle"] == "quarantined"
  detail = ui("renderDetail", catalog, "old/a")
  for text in (
    "Legacy ID",
    "A was retired",
    "B changed identity",
    "C is under investigation",
    "Terminal replacement is quarantined",
  ):
    assert text in detail
  assert 'href="#bcgov-public%2Fskill%2Fb"' in detail
  assert "native-install-choice" not in detail
  assert "Read exact source" not in detail  # Removed is a tombstone only.
  assert ui("resolveExtension", catalog, "invented/a")["error"] == "Extension not found"
  quarantine = ui("renderDetail", catalog, c)
  assert "Source may contain withdrawn guidance" in quarantine
  assert "native-install-choice" not in quarantine
  catalog["extensions"][-1]["lifecycle"] = "active"
  assert "Choose a replacement explicitly" in ui("renderDetail", catalog, a)
  assert "native-install-choice" not in ui("renderDetail", catalog, a)


def test_detail_exposes_exact_choice_bytes_source_and_honest_evidence(tmp_path):
  """The light detail consumes actual shared choices with no invented review/date."""
  root = _root(tmp_path)
  package = _package(root)
  (package / "SKILL.md").write_text(
    "---\nname: demo\ndescription: Useful guidance\n---\n# Demo\n", encoding="utf-8"
  )
  catalog, _ = m.build_catalog(root, revision="b" * 40)
  detail = ui("renderDetail", catalog, "bcgov-public/skill/demo")
  choice = catalog["extensions"][0]["install-options"][0]
  for value in (
    choice["source-url"],
    choice["placements"][0]["sha256"],
    choice["placements"][0]["destination"],
    catalog["engine"],
    "Source updated",
    "Not recorded",
    "Review rule",
    "not proof of a named review",
    "Author-declared harness readiness",
    "not a runtime compatibility test",
    "Catalogue source (source preview)",
    "Read exact source",
    "Declared access",
  ):
    assert value in detail
  assert "1970" not in detail
  assert "Latest published" not in detail
  catalog["extensions"][0]["policy-route"] = {
    "type": "specialty-review",
    "owner-team": "@bcgov/water",
  }
  catalog["extensions"][0]["specialty"] = "water"
  catalog["specialties"] = [
    {
      "id": "water",
      "display-name": "Watersheds",
      "display-flair": "River",
      "review-rule": "owning-team",
      "owner-team": "@bcgov/water",
    }
  ]
  detail = ui("renderDetail", catalog, "bcgov-public/skill/demo")
  assert "owning-team" in detail and "@bcgov/water" in detail
  assert "Named reviewer evidence: Not recorded" in detail
  catalog["extensions"][0]["checks"]["content-digest"] = "sha256:wrong"
  assert "Evidence does not match" in ui(
    "renderDetail", catalog, "bcgov-public/skill/demo"
  )
  assert "native-install-choice" not in ui(
    "renderDetail", catalog, "bcgov-public/skill/demo"
  )


def test_static_build_keeps_site_snapshot_release_and_deployment_independent(tmp_path):
  """A docs-only build links actual source/run separately from an older asset."""
  output = tmp_path / "site"
  shutil.copytree(ROOT / "docs", output)
  catalog = {
    "version": "catalog-2026.10.01",
    "revision": "a" * 40,
    "release-state": "published",
    "extensions": [],
    "repository": "https://github.com/bcgov/agent-marketplace",
  }
  metadata = {
    "catalogue": {
      "tag": catalog["version"],
      "source": catalog["revision"],
      "asset-digest": "sha256:123",
      "release": {
        "published_at": "2026-10-01T12:00:00Z",
        "url": "https://github.com/bcgov/agent-marketplace/releases/tag/catalog-2026.10.01",
      },
    },
    "site": {"source": "b" * 40, "run": "12345", "attempt": "2"},
  }
  (output / "assets/catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
  (output / "assets/site-build.json").write_text(json.dumps(metadata), encoding="utf-8")
  (output / "_generated").mkdir(exist_ok=True)
  (output / "_generated/catalog-cards.html").write_text("", encoding="utf-8")
  subprocess.run(
    ["node", str(ROOT / "docs/build-pages.js"), str(output)],
    check=True,
    capture_output=True,
  )
  page = (output / "catalog.html").read_text(encoding="utf-8")
  for href in (
    "/tree/" + "a" * 40,
    "/tree/" + "b" * 40,
    "/actions/runs/12345/attempts/2",
    "/releases/tag/catalog-2026.10.01",
    "/deployments",
  ):
    assert href in page
  assert "Successful deployment: Not recorded for this build" in page
  assert 'id="catalog-added"' in page and "assets/catalogue.js" in page
  catalog["version"] = "source"
  metadata["catalogue"]["release"] = None
  (output / "assets/catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
  (output / "assets/site-build.json").write_text(json.dumps(metadata), encoding="utf-8")
  subprocess.run(
    ["node", str(ROOT / "docs/build-pages.js"), str(output)],
    check=True,
    capture_output=True,
  )
  page = (output / "catalog.html").read_text(encoding="utf-8")
  assert "Source preview" in page and "/releases/tag/source" not in page
