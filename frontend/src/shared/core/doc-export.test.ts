import { describe, expect, test } from "vitest";

import { buildDocHtml, stripEmbeddedHtml } from "@/shared/core/doc-export";

describe("buildDocHtml", () => {
  // 本文と中身を持つ（正常系）
  test("build_doc_html", () => {
    // 実行
    const html = buildDocHtml({ title: "題", source: "本文の文", assets: { css: ".a{}", js: "var a;" } });
    // 検証
    expect(html).toContain("本文の文");
    expect(html).toContain(".a{}");
    expect(html).toContain("var a;");
  });
});

describe("stripEmbeddedHtml", () => {
  // 範囲を除く（正常系）
  test("strip_embedded_html", () => {
    expect(stripEmbeddedHtml("前\n<!-- html -->\n<div>中</div>\n<!-- /html -->\n後\n")).not.toContain("<div>中</div>");
  });
});
