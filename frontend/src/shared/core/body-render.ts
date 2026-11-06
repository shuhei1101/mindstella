/* eslint-disable @typescript-eslint/no-non-null-assertion -- 今の画面のコードを写した箇所で、正規表現の捕捉と描いた直後の要素を指す */
// 本文の差分の描画（今の画面の `screens/detail.ts` の本文の差分と同じ振る舞い）。mdmark が描いた React の外の DOM に手を入れる
import { getLibrary } from "@/shared/adapters/libraries";
import { DIAGRAM_SOURCE_ATTR, embeddedHtmlRanges, EMBEDDED_HTML_CLASS, HTML_BLOCK_CLASS, LINE_ATTR, renderDiagramSvg, renderMarkdown, TABLE_WRAP_CLASS } from "@/shared/core/body-links";
import { childMarks, COLORED_DIAGRAM_TYPES, diffDiagram, diffDiagramFromSource, diffInline, diffLineParts, LINE_DIFF_TIMEOUT_MS, pairedParts, pairEmbeddedHtml, placeRemovedBlocks, type DiagramDiff, type InlineDiff, type InlinePart, type JsDiff, type LinePart, type RemovedBlock } from "@/shared/core/diff";
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


/** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
const linesOf = (text: string): string[] => {
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  return lines;
};

/** 今の本文の行（1 始まり）のうち、差分で足した行 */
const addedLines = ({ parts, now }: { parts: LinePart[]; now: string[] }): Set<number> => {
  const added = new Set<number>();
  let line = 0;
  for (const part of parts) {
    if (part.kind === "removed") continue;
    for (let position = 0; position < part.lines.length; position += 1) {
      line += 1;
      // 空行だけの足しは段落の間の空きで、どの塊も足したことにしない
      if (part.kind === "added" && (now[line - 1] ?? "").trim() !== "") added.add(line);
    }
  }
  return added;
};

/** 今の本文の各行が属するブロックの先頭の行を求める。図のコードブロックの中は null（図の差分が示す）。それ以外のコードブロックの中は、中身の最初の行を持つブロックに属する */
export const blockOwners = ({ now, starts }: { now: string[]; starts: number[] }): (number | null)[] => {
  const owners: (number | null)[] = [];
  let fence: { owner: number | null } | null = null;
  now.forEach((text, offset) => {
    const line = offset + 1;
    const opening = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
    if (fence !== null) {
      owners.push(fence.owner);
      // 閉じるフェンス（言語を持たない行）で、コードブロックを出る
      if (opening !== null && opening[2] === "") fence = null;
      return;
    }
    if (opening !== null) {
      fence = { owner: opening[2] === "mermaid" ? null : line + 1 };
      owners.push(fence.owner);
      return;
    }
    // 印を持つブロックのうち、この行以前で最も後ろのもの
    owners.push(starts.filter((start) => start <= line).at(-1) ?? null);
  });
  return owners;
};

/** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
export const diffBlock = ({ op, children }: { op: "add" | "del"; children: Node[] }): HTMLElement => {
  return h({
    tag: op === "add" ? "ins" : "del",
    attrs: { class: "df-blk" },
    children: [...signMarks(op), ...children],
  });
};

/** 本文の足した部分の印を、今の本文の要素に付ける（段落・見出し・コードは囲み、表の行と箇条書きの項目は行の印にする） */
const markAddedBlocks = ({ root, parts, source }: { root: HTMLElement; parts: LinePart[]; source: string }): void => {
  const now = linesOf(source);
  const added = addedLines({ parts, now });
  if (added.size === 0) return;
  const blocks = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
  const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(LINE_ATTR))) });
  const marked = new Set<number>();
  for (const line of added) {
    const owner = owners[line - 1];
    if (owner !== null && owner !== undefined) marked.add(owner);
  }
  for (const block of blocks) {
    if (!marked.has(Number(block.getAttribute(LINE_ATTR)))) continue;
    if (block.tagName === "TR") {
      block.classList.add("df-row", "df-add");
      block.firstElementChild?.prepend(...signMarks("add"));
    } else if (block.tagName === "LI") {
      block.classList.add("df-li-add");
      block.prepend(...signMarks("add"));
    } else {
      // 囲みを元の位置に置いてから、ブロックを囲みの中へ移す
      const wrapper = diffBlock({ op: "add", children: [] });
      block.replaceWith(wrapper);
      wrapper.append(block);
    }
  }
};

/** 消した行を別に描いた要素から、行の印を外す（今の本文の行に対応づけない） */
export const withoutLineMarks = (root: HTMLElement): HTMLElement => {
  for (const element of root.querySelectorAll(`[${LINE_ATTR}]`)) element.removeAttribute(LINE_ATTR);
  return root;
};

