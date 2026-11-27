import { describe, expect, test, vi } from "vitest";

import { buildDocHtml, stripEmbeddedHtml } from "@/shared/core/doc-export";
import { buildIndex, type Item, type MindmapData } from "@/shared/core/records";

describe("buildDocHtml", () => {
  // 本文と中身を持つ（正常系）
  test("build_doc_html", () => {
    // 実行
    const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] } } as unknown as MindmapData;
    const html = buildDocHtml({ item: { id: "A-1", title: "題" } as Item, source: "本文の文", index: buildIndex(empty), assets: { css: ".a{}", js: "var a;" } });
    // 検証
    expect(html).toContain("本文の文");
    expect(html).toContain(".a{}");
    expect(html).toContain("var a;");
  });

  // 書き出した HTML は外部のリンクを新規タブで開く（正常系）
  test("build_doc_html_external_links", async () => {
    // 準備
    const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] } } as unknown as MindmapData;
    const html = buildDocHtml({ item: { id: "A-1", title: "題" } as Item, source: "本文", index: buildIndex(empty), assets: { css: "", js: "" } });
    const parsed = new DOMParser().parseFromString(html, "text/html");
    document.body.replaceChildren(...[...parsed.body.children].filter((element) => !element.matches("script:not([type])")).map((element) => document.importNode(element, true)));
    // jsdom は Blob の URL の import() を持たないため、起動のスクリプトの読み込みを、外部と項目の ID のリンクを描く mount の代わりに置き換えて流す
    const boot = [...parsed.querySelectorAll("script:not([type])")].map((script) => script.textContent).join("\n");
    const stub = '({ mount: (root) => { root.innerHTML = \'<a href="https://example.com/">外部</a><a href="#id=D-1">D-1</a>\'; } })';
    const created = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:doc-mdmark");
    const revoked = vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
    // 実行
    await ((0, eval)(boot.replace("await import(url)", stub)) as Promise<void>);
    // 検証
    const external = document.querySelector('a[href="https://example.com/"]');
    const internal = document.querySelector('a[href="#id=D-1"]');
    expect(external?.getAttribute("target")).toBe("_blank");
    expect(external?.getAttribute("rel")).toBe("noopener noreferrer");
    expect(internal?.hasAttribute("target")).toBe(false);
    created.mockRestore();
    revoked.mockRestore();
    document.body.replaceChildren();
  });
});

describe("stripEmbeddedHtml", () => {
  // 範囲を除く（正常系）
  test("strip_embedded_html", () => {
    expect(stripEmbeddedHtml("前\n<!-- html -->\n<div>中</div>\n<!-- /html -->\n後\n")).not.toContain("<div>中</div>");
  });
});
