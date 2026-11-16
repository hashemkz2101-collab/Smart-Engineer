import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Automated checks catch only a subset of accessibility problems. A passing run
// is not a full WCAG audit and does not replace manual screen-reader testing.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function summarize(violations) {
  return violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    targets: violation.nodes.map((node) => node.target.join(" ")),
  }));
}

for (const [name, path] of [
  ["home", "/"],
  ["not-found", "/no-such-page-p0-08"],
]) {
  for (const scheme of ["light", "dark"]) {
    test(`${name} page has no axe WCAG A/AA violations (${scheme})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(path);

      const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();

      expect(summarize(results.violations)).toEqual([]);
    });
  }
}