/** 消した行の図のコードブロックを、記法の原文だけにする（描かない） */
const plainDiagrams = (root: HTMLElement): void => {
  for (const figure of root.querySelectorAll("figure.diagram")) {
    const source = figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
    figure.replaceWith(h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
  }
};

/** 消した行のかたまりを、別に Markdown として描いた要素にする */
const renderRemoved = (block: RemovedBlock): HTMLElement => {
  const lines = block.tableHeader === null ? block.lines : [...block.tableHeader, ...block.lines];
  const rendered = withoutLineMarks(renderMarkdown(lines.join("\n")));
  plainDiagrams(rendered);
  return rendered;
};

/** 描いた消した行のかたまりと、それが元になる `RemovedBlock` の組 */
type RenderedRemoved = { block: RemovedBlock; rendered: HTMLElement };

/** 描いた消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む。かたまりごとに、差し込んだ語の面を付ける対象のブロックを返す */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
const insertRemovedBlocks = ({ root, blocks }: { root: HTMLElement; blocks: RenderedRemoved[] }): HTMLElement[][] => {
  // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
  const stamped = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
  const lineOf = (element: Element): number => Number(element.getAttribute(LINE_ATTR));
  const placed: HTMLElement[][] = [];
  for (const { block, rendered } of blocks) {
    const target = block.beforeLine === null ? undefined : stamped.find((element) => lineOf(element) >= (block.beforeLine ?? 0));
    const previous = target === undefined ? stamped.at(-1) : stamped[stamped.indexOf(target) - 1];
    // 表の本体の行だけ: 今の表の行の間（表の最後の後も）へ、消した行の印を付けた行として差し込む
    if (block.tableHeader !== null) {
      const rows = [...rendered.querySelectorAll<HTMLElement>("tbody tr")].map((row) => {
        row.classList.add("df-row", "df-del");
        row.firstElementChild?.prepend(...signMarks("del"));
        return row;
      });
      if (target?.tagName === "TR") {
        target.before(...rows);
        placed.push(rows);
        continue;
      }
      if (previous?.tagName === "TR") {
        previous.after(...rows);
        placed.push(rows);
        continue;
      }
    }
    // 囲みの中へ移す前に、語の面を付ける対象のブロックを引く
    placed.push(wordBlocksIn(rendered));
    const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
    if (target === undefined) {
      root.append(piece);
      continue;
    }
    // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む（表は包む入れ物ごと外側にする）
    const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
    const container = outer.closest("ul, ol, table") ?? outer;
    (container.parentElement?.matches(`.${TABLE_WRAP_CLASS}`) === true ? container.parentElement : container).before(piece);
  }
  return placed;
};

/** 前の本文の図のコードブロック（開く行から閉じる行まで。1 始まり）。閉じていないコードブロックは本文の最後まで */
const diagramFenceRanges = (lines: string[]): { open: number; close: number }[] => {
  const ranges: { open: number; close: number }[] = [];
  let open: number | null = null;
  lines.forEach((text, offset) => {
    const fence = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
    if (fence === null) return;
    if (open === null) {
      if (fence[2] === "mermaid") open = offset + 1;
    } else if (fence[2] === "") {
      ranges.push({ open, close: offset + 1 });
      open = null;
    }
  });
  if (open !== null) ranges.push({ open, close: lines.length });
  return ranges;
};

/** 消した行のうち、図のコードブロックの一部だけを消した分を外す（図の差分が示すので、本文には消した行として差し込まない）。図を丸ごと消した分は残す */
const withoutDiagramEdits = ({ parts, before }: { parts: LinePart[]; before: string }): LinePart[] => {
  const ranges = diagramFenceRanges(linesOf(before));
  if (ranges.length === 0) return parts;
  let line = 0;
  return parts.flatMap((part) => {
    if (part.kind === "added") return [part];
    const first = line + 1;
    line += part.lines.length;
    if (part.kind === "same") return [part];
    const last = line;
    // この消した部分に丸ごと入っていない図のコードブロックの行
    const partial = ranges.filter((range) => range.open < first || range.close > last);
    const kept = part.lines.filter((_, offset) => !partial.some((range) => first + offset >= range.open && first + offset <= range.close));
    return kept.length === 0 ? [] : [{ kind: part.kind, lines: kept }];
  });
};

/** 語の面を付ける対象になる、描いたブロック（段落・見出し・箇条書きの項目・表の本体の行）の選び方 */
const WORD_BLOCK_SELECTOR = "p, h1, h2, h3, h4, h5, h6, li, tbody tr";

/** 語の面を付ける対象のブロックか（ほかの対象のブロックを中に持たないもの） */
const isWordBlock = (element: Element): boolean => {
  return element.matches(WORD_BLOCK_SELECTOR) && element.querySelector(WORD_BLOCK_SELECTOR) === null;
};

/** 要素の中の、語の面を付ける対象のブロック（文書の順） */
export const wordBlocksIn = (root: HTMLElement): HTMLElement[] => {
  return [...root.querySelectorAll<HTMLElement>(WORD_BLOCK_SELECTOR)].filter(isWordBlock);
};

/** 足した部分ごとの、足した行（空行を除く）を持つ今のブロックのうち、語の面を付ける対象のもの（足した行の順） */
const addedBlocksByPart = ({ root, parts, now }: { root: HTMLElement; parts: LinePart[]; now: string[] }): Map<number, HTMLElement[]> => {
  const blocks = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
  const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(LINE_ATTR))) });
  const byStart = new Map(blocks.map((block) => [Number(block.getAttribute(LINE_ATTR)), block]));
  const found = new Map<number, HTMLElement[]>();
  let line = 0;
  parts.forEach((part, position) => {
    if (part.kind === "removed") return;
    const here: HTMLElement[] = [];
    for (let position = 0; position < part.lines.length; position += 1) {
      line += 1;
      // 空行だけの足しは段落の間の空きで、どのブロックも足したことにしない
      if (part.kind !== "added" || (now[line - 1] ?? "").trim() === "") continue;
      const owner = owners[line - 1];
      const block = owner === null || owner === undefined ? undefined : byStart.get(owner);
      if (block !== undefined && isWordBlock(block) && !here.includes(block)) here.push(block);
    }
    if (part.kind === "added") found.set(position, here);
  });
  return found;
};

