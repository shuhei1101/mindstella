import { describe, expect, test, vi } from "vitest";

import { linkBody, linkHeadings, markExternalLinks, renderMarkdown, resolveFileSources } from "@/shared/core/body-links";
import { buildIndex, type MindmapData } from "@/shared/core/records";

// mdmark の代わりに、決まった HTML を描く（mdmark と同じ属性のフェンスのコードブロック 2 つ（1 つはバーを持つ）・属性の無い字下げのコードブロック・mermaid のコードブロック・範囲の中の pre）
const CODE_BLOCK_HTML = [
  '<div class="mdmark-code"><div class="mdmark-code-bar"><span class="mdmark-code-lang">json</span><button type="button" class="mdmark-code-copy">コピー</button></div><pre tabindex="0" aria-label="コード: json" data-source-line="0"><code class="language-json">{"type": "http"}</code></pre></div>',
  '<pre tabindex="0" aria-label="コード" data-source-line="4"><code>plugins/mindstella/</code></pre>',
  '<pre data-source-line="8"><code>字下げのコード</code></pre>',
  '<pre tabindex="0" aria-label="コード: mermaid" data-source-line="10"><code class="language-mermaid">flowchart LR</code></pre>',
  '<div class="mdmark-html"><pre><code>範囲の中のコード</code></pre></div>',
  '<div class="mdmark-map"><pre><code class="language-mermaid">flowchart TB</code></pre></div>',
].join("");
// mdmark の `mount` が投げる例外（null なら投げずに描く）
const mount = vi.hoisted(() => ({ error: null as Error | null, options: [] as Record<string, unknown>[] }));
vi.mock("@/shared/adapters/libraries", () => ({
  libraryState: () => "ready",
  mdmarkMapConfig: () => undefined,
  getLibrary: () => ({
    mount: (root: HTMLElement, options: Record<string, unknown>) => {
      mount.options.push(options);
      if (mount.error !== null) throw mount.error;
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
    const data = { decisions: [{ id: "D-1", title: "題", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] } } as unknown as MindmapData;
    const root = document.createElement("div");
    root.innerHTML = "<p>D-1 を見る</p>";
    const onOpen = vi.fn();
    // 実行
    linkBody({ root, index: buildIndex(data), selfId: "D-9", onOpen, source: "D-1 を見る" });
    root.querySelector<HTMLElement>("[data-id='D-1']")?.click();
    // 検証
    expect(onOpen).toHaveBeenCalledWith("D-1");
  });

  // スレッドの ID と書き込みの ID をリンクにする（正常系）
  test("link_body_when_thread_ids", () => {
    // 準備
    const data = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] } } as unknown as MindmapData;
    const root = document.createElement("div");
    const source = "TH-1 と TH-1-2 と TH-99 を見る";
    root.innerHTML = `<p>${source}</p>`;
    const onOpenThread = vi.fn();
    const threads = (id: string) => (id === "TH-1" ? { title: "見直し", posts: ["TH-1-1", "TH-1-2"] } : null);
    // 実行
    linkBody({ root, index: buildIndex(data), selfId: "D-9", onOpen: vi.fn(), source, threads, onOpenThread });
    // 検証
    expect(root.querySelector("[data-thread='TH-99']")).toBeNull();
    expect(root.textContent).toBe(source);
    root.querySelector<HTMLElement>("[data-thread='TH-1']:not([data-post])")?.click();
    root.querySelector<HTMLElement>("[data-post='TH-1-2']")?.click();
    expect(onOpenThread.mock.calls).toEqual([
      ["TH-1", null],
      ["TH-1", "TH-1-2"],
    ]);
  });

  // 差分を描いた本文にもリンクを付け、削除した行の中は付けない（正常系）
  test("link_body_when_diff", () => {
    // 準備
    const data = {
      decisions: [
        { id: "D-1", title: "題", status: "未決定" },
        { id: "D-2", title: "消した題", status: "未決定" },
      ],
      tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] },
    } as unknown as MindmapData;
    const root = document.createElement("div");
    root.innerHTML = '<div class="mdmark-diff-block" data-kind="add"><p>D-1 を足した</p></div><div class="mdmark-diff-block" data-kind="del"><p>D-2 を消した</p></div>';
    // 実行
    linkBody({ root, index: buildIndex(data), selfId: "D-9", onOpen: vi.fn(), source: "D-1 を足した" });
    // 検証
    expect(root.querySelector("[data-id='D-1']")).not.toBeNull();
    expect(root.querySelector("[data-id='D-2']")).toBeNull();
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
    const outside = [...root.querySelectorAll("pre")].filter((pre) => pre.closest(".mdmark-html, .mdmark-map") === null && !pre.classList.contains("dg-raw"));
    expect(outside.map(attributes)).toEqual([
      { tabindex: "0", role: null, label: "コード: json" },
      { tabindex: "0", role: null, label: "コード" },
      { tabindex: "0", role: null, label: "コード" },
    ]);
    expect([...root.querySelectorAll("pre.dg-raw")].map((pre) => pre.getAttribute("tabindex"))).toEqual([null]);
    expect([...root.querySelectorAll(".mdmark-html pre")].map((pre) => pre.getAttribute("tabindex"))).toEqual([null]);
    expect(root.querySelectorAll(".mdmark-map .diagram").length).toBe(0);
    expect(root.querySelectorAll(".mdmark-map code.language-mermaid").length).toBe(1);
  });

  // mount が例外を投げても投げ返さず、mdmark の知らせと原文を返す（異常系）
  test("render_markdown_when_mount_failed", () => {
    // 準備
    mount.error = new TypeError("Failed to construct 'URL': Invalid URL");
    // 実行
    let root: HTMLElement;
    try {
      root = renderMarkdown("# 見出し\n\n<!-- map -->");
    } finally {
      mount.error = null;
    }
    // 検証
    expect(root.textContent).toContain("mdmark");
    expect(root.querySelector("pre.md-raw")?.textContent).toBe("# 見出し\n\n<!-- map -->");
  });

  // 比較元の Markdown を渡す（正常系）
  test("render_markdown_when_base", () => {
    // 準備
    mount.options.length = 0;
    // 実行
    renderMarkdown("今の段落", { base: "前の段落" });
    // 検証
    const options = mount.options.at(-1) as { baseMarkdown?: string; config: { features: Record<string, boolean> } };
    expect(options.baseMarkdown).toBe("前の段落");
    expect(options.config.features["print"]).toBe(true);
  });

  // 画面と重なる mdmark の機能だけをオフにする（正常系）
  test("render_markdown_features", () => {
    // 準備
    mount.options.length = 0;
    // 実行
    renderMarkdown("本文");
    // 検証
    const { features } = (mount.options.at(-1) as { config: { features: Record<string, boolean> } }).config;
    expect(features).not.toHaveProperty("syntax");
    expect(features).not.toHaveProperty("code");
    const off = Object.entries(features).filter(([, on]) => !on).map(([name]) => name).sort();
    expect(off).toEqual(["anchors", "back-to-top", "backlinks", "comments", "diagram-resize", "glossary", "lightbox", "mermaid", "sections", "side-toc", "toc", "views"].sort());
  });

  // 取り出し元を渡す（正常系）
  test("render_markdown_when_diff_source", async () => {
    // 準備
    mount.options.length = 0;
    // 実行
    renderMarkdown("今の段落", { diffSource: { docId: "D-1", before: "前の段落", after: "今の段落" } });
    // 検証
    type Revision = { id: string };
    const options = mount.options.at(-1) as {
      docId?: string;
      diffMode?: string;
      diffControls?: boolean;
      diffSource: { revisions: (docId: string) => Promise<Revision[]>; content: (input: { docId: string; revisionId: string }) => Promise<string> };
    };
    expect(options.docId).toBe("D-1");
    expect(options.diffMode).toBe("open");
    expect(options.diffControls).toBe(false);
    const revisions = await options.diffSource.revisions("D-1");
    expect(revisions).toHaveLength(2);
    const contents = await Promise.all(revisions.map(({ id }) => options.diffSource.content({ docId: "D-1", revisionId: id })));
    expect([...contents].sort()).toEqual(["今の段落", "前の段落"].sort());
  });
});

