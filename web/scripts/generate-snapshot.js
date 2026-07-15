#!/usr/bin/env node
/**
 * Wrapper that calls the Python snapshot generator.
 * Invoked by `npm run build` when NEXT_PUBLIC_DEMO_MODE=true.
 */

const { execSync } = require("child_process");
const path = require("path");

const repo = path.join(__dirname, "..", "..");
const script = path.join(__dirname, "generate-snapshot.py");

console.log("[reentry] Generating demo snapshot...");
try {
  execSync(`python3 "${script}"`, {
    stdio: "inherit",
    cwd: repo,
  });
} catch (err) {
  console.error("[reentry] Snapshot generation failed:", err.message);
  process.exit(1);
}
