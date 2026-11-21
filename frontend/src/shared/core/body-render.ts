/* eslint-disable @typescript-eslint/no-non-null-assertion -- 正規表現の捕捉と描いた直後の要素を指す */
// 本文の差分の描画。mdmark が描いた React の外の DOM に手を入れる
import { getLibrary } from "@/shared/adapters/libraries";
import { CODE_BLOCK_ATTRS, DIAGRAM_SOURCE_ATTR, EMBEDDED_HTML_CLASS, HTML_BLOCK_CLASS, LINE_ATTR, renderDiagramSvg, renderMarkdown } from "@/shared/core/body-links";
import { childMarks, COLORED_DIAGRAM_TYPES, diffDiagram, diffDiagramFromSource, diffInline, diffLineParts, LINE_DIFF_TIMEOUT_MS, pairedParts, pairEmbeddedHtml, type DiagramDiff, type InlineDiff, type JsDiff, type LinePart } from "@/shared/core/diff";
import { h, markupIcon } from "@/shared/core/dom-parts";
import { htmlBodyDiff } from "@/shared/core/html-body-diff";
import { htmlFrameElement } from "@/shared/core/html-frame";

const jsdiffOf = (): JsDiff => getLibrary("jsdiff") as JsDiff;
const linePartsOf = (before: string, after: string): LinePart[] | null => diffLineParts(before, after, jsdiffOf());
const diffInlineOf = (before: string, after: string, deadline: number): InlineDiff | null => diffInline(before, after, deadline, jsdiffOf());
const childMarksOf = (input: { before: string[]; after: string[] }) => childMarks({ ...input, jsdiff: jsdiffOf() });

/** 図の前の版の記法を、図の要素に持たせる属性の名前（図の拡大が Raw の差分に読む） */
export const BEFORE_SOURCE_ATTR = "data-before-source";

/** 前の版の図を描いて突き合わせる間、描いた SVG を置く画面の外の位置（px）と幅（px） */
const OFFSCREEN_LEFT_PX = -10000;
const OFFSCREEN_WIDTH_PX = 800;

/** 差分の記号と、読み上げに残す名前 */
const SIGNS = {
  add: { glyph: "+", name: "追加: " },
  del: { glyph: "−", name: "削除: " },
  same: { glyph: " ", name: "" },
} as const;


/** 読み上げにだけ残す文字 */
const srOnly = (text: string): HTMLElement => {
  return h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
};

/** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
export const signMarks = (op: keyof typeof SIGNS): Node[] => {
  const { glyph, name } = SIGNS[op];
  return [h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
};



/** 前後を組み立てられない旨・本文の差分を出せない旨の知らせ */
export const noteBox = (text: string): HTMLElement => {
  return h({
    tag: "p",
    attrs: { class: "df-note", role: "note" },
    children: [markupIcon("alert"), h({ tag: "span", children: [text] })],
  });
};


/** 消した行を別に描いた要素から、行の印を外す（今の本文の行に対応づけない） */
export const withoutLineMarks = (root: HTMLElement): HTMLElement => {
  for (const element of root.querySelectorAll(`[${LINE_ATTR}]`)) element.removeAttribute(LINE_ATTR);
  return root;
};

/** 語の面を付ける、消したブロックと足したブロックの対 */
export type WordPair = { removed: HTMLElement; added: HTMLElement };

/** 変わった語の面の要素 */
const wordMark = ({ mark, text }: { mark: "add" | "del"; text: string }): HTMLElement => {
  return h({ tag: "span", attrs: { class: `df-word df-${mark}` }, children: [text] });
};

/** 範囲の直下の要素を並びで比べるための文字列にする（描くたびに変わる部品の連番は揃える） */
const childSignature = (element: Element): string => {
  return element.outerHTML.replace(/mdmark-(diagram|param)-\d+-\d+/g, "mdmark-$1");
};