describe("markExternalLinks", () => {
  // 別のオリジンのリンクだけを新規タブで開く（正常系）
  test("mark_external_links", () => {
    // 準備
    const root = document.createElement("div");
    root.innerHTML = [
      '<a href="https://example.com/a">別のオリジン</a>',
      `<a href="${location.origin}/w/x/">同じオリジン</a>`,
      '<a href="#id=D-1">D-1</a>',
      '<a href="#見出し">見出し</a>',
    ].join("");
    // 実行
    markExternalLinks(root);
    // 検証
    const marked = [...root.querySelectorAll("a")].map((a) => ({ text: a.textContent, target: a.getAttribute("target"), rel: a.getAttribute("rel") }));
    expect(marked).toEqual([
      { text: "別のオリジン", target: "_blank", rel: "noopener noreferrer" },
      { text: "同じオリジン", target: null, rel: null },
      { text: "D-1", target: null, rel: null },
      { text: "見出し", target: null, rel: null },
    ]);
  });
});

describe("resolveFileSources", () => {
  // 相対パスだけを配信のパスにする（正常系）
  test("resolve_file_sources", () => {
    // 準備
    window.history.pushState({}, "", "/w/mindstella-x-1/");
    const root = document.createElement("div");
    root.innerHTML = [
      '<p><img id="a" src="../files/a.png"></p>',
      '<figure><video id="b" src="../files/b.mp4#t=2" poster="../files/p.png"></video></figure>',
      '<figure><audio id="c" src="../files/c.mp3"></audio></figure>',
      '<p><img id="u" src="https://example.com/u.png"></p>',
      '<p><img id="d" src="data:image/png;base64,AA"></p>',
      '<p><img id="r" src="/r.png"></p>',
      '<div class="mdmark-html"><img id="h" src="../files/h.png"></div>',
    ].join("");
    const attr = (id: string, name: string) => root.querySelector(`#${id}`)?.getAttribute(name);
    // 実行
    resolveFileSources(root);
    // 検証
    expect({
      a: attr("a", "src"),
      b: attr("b", "src"),
      poster: attr("b", "poster"),
      c: attr("c", "src"),
      u: attr("u", "src"),
      d: attr("d", "src"),
      r: attr("r", "src"),
      h: attr("h", "src"),
    }).toEqual({
      a: "/w/mindstella-x-1/files/a.png",
      b: "/w/mindstella-x-1/files/b.mp4#t=2",
      poster: "/w/mindstella-x-1/files/p.png",
      c: "/w/mindstella-x-1/files/c.mp3",
      u: "https://example.com/u.png",
      d: "data:image/png;base64,AA",
      r: "/r.png",
      h: "../files/h.png",
    });
  });
});
