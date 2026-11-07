import { describe, expect, test, vi } from "vitest";

import { linkBody, linkHeadings, renderMarkdown } from "@/shared/core/body-links";
import { buildIndex, type MindmapData } from "@/shared/core/records";

// mdmark の代わりに、決まった HTML を描く（mdmark と同じ属性のフェンスのコードブロック 2 つ・属性の無い字下げのコードブロック・mermaid のコードブロック・範囲の中の pre）
const CODE_BLOCK_HTML = [
  '<pre tabindex="0" aria-label="コード: json" data-source-line="0"><code class="language-json">{"type": "http"}</code></pre>',
  '<pre tabindex="0" aria-label="コード" data-source-line="4"><code>plugins/mindstella/</code></pre>',
  '<pre data-source-line="8"><code>字下げのコード</code></pre>',
  '<pre tabindex="0" aria-label="コード: mermaid" data-source-line="10"><code class="language-mermaid">flowchart LR</code></pre>',
  '<div class="mdmark-html"><pre><code>範囲の中のコード</code></pre></div>',
].join("");
vi.mock("@/shared/adapters/libraries", () => ({
  libraryState: () => "ready",
  getLibrary: () => ({
    mount: (root: HTMLElement) => {
      root.innerHTML = CODE_BLOCK_HTML;
    },
  }),
}));

describe("linkHeadings", () => {
  // 同じ文言に番号（正常系）
  test("link_headings", () => {
    // 準備
    const root = document.createElement("div");
    root.innerHTML = "<h2>決め方</h2><h2>決め方</h2>";
    // 実行
    linkHeadings({ root, onHeading: vi.fn(), onChangeSet: vi.fn() });
    // 検証
    expect(root.querySelectorAll("h2")[1]?.dataset["heading"]).toBe("決め方-1");
  });
});

describe("linkBody", () => {
  // ID をリンクにする（正常系）
  test("link_body", () => {
    // 準備
    const data = { decisions: [{ id: "D-1", title: "題", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] } } as unknown as MindmapData;
    const root = document.createElement("div");
    root.innerHTML = "<p>D-1 を見る</p>";
    const onOpen = vi.fn();
    // 実行
    linkBody({ root, index: buildIndex(data), selfId: "D-9", onOpen, source: "D-1 を見る" });
    root.querySelector<HTMLElement>("[data-id='D-1']")?.click();
    // 検証
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });
});

describe("renderMarkdown", () => {
  // mdmark が付けた属性を残し、字下げのコードブロックの pre にだけ付ける（正常系）
  test("render_markdown_when_code_block", () => {
    // 準備
    const attributes = (pre: Element) => ({ tabindex: pre.getAttribute("tabindex"), role: pre.getAttribute("role"), label: pre.getAttribute("aria-label") });
    // 実行
    const root = renderMarkdown("```json\n{}\n```");
    // 検証
    const outside = [...root.querySelectorAll("pre")].filter((pre) => pre.closest(".mdmark-html") === null && !pre.classList.contains("dg-raw"));
    expect(outside.map(attributes)).toEqual([
      { tabindex: "0", role: null, label: "コード: json" },
      { tabindex: "0", role: null, label: "コード" },
      { tabindex: "0", role: null, label: "コード" },
    ]);
    expect([...root.querySelectorAll("pre.dg-raw")].map((pre) => pre.getAttribute("tabindex"))).toEqual([null]);
    expect([...root.querySelectorAll(".mdmark-html pre")].map((pre) => pre.getAttribute("tabindex"))).toEqual([null]);
  });
});
