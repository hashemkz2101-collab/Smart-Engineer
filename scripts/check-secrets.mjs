// Fails when a tracked file looks like it contains a credential (SEC-005).
// This is a cheap guard against accidents, not a full secret scanner: it only knows a
// few well-known token shapes and quoted assignments of long values to secret-like names.
// A line carrying the marker `secret-scan:allow` is skipped (use it for test fixtures).
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const RULES = [
  { name: "private key block", pattern: /-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----/ },
  { name: "AWS access key id", pattern: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/ },
  { name: "GitHub token", pattern: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/ },
  { name: "GitHub fine-grained token", pattern: /\bgithub_pat_[A-Za-z0-9_]{40,}\b/ },
  { name: "Slack token", pattern: /\bxox[abprs]-[A-Za-z0-9-]{10,}\b/ },
  { name: "Google API key", pattern: /\bAIza[0-9A-Za-z_-]{35}\b/ },
  { name: "Stripe live key", pattern: /\b[sr]k_live_[0-9A-Za-z]{20,}\b/ },
  {
    name: "secret-like assignment",
    pattern:
      /\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)\w*["']?\s*[:=]\s*["'][^"'\s$<{][^"'\s]{15,}["']/i,
  },
];

const ALLOW_MARKER = "secret-scan:allow";
const SKIPPED_FILES = /(^|\/)(pnpm-lock\.yaml|uv\.lock)$|\.(png|jpe?g|webp|ico|woff2?|pdf)$/i;

export function scanText(text, file = "<text>") {
  const findings = [];
  text.split(/\r?\n/).forEach((line, index) => {
    if (line.includes(ALLOW_MARKER)) return;
    for (const rule of RULES) {
      if (rule.pattern.test(line)) {
        findings.push({ file, line: index + 1, rule: rule.name });
      }
    }
  });
  return findings;
}

export function scanRepository(root) {
  const files = execFileSync("git", ["ls-files", "-z"], { cwd: root, encoding: "utf8" })
    .split("\0")
    .filter(Boolean);
  const findings = [];
  for (const file of files) {
    if (SKIPPED_FILES.test(file)) continue;
    let text;
    try {
      text = readFileSync(path.join(root, file), "utf8");
    } catch {
      continue;
    }
    if (text.includes("\0")) continue;
    findings.push(...scanText(text, file));
  }
  return findings;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const findings = scanRepository(root);
  for (const item of findings) {
    // The matched text is deliberately not printed, so a real secret is not copied to logs.
    console.error(`${item.file}:${item.line}: possible ${item.rule}`);
  }
  if (findings.length > 0) {
    console.error(`${findings.length} possible secret(s) found.`);
    process.exit(1);
  }
  console.log("No secrets found in tracked files.");
}