/** 語の面を付ける、消したブロックと足したブロックの対 */
export type WordPair = { removed: HTMLElement; added: HTMLElement };

/** 変えた行の対（`pairedParts`）ごとに、消した部分から描いたブロックと、足した部分の行を持つ今のブロックを前から順に並べ、両方の数が同じときだけ 1 つずつ対にする */
const wordPairs = ({
  root,
  parts,
  now,
  placed,
}: {
  root: HTMLElement;
  parts: LinePart[];
  now: string[];
  placed: HTMLElement[][];
}): WordPair[] => {
  // 消した部分の並びの何番目か（`placed` は消した部分の順）
  const removedOrder = parts.flatMap((part, position) => (part.kind === "removed" ? [position] : []));
  const addedBlocks = addedBlocksByPart({ root, parts, now });
  return pairedParts(parts).flatMap(({ removed, added }) => {
    const removedList = placed[removedOrder.indexOf(removed)] ?? [];
    const addedList = addedBlocks.get(added) ?? [];
    if (removedList.length === 0 || removedList.length !== addedList.length) return [];
    return removedList.map((block, offset) => ({ removed: block, added: addedList[offset]! }));
  });
};

/** 要素の中の、行の印（`signMarks` が入れる記号と読み上げの文字）と、表・リストの構造の間の整形の空白を除いた文字のノード（文書の順） */
const wordTextNodes = (root: HTMLElement): Text[] => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      const parent = node.parentElement;
      const isSign = parent?.closest(".df-sign") != null || parent?.matches(".df-sign + .sr-only") === true;
      const isLayoutSpace = (node.textContent ?? "").trim() === "" && parent?.matches("table, thead, tbody, tr, ul, ol") === true;
      return isSign || isLayoutSpace ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    },
  });
  const nodes: Text[] = [];
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) nodes.push(node as Text);
  return nodes;
};

/** 変わった語の面の要素 */
const wordMark = ({ mark, text }: { mark: "add" | "del"; text: string }): HTMLElement => {
  return h({ tag: "span", attrs: { class: `df-word df-${mark}` }, children: [text] });
};

/** 文字のノードの並びのうち、語の差分の足した・消した部分を面の要素で囲む（ノードをまたぐ部分はノードごとに囲み、ノードの外の要素は分けない） */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
const wrapWords = ({ nodes, parts, mark }: { nodes: Text[]; parts: InlinePart[]; mark: "add" | "del" }): void => {
  // 同じでない部分の、文字の頭からの範囲
  const ranges: { start: number; end: number }[] = [];
  let offset = 0;
  for (const part of parts) {
    if (part.kind !== "same") ranges.push({ start: offset, end: offset + part.text.length });
    offset += part.text.length;
  }
  let nodeStart = 0;
  for (const node of nodes) {
    const text = node.data;
    const nodeEnd = nodeStart + text.length;
    const pieces: (string | HTMLElement)[] = [];
    // ノードの中で、ここまでを pieces に入れた位置
    let cursor = 0;
    for (const range of ranges) {
      const from = Math.max(range.start, nodeStart) - nodeStart;
      const to = Math.min(range.end, nodeEnd) - nodeStart;
      if (from >= to) continue;
      if (from > cursor) pieces.push(text.slice(cursor, from));
      pieces.push(wordMark({ mark, text: text.slice(from, to) }));
      cursor = to;
    }
    nodeStart = nodeEnd;
    if (pieces.length === 0) continue;
    if (cursor < text.length) pieces.push(text.slice(cursor));
    node.replaceWith(...pieces);
  }
};

