/* eslint-disable @typescript-eslint/no-non-null-assertion -- 正規表現の捕捉と描いた直後の要素を指す */
// HTML の本文の差分
import { getLibrary } from "@/shared/adapters/libraries";
import { rawDiffLines } from "@/shared/core/body-render";
import { diffLineParts, htmlChangedLines, LINE_DIFF_TIMEOUT_MS, type JsDiff, type LinePart } from "@/shared/core/diff";
import { h } from "@/shared/core/dom-parts";
import { htmlFrameElement } from "@/shared/core/html-frame";

const jsdiffOf = (): JsDiff => getLibrary("jsdiff") as JsDiff;

/** HTML の本文の差分の引数 */
export type HtmlBodyDiffProps = {
  /** 選んだ時点の本文の原文（`body_diff` で組み立てたもの） */
  before: string;
  /** 今の本文の原文（記録の `bodies`） */
  after: string;
  /** 今の本文の行の印つきの HTML（記録の `marked_bodies`） */
  marked: string;
  /** 選んだ時点の本文の形式。`md`（形式を替えた）のときは描いた結果の印と切り替えを出さず、原文の差分だけを出す */
  beforeFormat?: "md" | "html";
  /** 開いた時点の見せ方。`raw` は「原文の差分」を選んだ状態で開く（埋め込んだ HTML の範囲の差分は `raw`） */
  initial?: "rendered" | "raw";
  /** 選んだ時点の本文を描いた結果。渡したときは見せ方を「描いた結果（変更前）」「描いた結果（変更後）」「原文の差分」の 3 つにし、凡例は「描いた結果（変更後）」でだけ出す */
  beforeView?: HTMLElement | null;
  /** 今の本文を描いた結果で、足した要素・変えた要素にマーカーを付けたもの。渡したときは「描いた結果（変更後）」で `marked` の代わりにこれを出す */
  afterView?: HTMLElement | null;
  /** 切り替えの組の前に出す名前（埋め込んだ HTML の範囲の差分は「埋め込んだ HTML」）。無ければ名前を出さない */
  heading?: string | null;
};

/** 原文の差分で、同じ行がこの数を超えて続くときは前後だけを残して畳む（前後に残す行数） */
const RAW_DIFF_CONTEXT = 3;

/** 原文の行の差分。足した行・消した行に印を付け、変わっていない長い並びは前後 3 行を残して件数の行にする */
const rawDiff = ({ parts }: { parts: LinePart[] }): HTMLElement => {
  const lines: HTMLElement[] = [];
  const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
  parts.forEach((part, position) => {
    // 消した並びのすぐ後の足した並びは、消した並びと対にして渡し、変わった語に面を付ける
    if (part.kind === "added" && parts[position - 1]?.kind === "removed") return;
    const next = parts[position + 1];
    if (part.kind === "removed" && next?.kind === "added") {
      lines.push(...rawDiffLines({ parts: [part, next], deadline }));
      return;
    }
    if (part.kind !== "same" || part.lines.length <= RAW_DIFF_CONTEXT * 2) {
      lines.push(...rawDiffLines({ parts: [part], deadline }));
      return;
    }
    // 先頭・末尾の並びは、変わった行の側だけを残す
    const head = position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
    const tail = position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
    const skipped = part.lines.length - head.length - tail.length;
    lines.push(...rawDiffLines({ parts: [{ kind: "same", lines: head }], deadline }));
    lines.push(h({ tag: "span", attrs: { class: "df-line df-skip" }, children: [`変わっていない ${skipped} 行`] }));
    lines.push(...rawDiffLines({ parts: [{ kind: "same", lines: tail }], deadline }));
  });
  return h({
    tag: "div",
    attrs: { class: "html-diff" },
    children: [
      h({ tag: "p", attrs: { class: "html-diff-head" }, children: ["原文の差分"] }),
      h({ tag: "pre", attrs: { class: "dg-raw df-raw", tabindex: "0", "aria-label": "原文の差分" }, children: lines }),
    ],
  });
};

/** 凡例（足した・変わった）。消しただけの箇所があるときは、原文の差分で見られる旨を添える */
const legend = ({ removedOnly }: { removedOnly: boolean }): HTMLElement => {
  return h({
    tag: "div",
    attrs: { class: "df-legend" },
    children: [
      h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "追加した"] }),
      h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
      removedOnly ? h({ tag: "span", attrs: { class: "muted" }, children: ["削除した箇所は原文の差分で見られます"] }) : null,
    ],
  });
};

