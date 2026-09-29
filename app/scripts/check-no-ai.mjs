// Hestia is deterministic and works without AI (ADR 0015): the web must not declare or lock
// any AI SDK or framework. Imports are blocked by `no-restricted-imports` in eslint.config.mjs;
// this script checks package.json (every dependency field) and pnpm-lock.yaml, including
// transitive packages. Run with `pnpm lint`.
import { readFileSync } from "node:fs";

// Exact package names, or a scope/prefix ending in "*" for a whole family.
const FORBIDDEN = ["@anthropic-ai/*", "openai", "ai", "@ai-sdk/*", "langchain", "@langchain/*"];

const isForbidden = (name) =>
  FORBIDDEN.some((rule) =>
    rule.endsWith("*") ? name.startsWith(rule.slice(0, -1)) : name === rule,
  );

const root = new URL("../", import.meta.url);
const pkg = JSON.parse(readFileSync(new URL("package.json", root), "utf8"));
const fields = ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"];
const declared = fields.flatMap((field) =>
  Object.keys(pkg[field] ?? {}).map((name) => `package.json ${field}: ${name}`),
);

// pnpm-lock.yaml v9: `packages:` entries look like `  name@version:` or `  '@scope/name@version':`.
const lock = readFileSync(new URL("pnpm-lock.yaml", root), "utf8");
const section = lock.split(/^packages:$/m)[1]?.split(/^\S/m)[0] ?? "";
const locked = [...section.matchAll(/^ {2}'?((?:@[^/\s']+\/)?[^@\s']+)@/gm)].map((m) => m[1]);
if (locked.length === 0) throw new Error("check-no-ai: no packages found in pnpm-lock.yaml");

const offenders = [
  ...declared.filter((line) => isForbidden(line.split(": ")[1])),
  ...[...new Set(locked)].filter(isForbidden).map((name) => `pnpm-lock.yaml: ${name}`),
];
if (offenders.length > 0) {
  console.error("AI dependencies are forbidden in the web (ADR 0015):");
  for (const offender of offenders) console.error(`  ${offender}`);
  process.exit(1);
}
console.log(`check-no-ai: ok (${declared.length} declared, ${new Set(locked).size} locked)`);
