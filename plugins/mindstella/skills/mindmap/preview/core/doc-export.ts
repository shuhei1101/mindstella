// 資料のエクスポート。mdmark の CSS と JavaScript・用語の索引・本文を 1 枚の HTML にまとめる組み立てと、埋め込んだ HTML を除いた Markdown の組み立てと、ブラウザへのダウンロード。

namespace MindmapPreview {
  /** エクスポートした 1 枚の HTML の `mdmark.mount` に渡す機能のオフ。用語と資料・調査のエイリアスのツールチップ（`glossary`・`backlinks`）は mdmark が描き、通信するコードの色付けと、ファイルの外を指す機能を止める */
  export const MDMARK_EXPORT_FEATURES: Record<string, boolean> = {
    comments: false,
    print: false,
    views: false,
    syntax: false,
  };

  /** 配る書き出しが mdmark の CSS を中身に持つ `<style>` の id */
  export const MDMARK_CSS_EMBEDDED_ID = "mindmap-mdmark-css";

  /** 1 枚の HTML に入れる mdmark の CSS と JavaScript の中身 */
  export type MdmarkAssets = { css: string; js: string };

  /** `mdmarkAssets` の結果。取れたら CSS と JavaScript の中身、取れなければ理由 */
  export type MdmarkAssetsResult = ({ ok: true } & MdmarkAssets) | { ok: false; reason: string };

  /** URL を `integrity` で確かめて読み、本文を返す。`integrity` が合わないか、200 台でないときは投げる */
  async function fetchChecked({ url, integrity }: { url: string; integrity: string }): Promise<string> {
    const response = await fetch(url, { integrity, mode: "cors", credentials: "omit" });
    if (!response.ok) throw new Error(`${url} が ${response.status} を返しました`);
    return response.text();
  }

  /** 1 枚の HTML に入れる mdmark の CSS と JavaScript の中身を取る。配る書き出しは中身を持つ要素の文字を返し、サーバーの配信は CSS の `link` と import map の URL を `integrity` で確かめて読む。取れないときは拒否せず理由を返す */
  export async function mdmarkAssets(): Promise<MdmarkAssetsResult> {
    const embeddedJs = document.getElementById(MDMARK_EMBEDDED_ID);
    const embeddedCss = document.getElementById(MDMARK_CSS_EMBEDDED_ID);
    // 配る書き出し: 中身を持つ要素の文字
    if (embeddedJs !== null && embeddedCss !== null) {
      return { ok: true, css: embeddedCss.textContent ?? "", js: embeddedJs.textContent ?? "" };
    }
    // サーバーの配信: import map の JavaScript の URL と、同じ場所の CSS の `link`
    const entry = mdmarkImportMapEntry();
    if (entry === null) return { ok: false, reason: "mdmark の JavaScript の URL を import map から読めませんでした" };
    const cssUrl = entry.url.replace(/index\.js$/, "index.css");
    const link = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')].find((element) => element.getAttribute("href") === cssUrl);
    if (link === undefined) return { ok: false, reason: "mdmark の CSS の link を読めませんでした" };
    try {
      const [css, js] = await Promise.all([fetchChecked({ url: cssUrl, integrity: link.integrity }), fetchChecked(entry)]);
      return { ok: true, css, js };
    } catch (error) {
      return { ok: false, reason: `mdmark の CSS と JavaScript を読み込めませんでした（${error instanceof Error ? error.message : String(error)}）` };
    }
  }

  /** `script` 要素を閉じるタグ。このファイル自身が雛形の `script` 要素の中に入るため、閉じるタグをそのまま書かず、つないで作る */
  const SCRIPT_CLOSE = `<${"/"}script>`;

