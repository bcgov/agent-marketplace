/* Two-file GitHub authoring. Contributed text is always rendered as text. */
"use strict";

(function () {
  const upstream = "https://github.com/bcgov/agent-marketplace";

  function newFile(repository, branch, filename, value) {
    const query = new URLSearchParams({filename, value});
    return `https://github.com/${repository}/new/${encodeURIComponent(branch)}?${query}`;
  }

  function starter(data, fields) {
    const {type, specialty, name, summary, maintainer, base = "main"} = fields;
    if (!Object.hasOwn(data.types, type)) throw Error("Choose a supported Extension type.");
    if (!data.specialties.some(item => item.id === specialty)) throw Error("Choose a registered Specialty or Community.");
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name) || name.length > 64) {
      throw Error("Use a lowercase, hyphen-separated name of at most 64 characters.");
    }
    const identity = `bcgov-public/${type}/${name}`;
    if (data.reserved.includes(identity)) {
      throw Error(`${identity} is unavailable. Choose another name; the same type/name is reserved across all Specialties, including retired Extensions.`);
    }
    if (!/^[a-z\d](?:[a-z\d-]{0,37}[a-z\d])?$/i.test(maintainer)) {
      throw Error("Enter your GitHub username without @ (an individual maintainer).");
    }
    if (!summary.trim() || summary.length > 1024 || /[<>\r\n]/.test(summary)) {
      throw Error("Add a one-line summary of at most 1,024 characters without angle brackets.");
    }
    const definition = data.types[type];
    const directory = `${definition.directory}/${specialty}/${name}`;
    const filename = definition.filename.replace("{name}", name);
    const native = definition.native.replaceAll("__EXTENSION_NAME__", name)
      .replaceAll("__SUMMARY__", JSON.stringify(summary));
    const manifest = `maintainers:\n  - ${JSON.stringify("@" + maintainer)}\ncapabilities: none\n`;
    return {
      identity, native, manifest,
      nativePath: `${directory}/${filename}`,
      manifestPath: `${directory}/bcgov-extension.yaml`,
      startUrl: newFile("bcgov/agent-marketplace", base, `${directory}/${filename}`, native),
    };
  }

  if (typeof module !== "undefined") module.exports = {starter, newFile};
  if (typeof document === "undefined") return;

  async function initialize() {
    const form = document.getElementById("browser-starter");
    if (!form) return;
    const status = document.getElementById("starter-status");
    const output = document.getElementById("starter-output");
    try {
      const response = await fetch("assets/contribute.json");
      if (!response.ok) throw Error("Starter data could not be loaded. Reload the page or use the linked repository contribution guide.");
      const data = await response.json();
      const query = new URLSearchParams(location.search);
      const base = query.get("base") || "main";
      document.getElementById("contribution-base").textContent = base;
      document.getElementById("base-source").href = `${upstream}/tree/${encodeURIComponent(base)}`;
      const choices = document.getElementById("extension-specialty");
      const registry = document.getElementById("specialty-registry");
      for (const item of data.specialties) {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item["display-name"] + (item["owner-team"] ? ` — ${item["owner-team"]}` : " (start here)");
        choices.append(option);
        const row = document.createElement("li");
        row.textContent = `${item["display-name"]}: ${item.description} ` +
          (item["owner-team"] ? `Owner ${item["owner-team"]}; review rule: ${item["review-rule"]}. Human review required.` : "Community review route depends on the checks and eligibility below.");
        registry.append(row);
      }
      for (const key of ["type", "specialty", "name"]) {
        const field = form.elements[key];
        if (query.has(key)) field.value = query.get(key);
      }
      function refresh() {
        output.hidden = true;
        for (const id of ["start-native", "add-manifest", "open-pr"]) document.getElementById(id).removeAttribute("href");
        try {
          const fields = Object.fromEntries(new FormData(form));
          const result = starter(data, {...fields, base});
          for (const [id, text] of Object.entries({
            "native-path": result.nativePath, "native-stub": result.native,
            "manifest-path": result.manifestPath, "manifest-stub": result.manifest,
            "extension-identity": result.identity,
          })) document.getElementById(id).textContent = text;
          document.getElementById("start-native").href = result.startUrl;
          const owner = data.specialties.find(item => item.id === fields.specialty);
          document.getElementById("selected-review").textContent = owner["owner-team"]
            ? `Human review: ${owner["owner-team"]} (${owner["review-rule"]}). Mark the PR ready for review so GitHub can request its owners.`
            : "Community: CI checks eligibility; automatic merging may be disabled. A passing review hold needs a maintainer's review.";
          const repo = document.getElementById("working-repository").value.trim();
          const branch = document.getElementById("working-branch").value.trim();
          const branchStatus = document.getElementById("branch-status");
          if (/^[\w-]+\/[\w.-]+$/.test(repo) && branch && !/[\s?#]/.test(branch)) {
            document.getElementById("add-manifest").href = newFile(repo, branch, result.manifestPath, result.manifest);
            document.getElementById("open-pr").href = `${upstream}/compare/${encodeURIComponent(base)}...${encodeURIComponent(repo.split("/")[0])}:${encodeURIComponent(repo.split("/")[1])}:${encodeURIComponent(branch)}?expand=1`;
            branchStatus.textContent = `Use the existing branch ${branch} in ${repo} for file 2. Confirm these match the native file's location before continuing.`;
          } else {
            branchStatus.textContent = "After committing file 1, enter the actual fork/repository and branch below to enable the Manifest and PR links.";
          }
          status.textContent = "Starter ready. Edit the native body and declare actual capabilities before committing.";
          output.hidden = false;
        } catch (error) {
          status.textContent = error.message;
        }
      }
      form.addEventListener("input", refresh);
      form.addEventListener("change", refresh);
      form.addEventListener("submit", event => { event.preventDefault(); refresh(); });
      document.getElementById("branch-details").addEventListener("input", refresh);
      refresh();
    } catch (error) {
      status.textContent = error.message;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
