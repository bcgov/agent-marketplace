# Historical decision evidence

These seven research notes and ten prototype artifacts preserve decision aids from October–November 2026. They are historical evidence, not current product instructions. The [locked v1 spec](https://github.com/bcgov/agent-marketplace/issues/7), its amendments and [four ADRs](../adr/0001-author-declared-harness-readiness.md) govern current behavior. The archive is outside site navigation/search. Prototype artifacts are inert `.txt` source snapshots, including HTML, scripts and preview data; they are not runnable product demos.

[Exact preservation manifest](preservation.json) records original branch/ref, commit, path, Git blob, SHA-256 and destination for every file. Six research files and all ten prototype artifacts retain exact bytes. `fork-pr-automerge.md` only repairs historical relative repository links to immutable parent `e11a37b56a56a55b5721bb9fa5abac259e65012b`; original and preserved hashes are recorded separately and original bytes remain in the complete bundle. The scanner note retains its sibling link. Prototype earlier variants and all unique branch commits remain in the full eight-ref history backup; extracted tips are not a complete history substitute.

| Preserved file | Original commit | Original Git blob |
| --- | --- | --- |
| [catalog.html.txt](prototypes/catalogue-personality/docs/_pages/catalog.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `fe07951547a7decc6ef272448a04655074d683ea` |
| [catalog-detail-prototype.html.txt](prototypes/catalogue-personality/docs/_pages/catalog-detail-prototype.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `cb3ac3aeaed2b043a868749632cd8400d2160b0e` |
| [catalog-personality-prototype.html.txt](prototypes/catalogue-personality/docs/_pages/catalog-personality-prototype.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `c19de5000183e6ebf90396622e6ff3d0a7b18e89` |
| [catalog.html.txt](prototypes/catalogue-personality/docs/catalog.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `06e3c615af4598616b58d421d80214b3f413888c` |
| [catalog-detail-prototype.html.txt](prototypes/catalogue-personality/docs/catalog-detail-prototype.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `17289737447d748c25a4064045d563eaff601391` |
| [catalog-personality-prototype.html.txt](prototypes/catalogue-personality/docs/catalog-personality-prototype.html.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `11817875e774a004334e107e4c95c88e5757a1ed` |
| [skill-previews-prototype.json.txt](prototypes/catalogue-personality/docs/assets/skill-previews-prototype.json.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `61cbb9a8decb1ac28e87ea4355523fe0785c860d` |
| [generate-skill-previews-prototype.js.txt](prototypes/catalogue-personality/docs/generate-skill-previews-prototype.js.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `be52f177aaf3636a257e6e9591cb6b65932c3695` |
| [build.sh.txt](prototypes/catalogue-personality/docs/build.sh.txt) | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | `479497efd594d740453e9720d2de951f08ef2b5e` |
| [marketplace-source-benchmark.md](marketplace-source-benchmark.md) | `dd143a4dd2bb779b21b51bd4b3d96bd81f29b879` | `d6d23a0f54d6d3b4eb5286ce16cc8e34473bf9fc` |
| [security-check-prototype.html.txt](prototypes/security-check-flow/docs/demos/security-check-prototype.html.txt) | `dd143a4dd2bb779b21b51bd4b3d96bd81f29b879` | `8373a8c104fb2373a08e1201ac3ad0f18566321e` |
| [codex-patch-inventory.md](codex-patch-inventory.md) | `acaad6023466cd8fc2d255469aa8420d0f1d4f8a` | `33f22e3607c395d042f648061266e3709237f5bd` |
| [extension-level-evidence-findings.md](extension-level-evidence-findings.md) | `761c7b5f4840da170e29e3727d11482b528fc066` | `fc47aafce6fb7d0396b8cfa0abbc114a84cbf5b9` |
| [fork-pr-automerge.md](fork-pr-automerge.md) | `5c8e805b58b976de83f09037cc6ef016a51330b1` | `2ebc962c4b7639c5acd7bb94de012f571946c121` |
| [native-install-formats.md](native-install-formats.md) | `af91f4a80e011bfee8061636f9342c4ed7e544b8` | `6b4524fd81220f00aadbabc596b62273fcdc0faa` |
| [replaceable-skill-scanner-findings.md](replaceable-skill-scanner-findings.md) | `3005d63679cab27c99a9461de8a273bf9353340e` | `12597dbecf025444a6ce817f3782da662dbf3bd3` |
| [scan-extensibility-findings.md](scan-extensibility-findings.md) | `81dcee04714260754018d351bc0df30e18f253cd` | `3c70e4d3b0b5bb188cdf43a1ab83e6e9e1bb7053` |

## Decisions and later amendments

- [#9](https://github.com/bcgov/agent-marketplace/issues/9): Codex patch inventory; the original macOS `working/agent-marketplace-changes.patch` and `working/APPLY-CHANGES.txt` are unavailable. No tracked working path/history or matching local/remote branch was found. This does not claim those original bytes were backed up or deleted.
- [#10](https://github.com/bcgov/agent-marketplace/issues/10): fork research; later #12/#29/#43 supersede account-age, token and broad-bypass ideas. Built-in actor feasibility is still pending.
- [#11](https://github.com/bcgov/agent-marketplace/issues/11): native format research; #17/#47 define tested choices. Plugin packaging is deferred #50.
- [#13](https://github.com/bcgov/agent-marketplace/issues/13) and [#21](https://github.com/bcgov/agent-marketplace/issues/21): scanner research and its latest addendum; scanner pilots deferred #37. Findings do not certify safety.
- [#18](https://github.com/bcgov/agent-marketplace/issues/18): Catalogue personality/detail snapshots. Earlier explicitly discussed variants remain in bundled history; current Catalogue omits historical native previews.
- [#22](https://github.com/bcgov/agent-marketplace/issues/22): security check storyboard. Prototype tip also has unmerged glossary/copilot instructions retained in the bundle, not imported as current product code.
- [#23](https://github.com/bcgov/agent-marketplace/issues/23), #24/#55: extension evidence and the benchmark unexpectedly stored on the security prototype branch. Historical external-source evidence is not enabled v1 External-source discovery.

## Preservation gate

[Exact cleanup scope](ref-cleanup.md) remains **pending**. These files must reach retained main and affected decision records must receive stable current-main preservation references before any named remote ref is deleted. A prepared integration branch, bare commit URL or closed PR ref alone does not satisfy that gate. The complete verified bundle has SHA-256 `ad42a6a0a6e618b73c844659a80870a4fd2136502fb6eb136e7194835dc76192`; its durable operator backup location is recorded privately with the handoff. No remote ref deletion is claimed here.