  /** HTML の文字として出す文字列にする（`&`・`<`・`>`・`"` を文字参照にする） */
  function escapeHtml(text: string): string {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /** エクスポートした HTML が起動のときに流す JavaScript。mdmark の中身から Blob の URL を作って `import()` し、本文を描き、今の値をコピーするボタンの文言を替える（`relabelParamCopy` と同じ置き換え） */
  const DOC_BOOT_SCRIPT = [
    "(async () => {",
    '  const data = JSON.parse(document.getElementById("doc-data").textContent);',
    '  const url = URL.createObjectURL(new Blob([document.getElementById("doc-mdmark").textContent], { type: "text/javascript" }));',
    "  let library;",
    "  try {",
    "    library = await import(url);",
    "  } finally {",
    "    URL.revokeObjectURL(url);",
    "  }",
    '  const root = document.getElementById("doc");',
    "  library.mount(root, { markdown: data.source, config: { features: data.features }, index: data.index });",
    "  const relabel = (button) => {",
    "    const texts = [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);",
    "    if (texts.length === 1 && texts[0].textContent === data.copyLabel) return;",
    "    texts.forEach((node) => node.remove());",
    "    button.append(document.createTextNode(data.copyLabel));",
    "  };",
    '  root.querySelectorAll(".mdmark-param-copy").forEach(relabel);',
    "  new MutationObserver((records) => {",
    "    for (const record of records) {",
    "      for (const added of record.addedNodes) {",
    "        if (added.nodeType !== Node.ELEMENT_NODE) continue;",
    '        if (added.matches(".mdmark-param-copy")) relabel(added);',
    '        added.querySelectorAll(".mdmark-param-copy").forEach(relabel);',
    "      }",
    "    }",
    "  }).observe(root, { childList: true, subtree: true });",
    "})();",
  ].join("\n");

  /** エクスポートした HTML の、本文を置く枠の幅と余白 */
  const DOC_PAGE_STYLE = "body{margin:0}.doc-page{max-width:60rem;margin:0 auto;padding:24px 16px}.doc-title{margin:0 0 16px}";

  /** 資料 1 件の本文を、mdmark の CSS と JavaScript を中に持ち、ネットにつながらなくても開ける 1 枚の HTML にする。`item` 自身と取り下げた資料・調査は、ツールチップの索引に入れない。JavaScript が `script` 要素を閉じるタグを含むときは組み立てずに投げる */
  export function buildDocHtml({
    item,
    source,
    index,
    assets,
  }: {
    item: Item;
    source: string;
    index: RecordIndex;
    assets: MdmarkAssets;
  }): string {
    if (/<\/script/i.test(assets.js)) throw new Error("mdmark の JavaScript が script 要素を閉じるタグを含むため、1 枚の HTML に入れられません");
    if (/<\/style/i.test(assets.css)) throw new Error("mdmark の CSS が </style を含むため、1 枚の HTML に入れられません");
    // mdmark に渡す索引。用語集の用語と、item 自身と取り下げたものを除いた資料・調査
    const documents = [...index.data.docs, ...index.data.research]
      .filter((entry) => entry.id !== item.id && entry.withdrawn !== true)
      .map((entry) => ({
        id: entry.id,
        path: `${entry.id}.md`,
        title: entry.title,
        ...(entry.aliases === undefined ? {} : { aliases: entry.aliases }),
        ...(entry.description === undefined ? {} : { description: entry.description }),
      }));
    const terms = index.data.terms.map((term) => ({
      id: term.id,
      term: term.title,
      meaning: term.meaning ?? "",
      ...(term.aliases === undefined ? {} : { aliases: term.aliases }),
    }));
    // 本文・索引・文言を 1 つの JSON にする。`<` は HTML を壊さないよう、エスケープした形で入れる
    const data = JSON.stringify({
      source,
      index: { docs: documents, terms },
      features: MDMARK_EXPORT_FEATURES,
      copyLabel: MDMARK_PARAM_COPY_LABEL,
    }).replace(/</g, "\\u003c");
    const title = escapeHtml(item.title);
    return [
      "<!doctype html>",
      '<html lang="ja">',
      "<head>",
      '<meta charset="utf-8">',
      '<meta name="viewport" content="width=device-width, initial-scale=1">',
      `<title>${title}</title>`,
      `<style>${assets.css}</style>`,
      `<style>${DOC_PAGE_STYLE}</style>`,
      "</head>",
      "<body>",
      '<main class="doc-page">',
      `<h1 class="doc-title">${title}</h1>`,
      '<div id="doc"></div>',
      "</main>",
      `<script type="application/json" id="doc-data">${data}${SCRIPT_CLOSE}`,
      `<script type="text/plain" id="doc-mdmark">${assets.js}${SCRIPT_CLOSE}`,
      `<script>${DOC_BOOT_SCRIPT}${SCRIPT_CLOSE}`,
      "</body>",
      "</html>",
      "",
    ].join("\n");
  }

  /** 本文から `<!-- html -->` 〜 `<!-- /html -->` の範囲を印の行ごと除き、空行が 3 つ以上続くところを 2 つにまとめた Markdown を返す */
  export function stripEmbeddedHtml(source: string): string {
    const removed = new Set<number>();
    for (const { open, close } of embeddedHtmlRanges(source)) {
      for (let line = open; line <= close; line += 1) removed.add(line);
    }
    return source
      .split("\n")
      .filter((_line, position) => !removed.has(position + 1))
      .join("\n")
      .replace(/\n{4,}/g, "\n\n\n");
  }

  /** 文字をファイルとして端末に保存させる。`Blob` の URL を `download` を持つ `a` で開き、URL を解放する */
  export function downloadText({ name, text, type }: { name: string; text: string; type: "text/html" | "text/markdown" }): void {
    const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
    const anchor = h({ tag: "a", attrs: { href: url, download: name } });
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }
}
