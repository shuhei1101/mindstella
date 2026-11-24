import { describe, expect, test } from "vitest";

import { bodyToc } from "@/shared/core/body-toc";

describe("bodyToc", () => {
  // 階層と文字を取り出す（正常系）
  test("body_toc", () => {
    // 準備
    const markdown = ["# 目的", "本文", "## [保存先](x) の **決め方**", "### 末尾 ##"].join("\n");
    // 実行
    const entries = bodyToc(markdown);
    // 検証
    expect(entries.map(({ level, text }) => ({ level, text }))).toEqual([
      { level: 1, text: "目的" },
      { level: 2, text: "保存先 の 決め方" },
      { level: 3, text: "末尾" },
    ]);
  });

  // コードブロックの中は見出しにしない（正常系）
  test("body_toc_when_fenced", () => {
    // 準備
    const markdown = ["```", "# 後で消す", "```", "~~~", "# 後で消す", "~~~", "## 見出し"].join("\n");
    // 実行
    const entries = bodyToc(markdown);
    // 検証
    expect(entries.map(({ text }) => text)).toEqual(["見出し"]);
  });

  // 同じ文言に番号を付ける（正常系）
  test("body_toc_when_same_text", () => {
    // 準備
    const markdown = ["## 決め方", "## 決め方"].join("\n");
    // 実行
    const entries = bodyToc(markdown);
    // 検証
    expect(entries.map(({ slug }) => slug)).toEqual(["決め方", "決め方-1"]);
  });
});
