#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const docsDir = path.resolve(process.argv[2] || __dirname);
const pagesDir = path.join(docsDir, "_pages");
const partialsDir = path.join(docsDir, "_partials");
const generatedDir = path.join(docsDir, "_generated");
const now = new Date();
const year = String(now.getFullYear());
const month = `${year}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const date = `${month}-${String(now.getDate()).padStart(2, "0")}`;
const headerTemplate = fs.readFileSync(path.join(partialsDir, "header.html"), "utf8");
const footerTemplate = fs.readFileSync(path.join(partialsDir, "footer.html"), "utf8");

function replaceAll(value, token, replacement) {
  return value.split(token).join(replacement);
}

for (const filename of fs.readdirSync(pagesDir).sort()) {
  if (!filename.endsWith(".html")) {
    continue;
  }
  if (filename.startsWith("_")) {
    console.log(`  Skipping template: ${filename}`);
    continue;
  }

  console.log(`  Building: ${filename}`);
  const source = fs.readFileSync(path.join(pagesDir, filename), "utf8");
  const title = source.match(/^<!--\s*TITLE:\s*(.*?)\s*-->$/m)?.[1] || "Documentation";
  const nav = source.match(/^<!--\s*NAV:\s*([A-Za-z0-9_]+)\s*-->$/m)?.[1];
  let content = source.replace(/^<!--.*-->\s*$/gm, "").trim();
  if (content.includes("{{CATALOG_CARDS}}")) {
    const cards = fs.readFileSync(
      path.join(generatedDir, "catalog-cards.html"),
      "utf8",
    );
    content = replaceAll(content, "{{CATALOG_CARDS}}", cards.trim());
  }

  let header = replaceAll(headerTemplate, "{{PAGE_TITLE}}", title);
  if (nav) {
    header = replaceAll(header, `{{NAV_${nav.toUpperCase()}}}`, "active");
  }
  header = header.replace(/\{\{NAV_[A-Z_]+\}\}/g, "");

  let footer = replaceAll(footerTemplate, "{{YEAR}}", year);
  content = replaceAll(content, "{{YEAR}}", year);
  content = replaceAll(content, "{{CURRENT_MONTH}}", month);
  content = replaceAll(content, "{{CURRENT_DATE}}", date);

  const output = `${header.trimEnd()}\n${content}\n${footer.trimStart()}`;
  fs.writeFileSync(path.join(docsDir, filename), output, "utf8");
}
