import js from "@eslint/js";
import prettier from "eslint-config-prettier/flat";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

const NO_AI = "AI SDKs and frameworks are forbidden in the web (ADR 0015).";

export default defineConfig([
  globalIgnores(["dist/**", "src-tauri/**", "src/routeTree.gen.ts", "src/api/schema.gen.ts"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: { globals: globals.browser },
    rules: {
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
    // shadcn primitives export helpers (variants) next to components.
    files: ["src/components/ui/**"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  prettier,
]);
