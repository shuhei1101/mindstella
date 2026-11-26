import { Linter } from "eslint";
import tseslint from "typescript-eslint";
import { describe, expect, test } from "vitest";

import config from "../../../../eslint.config.js";

/** eslint.config.js の no-restricted-syntax の設定（frontend/src の .tsx にヒットする最後の指定） */
const restrictedSyntax = (): Linter.RuleEntry => {
  const entries = config.flatMap((item) => (item.rules?.["no-restricted-syntax"] === undefined ? [] : [item.rules["no-restricted-syntax"]]));
  const entry = entries.at(-1);
  if (entry === undefined) throw new Error("no-restricted-syntax の設定がありません");
  return entry;
};

/** JSX の断片を no-restricted-syntax だけで検査し、誤りの数を返却する */
const errorsOf = (source: string): number => {
  const linter = new Linter({ configType: "flat" });
  const messages = linter.verify(
    source,
    [{ files: ["**/*.tsx"], languageOptions: { parser: tseslint.parser, parserOptions: { ecmaFeatures: { jsx: true } } }, rules: { "no-restricted-syntax": restrictedSyntax() } }],
    "sample.tsx",
  );
  return messages.filter((message) => message.ruleId === "no-restricted-syntax").length;
};

describe("eslint.config.js の記録の文字の検出", () => {
  // 記録の文字を JSX の子に直接描く記載を誤りにする（正常系）
  test.each(["<p>{x.title}</p>", "<p>{x?.title}</p>", "<p>{title}</p>", "<p>{summary}</p>", "<p>{titleOf(index, id)}</p>", "<>{x.summary}</>"])("record_text_lint_error", (jsx) => {
    // 実行・検証
    expect(errorsOf(`const a = ${jsx};`)).toBe(1);
  });

  // 部品『記録の文字』で描く記載は合格にする（正常系）
  test("record_text_lint_ok", () => {
    // 実行・検証
    expect(errorsOf('const a = <p><RecordText text={x.title} mode="link" lookup={lookup} /></p>;')).toBe(0);
  });
});
