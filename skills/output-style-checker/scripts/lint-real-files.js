"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const skillRoot = path.resolve(__dirname, "..");
const manifestPath = path.join(skillRoot, "regression", "manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

const missing = manifest.filter((entry) => !fs.existsSync(entry.path));
if (missing.length > 0) {
  console.error("Missing regression files:");
  for (const entry of missing) {
    console.error(`- ${entry.label}: ${entry.path}`);
  }
  process.exit(1);
}

console.log("Regression targets:");
for (const entry of manifest) {
  console.log(`- ${entry.label}: ${entry.path}`);
}
console.log("");

const result = spawnSync(
  "npx",
  ["textlint", "--rulesdir", "./rules", ...manifest.map((entry) => entry.path)],
  {
    cwd: skillRoot,
    stdio: "inherit"
  }
);

process.exit(result.status === null ? 1 : result.status);
