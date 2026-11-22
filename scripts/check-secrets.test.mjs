import assert from "node:assert/strict";
import test from "node:test";

import { scanText } from "./check-secrets.mjs";

// Fixtures are assembled at run time so this file does not itself contain the shapes.
const fake = {
  aws: "AKIA" + "ABCDEFGHIJKLMNOP",
  github: "ghp_" + "a".repeat(36),
  pem: "-----BEGIN " + "RSA PRIVATE KEY-----",
  assignment: `const apiKey = "${"x9".repeat(10)}";`,
};

test("known token shapes are found and reported by line", () => {
  for (const [name, text] of Object.entries(fake)) {
    const found = scanText(`line one\n${text}\n`, "f.txt");
    assert.equal(found.length, 1, name);
    assert.deepEqual([found[0].file, found[0].line], ["f.txt", 2]);
  }
});

test("ordinary configuration and placeholders are not flagged", () => {
  const harmless = [
    'PASSWORD = "correct horse battery"',
    "POSTGRES_PASSWORD: ci_only_password",
    'const secret = process.env.SMART_ENGINEER_SECRET;',
    'password: "${PASSWORD}"',
    "// never put an api_key in the frontend",
    'const token = "";',
  ];
  for (const line of harmless) {
    assert.deepEqual(scanText(line), [], line);
  }
});

test("the allow marker skips a deliberate fixture line", () => {
  assert.deepEqual(scanText(`${fake.aws} // secret-scan:allow`), []);
});

test("the matched text is never part of a finding", () => {
  const [finding] = scanText(fake.github, "f.txt");
  assert.ok(!JSON.stringify(finding).includes(fake.github));
});