/** 差分の表示の間、変わった埋め込んだ HTML の範囲を、範囲の差分（変更前・変更後の描いた結果と原文の差分）に置き換える。範囲の直下の要素のうち、足した要素と変えた要素にマーカーを付けた今の範囲を、変更後の描いた結果にする */
export const replaceChangedRanges = ({ root, before, after }: { root: HTMLElement; before: string; after: string }): void => {
  const ranges = [...root.querySelectorAll<HTMLElement>(`.${EMBEDDED_HTML_CLASS}`)];
  for (const pair of pairEmbeddedHtml({ before, after })) {
    const element = ranges[pair.order];
    if (element === undefined) continue;
    // 選んだ時点の範囲を、範囲の印で包んで描く
    const beforeView = renderMarkdown(`<!-- html -->\n${pair.before}\n<!-- /html -->\n`);
    const beforeRange = beforeView.querySelector(`.${EMBEDDED_HTML_CLASS}`);
    if (beforeRange === null) continue;
    const marks = childMarksOf({ before: [...beforeRange.children].map(childSignature), after: [...element.children].map(childSignature) });
    marks?.forEach((mark, position) => {
      if (mark !== null) element.children[position]?.setAttribute("data-df", mark === "added" ? "add" : "chg");
    });
    // 今の範囲を差分の部品へ移す間、置き場所を残す。差分を計算しきれなかったら今の範囲のまま戻す
    const placeholder = document.createComment("");
    element.replaceWith(placeholder);
    const diff = htmlBodyDiff({ before: pair.before, after: pair.after, marked: "", initial: "raw", heading: "埋め込んだ HTML", beforeView, afterView: element });
    placeholder.replaceWith(diff ?? element);
  }
};

// ─── 図の差分 ───

/** 記法の 1 行目の語（図の種類）。先頭の設定の行（`%%`）と空行は読み飛ばす */
const diagramType = (source: string): string => {
  const first = source
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line !== "" && !line.startsWith("%%"));
  return first?.split(/\s+/)[0] ?? "";
};

/** 行の差分を比べやすいよう、記法の末尾を改行 1 つにそろえる */
const withTrailingNewline = (source: string): string => {
  return source.endsWith("\n") ? source : `${source}\n`;
};

/** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする。変えた行の対は、変わった語を濃い面で囲む（`deadline` は、行の差分を呼ぶ直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
export const rawDiffLines = ({ parts, deadline }: { parts: LinePart[]; deadline: number }): HTMLElement[] => {
  const op = { added: "add", removed: "del", same: "same" } as const;
  // 対の行ごとの語の差分（`parts` の添え字 → 行ごと）。対の行ごとに 1 回だけ比べ、消した側と足した側に同じ結果を使う
  const inlines = new Map<number, (InlineDiff | null)[]>();
  for (const { removed, added } of pairedParts(parts)) {
    const removedLines = parts[removed]?.lines ?? [];
    const addedLines = parts[added]?.lines ?? [];
    const compared = removedLines.map((text, offset) => diffInlineOf(text, addedLines[offset] ?? "", deadline));
    inlines.set(removed, compared);
    inlines.set(added, compared);
  }
  return parts.flatMap((part, position) =>
    part.lines.map((text, offset) => {
      const inline = inlines.get(position)?.[offset] ?? null;
      const pieces = inline === null ? null : part.kind === "removed" ? inline.before : inline.after;
      return h({
        tag: "span",
        attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
        children: [
          ...signMarks(op[part.kind]),
          ...(pieces === null ? [text] : pieces.map((piece) => (piece.kind === "same" ? piece.text : wordMark({ mark: part.kind === "removed" ? "del" : "add", text: piece.text })))),
        ],
      });
    }),
  );
};

/** 前後の版の図の記法の並びから、今の図ごとの前の版の記法を決める。前の版と同じ図は null、前に無い図は空文字列。同じ記法の図を先に組にし、残りを並びの順で組にする */
const pairDiagrams = ({ before, after }: { before: string[]; after: string[] }): (string | null)[] => {
  const free = new Set(before.keys());
  const unchanged = after.map((source) => {
    const match = [...free].find((candidate) => (before[candidate] ?? "").trim() === source.trim());
    if (match === undefined) return false;
    free.delete(match);
    return true;
  });
  const rest = [...free];
  return after.map((_, position) => {
    if (unchanged[position] === true) return null;
    const next = rest.shift();
    return next === undefined ? "" : (before[next] ?? "");
  });
};

