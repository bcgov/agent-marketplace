#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const docsDir = __dirname;
const root = path.resolve(docsDir, "..");
const catalog = JSON.parse(fs.readFileSync(path.join(docsDir, "assets/catalog.json"), "utf8"));
const previews = {};

function list(text, numbered = false, limit = 5) {
  const lines = text.split("\n");
  const entries = [];
  for (const line of lines) {
    const start = line.match(numbered ? /^\d+\.\s+(.+)/ : /^-\s+(.+)/);
    if (start) {
      if (entries.length === limit) break;
      entries.push(start[1]);
    } else if (entries.length && /^\s{2,}\S/.test(line)) {
      entries[entries.length - 1] += ` ${line.trim()}`;
    }
  }
  return entries;
}

for (const record of catalog.extensions) {
  if (record.type !== "skill") continue;
  const file = record.files.find(item => item.path === "SKILL.md");
  if (!file || !record.source?.path) {
    throw new Error(`Missing SKILL.md metadata for ${record.id}`);
  }
  const source = fs.readFileSync(path.join(root, record.source.path, "SKILL.md"));
  const digest = crypto.createHash("sha256").update(source).digest("hex");
  if (digest !== file.sha256) {
    throw new Error(`Published SKILL.md digest does not match ${record.id}`);
  }
  const markdown = source.toString("utf8").replace(/^---\n[\s\S]*?\n---\n/, "").trimStart();
  const sections = Object.fromEntries(markdown.split(/^## /m).slice(1).map(block => {
    const [heading, ...body] = block.split("\n");
    return [heading, body.join("\n")];
  }));
  const firstSection = markdown.split(/^## /m)[0].replace(/^# .+\n/, "").trim();
  const intro = firstSection.split(/\n\s*\n/)[0] || "";
  previews[record.id] = {
    title: markdown.match(/^# (.+)$/m)?.[1] || record["display-name"],
    intro: intro.replace(/\s*\n\s*/g, " "),
    useWhen: list(sections["Use When"] || ""),
    dontUseWhen: list(sections["Don't Use When"] || ""),
    workflow: list(sections.Workflow || "", true, 3),
    digest,
  };
}

fs.writeFileSync(
  path.join(docsDir, "assets/skill-previews-prototype.json"),
  `${JSON.stringify(previews, null, 2)}\n`,
);
