import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import stylistic from "@stylistic/eslint-plugin";
import vue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import globals from "globals";

export default [
  {
    ignores: ["hoard/dist/**", "node_modules/**", "vendor/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs["flat/strongly-recommended"],
  prettier,
  {
    plugins: {
      "@stylistic": stylistic,
    },
    rules: {
      curly: ["error", "all"],
      "@stylistic/padding-line-between-statements": [
        "error",
        { blankLine: "always", prev: ["function", "class"], next: "*" },
        { blankLine: "always", prev: "*", next: ["function", "class"] },
      ],
      "@stylistic/lines-between-class-members": [
        "error",
        "always",
        { exceptAfterSingleLine: true },
      ],
    },
  },
  {
    files: ["hoard/**/*.{ts,vue}"],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    files: ["hoard/**/*.vue"],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
    rules: {
      // PrimeVue exports direct component names such as Button and Dialog.
      // They are locally imported and intentionally not HTML elements.
      "vue/no-reserved-component-names": "off",
      "vue/html-closing-bracket-newline": [
        "error",
        {
          singleline: "never",
          multiline: "always",
          selfClosingTag: {
            singleline: "never",
            multiline: "always",
          },
        },
      ],
      "vue/multiline-html-element-content-newline": "error",
      "vue/require-default-prop": "off",
      "vue/block-tag-newline": [
        "error",
        {
          singleline: "always",
          multiline: "always",
          maxEmptyLines: 0,
        },
      ],
    },
  },
];