/** 図の下に出す、凡例と「削除したもの」 */
const diagramNotes = ({ colored, removed }: { colored: boolean; removed: string[] }): HTMLElement => {
  const legend = colored
    ? h({
      tag: "div",
      attrs: { class: "df-legend" },
      children: [
        h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "追加した"] }),
        h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
      ],
    })
    : h({
      tag: "div",
      attrs: { class: "df-legend" },
      children: [
        h({ tag: "span", attrs: { class: "df-badge df-chg" }, children: [markupIcon("changed"), "変わった図"] }),
        h({ tag: "span", attrs: { class: "muted" }, children: ["図の中の変更は Raw で見られます"] }),
      ],
    });
  return h({
    tag: "figcaption",
    attrs: { class: "df-notes" },
    children: [
      legend,
      removed.length === 0
        ? null
        : h({
          tag: "div",
          attrs: { class: "df-removed" },
          children: [
            h({ tag: "span", attrs: { class: "df-removed-t" }, children: ["削除したもの"] }),
            h({
              tag: "ul",
              children: removed.map((name) =>
                h({ tag: "li", children: [h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: ["−"] }), srOnly("消した: "), name] }),
              ),
            }),
          ],
        }),
    ],
  });
};

/** 図の差分で見つけた要素に色の印を付ける（ノードは枠と面、辺は線、メッセージは文字と線） */
const paintDiagramElement = ({ element, mode }: { element: Element; mode: "add" | "chg" }): void => {
  if (element.matches("text")) {
    element.classList.add(`df-t-${mode}`);
    element.nextElementSibling?.classList.add(`df-e-${mode}`);
    return;
  }
  element.classList.add(element.matches("path") ? `df-e-${mode}` : `df-n-${mode}`);
};

/** 前の版の図を `renderDiagramSvg` で描き、今の版の図と `diffDiagram` で突き合わせる。前の版の図を描けないときと、色を付けない種類・突き合わせを打ち切ったときは null */
const diffByRenderedBefore = async ({ type, beforeSource, afterSvg }: { type: string; beforeSource: string; afterSvg: SVGElement }): Promise<DiagramDiff | null> => {
  const beforeSvg = await renderDiagramSvg(beforeSource);
  if (beforeSvg === null) return null;
  // 前の版の図は、座標を取れるよう画面の外に置いて突き合わせる
  const offscreen = h({
    tag: "div",
    attrs: {
      "aria-hidden": "true",
      style: `position:absolute;top:0;left:${OFFSCREEN_LEFT_PX}px;width:${OFFSCREEN_WIDTH_PX}px`,
    },
    children: [beforeSvg],
  });
  document.body.append(offscreen);
  const diagram = diffDiagram(type, beforeSvg, afterSvg);
  offscreen.remove();
  return diagram;
};

/** 変わった図に、色・凡例と削除したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
export const decorateDiagram = async ({ figure, beforeSource }: { figure: HTMLElement; beforeSource: string }): Promise<void> => {
  const holder = figure.querySelector<HTMLElement>(".mermaid");
  const afterSource = holder?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
  figure.classList.add("df-changed", "df-frame");
  // Raw: 記法の行ごとの差分（打ち切ったときは今の記法のまま）
  const raw = figure.querySelector<HTMLElement>(":scope > .dg-raw");
  const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
  const parts = linePartsOf(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
  if (raw !== null && parts !== null) {
    raw.classList.add("df-raw");
    raw.replaceChildren(...rawDiffLines({ parts, deadline }));
  }
  const type = diagramType(afterSource);
  const afterSvg = holder?.querySelector<SVGElement>("svg") ?? null;
  let colored = false;
  let removed: string[] = [];
  if (afterSvg !== null && COLORED_DIAGRAM_TYPES.includes(type) && beforeSource.trim() !== "") {
    // flowchart は前後の記法の解析で突き合わせ、前の版を描かない。null（flowchart でない・解析できない）の図だけ前の版を描く
    const diagram =
      (await diffDiagramFromSource(type, beforeSource, afterSource, afterSvg)) ?? (await diffByRenderedBefore({ type, beforeSource, afterSvg }));
    if (diagram !== null) {
      for (const element of diagram.added) paintDiagramElement({ element, mode: "add" });
      for (const element of diagram.changed) paintDiagramElement({ element, mode: "chg" });
      removed = diagram.removed;
      colored = true;
    }
  }
  figure.classList.toggle("df-frame", !colored);
  figure.classList.toggle("df-colored", colored);
  figure.append(diagramNotes({ colored, removed }));
  // 図の拡大が、同じ凡例と Raw の差分を出せるようになる
  figure.setAttribute(BEFORE_SOURCE_ATTR, beforeSource);
};

/** 差分の表示の間、今の本文の図のうち前の版から変わったものを、色・凡例・Raw の差分で示す */
export const decorateDiagrams = ({ root, before }: { root: HTMLElement; before: string }): void => {
  const afterFigures = [...root.querySelectorAll<HTMLElement>("figure.diagram")];
  if (afterFigures.length === 0) return;
  const sourceOf = (figure: ParentNode): string => figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
  const beforeSources = [...renderMarkdown(before).querySelectorAll("figure.diagram")].map(sourceOf);
  const pairs = pairDiagrams({ before: beforeSources, after: afterFigures.map(sourceOf) });
  afterFigures.forEach((figure, position) => {
    const beforeSource = pairs[position];
    // 前の版と同じ図は印を付けない
    if (beforeSource === null || beforeSource === undefined) return;
    void decorateDiagram({ figure, beforeSource });
  });
};

