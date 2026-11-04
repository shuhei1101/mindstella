// React の側（frontend/src）だけに当てる ESLint の設定
import js from "@eslint/js";
import betterTailwindcss from "eslint-plugin-better-tailwindcss";
import boundaries from "eslint-plugin-boundaries";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["frontend/src/shared/api/generated/**", "frontend/src/route-tree.gen.ts", "plugins/**", "tests/**", "dev/**", "node_modules/**", "storybook-static/**", "storybook-react-static/**", ".storybook/**"] },
  {
    files: ["frontend/src/**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: {
      "better-tailwindcss": betterTailwindcss,
      boundaries,
      "jsx-a11y": jsxA11y,
      "react-hooks": reactHooks,
      sonarjs,
    },
    settings: {
      "better-tailwindcss": { entryPoint: "frontend/src/shared/styles/index.css" },
      "import/resolver": { typescript: { project: "frontend/tsconfig.json" } },
      "boundaries/elements": [
        { type: "app", pattern: "frontend/src/app/**" },
        { type: "routes", pattern: "frontend/src/routes/**" },
        { type: "features", pattern: "frontend/src/features/**" },
        { type: "shared", pattern: "frontend/src/shared/**" },
      ],
    },
    rules: {
      ...reactHooks.configs["recommended-latest"].rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      ...betterTailwindcss.configs.recommended.rules,
      "better-tailwindcss/no-unknown-classes": "error",
      "better-tailwindcss/no-restricted-classes": ["error", { restrict: [{ pattern: "\\[.*\\]", message: "任意値は使わない" }] }],
      "better-tailwindcss/enforce-consistent-line-wrapping": "off",
      "@typescript-eslint/no-deprecated": "error",
      "sonarjs/cognitive-complexity": ["error", 15],
      "boundaries/dependencies": [
        "error",
        {
          default: "disallow",
          policies: [
            { from: { element: { type: "app" } }, allow: { to: { element: { types: ["app", "routes", "features", "shared"] } } } },
            { from: { element: { type: "routes" } }, allow: { to: { element: { types: ["routes", "features", "shared"] } } } },
            { from: { element: { type: "features" } }, allow: { to: { element: { types: ["features", "shared"] } } } },
            { from: { element: { type: "shared" } }, allow: { to: { element: { types: ["shared"] } } } },
          ],
        },
      ],
    },
  },
);
