import { describe, expect, test } from "vitest";

import { buildDocHtml, stripEmbeddedHtml } from "@/shared/core/doc-export";
import { buildIndex, type Item, type MindmapData } from "@/shared/core/records";

describe("buildDocHtml", () => {
  // 本文と中身を持つ（正常系）
  test("build_doc_html", () => {
    // 実行
    const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] } } as unknown as MindmapData;
    const html = buildDocHtml({ item: { id: "A-1", title: "題" } as Item, source: "本文の文", index: buildIndex(empty), assets: { css: ".a{}", js: "var a;" } });
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
