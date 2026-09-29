import js from "@eslint/js";
import prettier from "eslint-config-prettier/flat";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";
import tailwind from "./eslint/tailwind.mjs";

const NO_AI = "AI SDKs and frameworks are forbidden in the web (ADR 0015).";

export default defineConfig([
  globalIgnores(["dist/**", "src-tauri/**", "src/routeTree.gen.ts", "src/api/schema.gen.ts"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.strict,
      tseslint.configs.stylistic,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: { globals: globals.browser },
    plugins: { "hestia-tailwind": tailwind },
    rules: {
      // Clean code (docs/conventions.md, «Web»).
      eqeqeq: ["error", "always"],
      "no-console": "error",
      "object-shorthand": "error",
      "prefer-template": "error",
      "@typescript-eslint/consistent-type-imports": ["error", { fixStyle: "inline-type-imports" }],
      "@typescript-eslint/consistent-type-definitions": ["error", "type"],
      "@typescript-eslint/no-non-null-assertion": "error",
      // Tailwind: the scale and the theme tokens, never arbitrary values (app/AGENTS.md).
      "hestia-tailwind/no-arbitrary-value": "error",

      // Hestia is deterministic and works without AI (ADR 0015). Keep in sync with
      // scripts/check-no-ai.mjs, which checks package.json and pnpm-lock.yaml.
      "no-restricted-imports": [
        "error",
        {
          paths: ["openai", "ai", "langchain"].map((name) => ({ name, message: NO_AI })),
          patterns: [
            {
              group: [
                "openai/*",
                "ai/*",
                "langchain/*",
                "@ai-sdk/*",
                "@anthropic-ai/*",
                "@langchain/*",
              ],
              message: NO_AI,
            },
          ],
        },
      ],
    },
  },
  {
    // TanStack Router file routes export `Route`; the router plugin's code splitting keeps HMR working.
    files: ["src/routes/**"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  {
    // shadcn primitives export helpers (variants) next to components, and are vendored as
    // shadcn ships them (upstream arbitrary values included).
    files: ["src/components/ui/**"],
    rules: {
      "react-refresh/only-export-components": "off",
      "hestia-tailwind/no-arbitrary-value": "off",
    },
  },
  prettier,
]);
