import js from "@eslint/js";
import prettier from "eslint-config-prettier/flat";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

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