// ─── 詳細の中身 ───


/** 節の見出し（h3）の次に置く、本文・値の見出しのうち最も上の段 */
const SECTION_TOP_HEADING_LEVEL = 4;


/** 見出しの要素の最も下の段（h6） */
const LOWEST_HEADING_LEVEL = 6;

/** 見出しの要素の段（h1〜h6 の数字） */
const headingLevel = (heading: HTMLElement): number => {
  return Number(heading.tagName.slice(1));
};

/** 見出しのうち最も上の段を top（省略すると節の見出しの次の段）にするための、全ての見出しに足す段の差。見出しが無ければ 0 */
export const headingShift = ({ roots, top = SECTION_TOP_HEADING_LEVEL }: { roots: HTMLElement[]; top?: number }): number => {
  const levels = roots.flatMap((root) => [...root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")].map(headingLevel));
  return levels.length === 0 ? 0 : top - Math.min(...levels);
};

/** 本文・値の見出しに渡された段の差を足して並べる（`headingShift` が求めた差なら h3〜h6 になる）。見た目は元の段のまま（`data-md-level`） */
export const lowerHeadings = ({ root, shift }: { root: HTMLElement; shift: number }): void => {
  for (const heading of root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")) {
    const level = headingLevel(heading);
    const lowered = Math.min(level + shift, LOWEST_HEADING_LEVEL);
    const replacement = h({
      tag: `h${lowered}` as "h3" | "h4" | "h5" | "h6",
      attrs: {
        "data-md-level": level,
        // 元の Markdown の行の印を引き継ぐ
        [LINE_ATTR]: heading.getAttribute(LINE_ATTR),
        // h6 を超える段は、読み上げの段で伝える
        "aria-level": level + shift > LOWEST_HEADING_LEVEL ? level + shift : null,
      },
      children: [...heading.childNodes],
    });
    heading.replaceWith(replacement);
  }
};

/** 資料の HTML の本文の枠が持つ属性（コメントの一覧から開いたとき、示す箇所を求める枠を引く） */
export const HTML_BODY_ATTR = "data-html-body";

/** Markdown の本文の中の `html` のコードブロックの入れ物を、枠に置き換える。差分の表示の間の足した・消した部分は、枠に描かず原文に印を付けたまま出す */
export const drawHtmlBlocks = (root: HTMLElement): void => {
  for (const block of root.querySelectorAll<HTMLElement>(`.${HTML_BLOCK_CLASS}`)) {
    const source = block.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
    if (block.closest(".mdmark-diff-block") !== null) {
      block.replaceWith(h({ tag: "pre", attrs: { class: "html-block-src", ...CODE_BLOCK_ATTRS }, children: [source] }));
    } else {
      const frame = htmlFrameElement({ source, selectable: false, label: "html のコードブロック" });
      frame.classList.add(HTML_BLOCK_CLASS);
      const line = block.getAttribute(LINE_ATTR);
      if (line !== null) frame.setAttribute(LINE_ATTR, line);
      block.replaceWith(frame);
    }
  }
};

/** 項目の中身（種類ごと）。本文は Markdown と図を描く */