/** HTML の本文の差分。差分を計算しきれなかったときは null */
export const htmlBodyDiff = ({
  before,
  after,
  marked,
  beforeFormat = "html",
  initial = "rendered",
  beforeView = null,
  afterView = null,
  heading = null,
}: HtmlBodyDiffProps): HTMLElement | null => {
  const parts = diffLineParts(before, after, jsdiffOf());
  if (parts === null) return null;
  const raw = rawDiff({ parts });
  // 埋め込んだ HTML の範囲の差分: 変更前・変更後の描いた結果と原文の差分の 3 つを切り替える
  if (beforeView !== null) return rangeDiff({ raw, beforeView, afterView, marked, initial, heading });
  // 選んだ時点の本文が Markdown: 描いた結果の印と切り替えを出さず、原文の差分だけを出す
  if (beforeFormat === "md") return raw;
  const changed = htmlChangedLines(before, after, jsdiffOf());
  if (changed === null) return null;
  const marks = { added: changed.added, changed: changed.changed };
  // 選んだ箇所のコメントの入口は出さない（差分の表示の間は今の本文の行と合わない場合がある）
  const rendered = h({
    tag: "div",
    attrs: { class: "html-marked" },
    children: [htmlFrameElement({ source: marked, selectable: false, marks })],
  });
  raw.hidden = true;
  const legendElement = legend({ removedOnly: changed.removedOnly });
  /** 描いた結果と原文の差分を切り替えるボタン */
  const toggle = (label: string, showRaw: boolean): HTMLElement =>
    h({
      tag: "button",
      attrs: {
        type: "button",
        "aria-pressed": String(!showRaw),
        onclick: (event) => {
          const pressed = event.currentTarget as HTMLElement;
          for (const button of pressed.parentElement?.children ?? []) button.setAttribute("aria-pressed", String(button === pressed));
          raw.hidden = !showRaw;
          rendered.hidden = showRaw;
          legendElement.hidden = showRaw;
        },
      },
      children: [label],
    });
  const container = h({
    tag: "div",
    attrs: { class: "html-diff-c" },
    children: [
      h({
        tag: "div",
        attrs: { class: "html-diff-bar" },
        children: [
          headingLabel({ heading }),
          h({
            tag: "div",
            attrs: { class: "segment", role: "group", "aria-label": viewGroupName({ heading }) },
            children: [toggle("描いた結果", false), toggle("原文の差分", true)],
          }),
          legendElement,
        ],
      }),
      rendered,
      raw,
    ],
  });
  // 「原文の差分」を選んだ状態で開く
  if (initial === "raw") container.querySelector<HTMLElement>(".segment button:last-child")?.click();
  return container;
};

/** 見せ方の切り替えの組の読み上げの名前 */
const viewGroupName = ({ heading }: { heading: string | null }): string => {
  return heading === null ? "本文の差分の見せ方" : `${heading}の差分の見せ方`;
};

/** 切り替えの組の前に出す名前（無ければ null） */
const headingLabel = ({ heading }: { heading: string | null }): HTMLElement | null => {
  return heading === null ? null : h({ tag: "span", attrs: { class: "html-diff-heading" }, children: [heading] });
};

/** 埋め込んだ HTML の範囲の差分。「描いた結果（変更前）」「描いた結果（変更後）」「原文の差分」を切り替える。凡例は「描いた結果（変更後）」でだけ出す */
const rangeDiff = ({
  raw,
  beforeView,
  afterView,
  marked,
  initial,
  heading,
}: {
  raw: HTMLElement;
  beforeView: HTMLElement;
  afterView: HTMLElement | null;
  marked: string;
  initial: "rendered" | "raw";
  heading: string | null;
}): HTMLElement => {
  const views = [
    { label: "描いた結果（変更前）", element: h({ tag: "div", attrs: { class: "html-marked" }, children: [beforeView] }), legended: false },
    {
      label: "描いた結果（変更後）",
      element: h({
        tag: "div",
        attrs: { class: "html-marked" },
        children: [afterView ?? htmlFrameElement({ source: marked, selectable: false })],
      }),
      legended: true,
    },
    { label: "原文の差分", element: raw, legended: false },
  ];
  const legendElement = legend({ removedOnly: false });
  // 開いた時点の見せ方（`raw` は原文の差分、`rendered` は変更後の描いた結果）
  const first = initial === "raw" ? 2 : 1;
  const show = (position: number): void => {
    views.forEach((view, at) => {
      view.element.hidden = at !== position;
    });
    legendElement.hidden = !views[position]!.legended;
  };
  show(first);
  return h({
    tag: "div",
    attrs: { class: "html-diff-c html-diff-range" },
    children: [
      h({
        tag: "div",
        attrs: { class: "html-diff-bar" },
        children: [
          headingLabel({ heading }),
          h({
            tag: "div",
            attrs: { class: "segment", role: "group", "aria-label": viewGroupName({ heading }) },
            children: views.map((view, position) =>
              h({
                tag: "button",
                attrs: {
                  type: "button",
                  "aria-pressed": String(position === first),
                  onclick: (event) => {
                    const pressed = event.currentTarget as HTMLElement;
                    for (const button of pressed.parentElement?.children ?? []) button.setAttribute("aria-pressed", String(button === pressed));
                    show(position);
                  },
                },
                children: [view.label],
              }),
            ),
          }),
          legendElement,
        ],
      }),
      ...views.map((view) => view.element),
    ],
  });
};
