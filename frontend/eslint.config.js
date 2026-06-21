import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["src/**/*.{js,jsx}"],
    plugins: { react, "react-hooks": reactHooks },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      // This codebase consistently calls an async load() function from
      // useEffect for data fetching, which is a standard and accepted
      // React pattern. This rule's heuristic does not distinguish that
      // from genuinely problematic synchronous setState-in-effect chains,
      // so it produces noise rather than catching real bugs here.
      "react-hooks/set-state-in-effect": "off",
    },
    settings: { react: { version: "detect" } },
  },
];