/** 対の 2 つのブロックの、行の印を除いた文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
export const markWords = ({ pair, deadline }: { pair: WordPair; deadline: number }): void => {
  const removedNodes = wordTextNodes(pair.removed);
  const addedNodes = wordTextNodes(pair.added);
  const inline = diffInlineOf(removedNodes.map((node) => node.data).join(""), addedNodes.map((node) => node.data).join(""), deadline);
  if (inline === null) return;
  wrapWords({ nodes: removedNodes, parts: inline.before, mark: "del" });
  wrapWords({ nodes: addedNodes, parts: inline.after, mark: "add" });
};

/** 描いた本文の差分。`markWords` は、見出し・本文のリンクを付けた後に呼んで、変えた行の対に語の面を付ける */
type BodyDiff = { root: HTMLElement; markWords: () => void };

/** 埋め込んだ HTML の範囲の中の行の差分を、本文の行の差分から外す（範囲の差分は範囲ごとの部品が出す）。前の版の範囲の中の消した行は落とし、今の範囲の中の足した行は変えていない行にして、今の本文の行の数は変えない */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
const withoutEmbeddedHtmlEdits = ({ parts, before, after }: { parts: LinePart[]; before: string; after: string }): LinePart[] => {
  /** 範囲の印の行を含む、範囲の中の行（1 始まり） */
  const linesInRanges = (source: string): Set<number> => {
    const lines = new Set<number>();
    for (const { open, close } of embeddedHtmlRanges(source)) for (let line = open; line <= close; line += 1) lines.add(line);
    return lines;
  };
  const inBefore = linesInRanges(before);
  const inAfter = linesInRanges(after);
  const result: LinePart[] = [];
  /** 同じ種類が続くときは 1 つの並びにまとめて足す */
  const push = (kind: LinePart["kind"], line: string): void => {
    const last = result[result.length - 1];
    if (last?.kind === kind) last.lines.push(line);
    else result.push({ kind, lines: [line] });
  };
  let beforeLine = 1;
  let afterLine = 1;
  for (const part of parts) {
    for (const line of part.lines) {
      if (part.kind === "removed") {
        if (!inBefore.has(beforeLine)) push("removed", line);
        beforeLine += 1;
      } else if (part.kind === "added") {
        push(inAfter.has(afterLine) ? "same" : "added", line);
        afterLine += 1;
      } else {
        push("same", line);
        beforeLine += 1;
        afterLine += 1;
      }
    }
  }
  return result;
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

/** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
export const renderBodyDiff = ({ before, after, deadline }: { before: string; after: string; deadline: number }): BodyDiff | null => {
  const compared = linePartsOf(before, after);
  if (compared === null) return null;
  const parts = withoutDiagramEdits({ parts: withoutEmbeddedHtmlEdits({ parts: compared, before, after }), before });
  const rendered = renderMarkdown(after);
  const removed = placeRemovedBlocks(parts).map((block) => ({ block, rendered: renderRemoved(block) }));
  // 今の本文と消した部分の見出しを合わせた最も上の段から、段の差を 1 つ求める
  const shift = headingShift({ roots: [rendered, ...removed.map((piece) => piece.rendered)] });
  lowerHeadings({ root: rendered, shift });
  for (const piece of removed) lowerHeadings({ root: piece.rendered, shift });
  markAddedBlocks({ root: rendered, parts, source: after });
  const placed = insertRemovedBlocks({ root: rendered, blocks: removed });
  const pairs = wordPairs({ root: rendered, parts, now: linesOf(after), placed });
  return { root: rendered, markWords: () => pairs.forEach((pair) => markWords({ pair, deadline })) };
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

/** 図の下に出す、凡例と「消したもの」 */
const diagramNotes = ({ colored, removed }: { colored: boolean; removed: string[] }): HTMLElement => {
  const legend = colored
    ? h({
      tag: "div",
      attrs: { class: "df-legend" },
      children: [
        h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
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
            h({ tag: "span", attrs: { class: "df-removed-t" }, children: ["消したもの"] }),
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

/** 変わった図に、色・凡例と消したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
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
    if (block.closest(".df-blk") !== null) {
      block.replaceWith(h({ tag: "pre", attrs: { class: "html-block-src" }, children: [source] }));
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
