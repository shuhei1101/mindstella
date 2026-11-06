// HTML の本文の差分のストーリー（部品設計『HTMLの本文の差分.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { getLibrary, loadLibrary } from "@/shared/adapters/libraries";
import { BodyDiffLayoutSwitch } from "@/shared/components/body-diff-layout-switch";
import { HtmlBodyDiff, type HtmlBodyDiffProps } from "@/shared/components/html-body-diff";
import { EMBEDDED_HTML_CLASS, renderMarkdown } from "@/shared/core/body-links";
import { childMarks, type JsDiff } from "@/shared/core/diff";

/** 選んだ時点の本文（段落を 1 行ずつ持つ） */
const BEFORE = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>二つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 今の本文（2 つ目の段落を書き換えた） */
const AFTER = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>書き換えた二つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 今の本文の行の印つきの HTML */
const MARKED = [
  '<h1 data-line="1" data-line-end="1">画面の流れ</h1>',
  '<p data-line="2" data-line-end="2">一つ目の段落</p>',
  '<p data-line="3" data-line-end="3">書き換えた二つ目の段落</p>',
  '<p data-line="4" data-line-end="4">三つ目の段落</p>',
].join("\n");

/** 2 つ目の段落を消した今の本文 */
const REMOVED = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 消した今の本文の行の印つきの HTML */
const REMOVED_MARKED = ['<h1 data-line="1" data-line-end="1">画面の流れ</h1>', '<p data-line="2" data-line-end="2">一つ目の段落</p>', '<p data-line="3" data-line-end="3">三つ目の段落</p>'].join("\n");

/** 埋め込んだ HTML の範囲の、選んだ時点（段落 2 つ）と今（2 つ目を書き換え、段落を足した）の原文 */
const RANGE_BEFORE = "```html\n<p>一つ目の段落</p>\n<p>二つ目の段落</p>\n```";
const RANGE_AFTER = "```html\n<p>一つ目の段落</p>\n<p>書き換えた二つ目の段落</p>\n<p>足した段落</p>\n```";

/** 範囲を `<!-- html -->` の印で包んで描いた本文の、範囲の要素 */
const renderedRange = (content: string): HTMLElement | null => renderMarkdown(`<!-- html -->\n${content}\n<!-- /html -->\n`).querySelector<HTMLElement>(`.${EMBEDDED_HTML_CLASS}`);

/** 範囲の差分の引数。今の範囲の直下の要素に、足した・変わったのマーカー（`data-df`）を付ける */
const rangeArgs = (): Partial<HtmlBodyDiffProps> => {
  const beforeView = renderedRange(RANGE_BEFORE);
  const afterView = renderedRange(RANGE_AFTER);
  if (beforeView === null || afterView === null) return {};
  const marks = childMarks({
    before: [...beforeView.children].map((child) => child.outerHTML),
    after: [...afterView.children].map((child) => child.outerHTML),
    jsdiff: getLibrary("jsdiff") as JsDiff,
  });
  marks?.forEach((mark, position) => {
    if (mark !== null) afterView.children[position]?.setAttribute("data-df", mark === "added" ? "add" : "chg");
  });
  return { before: RANGE_BEFORE, after: RANGE_AFTER, marked: "", initial: "raw", heading: "埋め込んだ HTML", beforeView, afterView };
};

/** 範囲の差分のストーリー。描画のライブラリを読んでから、描いた結果の要素を作る */
const rangeStory = {
  loaders: [async () => Promise.all([loadLibrary("mdmark"), loadLibrary("jsdiff")])],
  render: () => <HtmlBodyDiff before="" after="" marked="" {...rangeArgs()} />,
};

/** `selector` に当たる `index` 番目のボタンを、描かれたら押す（本文の差分は描画のライブラリを読んでから描く） */
const pressView = ({ canvas, selector, index = 0 }: { canvas: HTMLElement; selector: string; index?: number }): void => {
  const press = (): boolean => {
    const button = canvas.querySelectorAll<HTMLButtonElement>(selector)[index];
    button?.click();
    return button !== undefined;
  };
  if (press()) return;
  const observer = new MutationObserver(() => {
    if (press()) observer.disconnect();
  });
  observer.observe(canvas, { childList: true, subtree: true });
};

const meta = {
  title: "Shared/HtmlBodyDiff",
  component: HtmlBodyDiff,
  render: (args) => <HtmlBodyDiff {...args} {...(args.layout === "side" ? { layoutSwitch: <BodyDiffLayoutSwitch layout="side" onChange={fn()} /> } : {})} />,
  args: { before: BEFORE, after: AFTER, marked: MARKED },
} satisfies Meta<typeof HtmlBodyDiff>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 既定。描いた結果で、変えた 2 つ目の段落に「変わった」の印。上に「描いた結果」「原文の差分」の切り替えと、「足した」「変わった」の凡例 */
export const Rendered: Story = {};

/** 「原文の差分」に切り替えた。消した行と足した行を記号と色で出し、変わっていない長い並びは前後 3 行を残して「変わっていない {数} 行」に畳む */
export const RawDiff: Story = {
  play: ({ canvasElement }) => {
    pressView({ canvas: canvasElement, selector: '.segment button[aria-pressed="false"]' });
  },
};

/** 段落を消しただけ。描いた結果には印を付けられないため、凡例に「消した箇所は原文の差分で見られます」を添える */
export const RemovedOnly: Story = { args: { before: BEFORE, after: REMOVED, marked: REMOVED_MARKED } };

/** 選んだ時点の本文が Markdown。切り替えを出さず、原文の差分だけを出す */
export const FromMarkdown: Story = { args: { before: "# 画面の流れ\n\n一つ目の段落\n", after: AFTER, marked: MARKED, beforeFormat: "md" } };

/** 左右に並べた描いた結果。左に選んだ時点、右に今の本文を描き、右の変えた 2 つ目の段落にだけ「変わった」の印。切り替えの行に並べ方の組と見せ方の組を並べる */
export const SideRendered: Story = { args: { layout: "side" } };

/** 左右に並べた原文の差分。左に消した行、右に足した行を同じ高さで並べ、片側にしか無い行の向かいは縞の空き。変わっていない長い並びは両方の列にまたがる 1 行に畳む */
export const SideRaw: Story = {
  args: { layout: "side" },
  play: ({ canvasElement }) => {
    pressView({ canvas: canvasElement, selector: '.segment[aria-label="本文の差分の見せ方"] button[aria-pressed="false"]' });
  },
};

/** 選んだ時点の本文が Markdown で、左右に並べた。左は Markdown として描き、右の今の本文には印を付けない */
export const SideFromMarkdown: Story = { args: { before: "# 画面の流れ\n\n一つ目の段落\n", after: AFTER, marked: MARKED, beforeFormat: "md", layout: "side" } };

/** 埋め込んだ HTML の範囲の差分。「埋め込んだ HTML」の名前の後に「描いた結果（変更前）」「描いた結果（変更後）」「原文の差分」を並べ、「原文の差分」を選んだ状態で開く。凡例は出さない */
export const RangeRaw: Story = rangeStory;

/** 範囲の差分で「描いた結果（変更前）」に切り替えた。選んだ時点の範囲を描いた結果をマーカー無しで出し、凡例は出さない */
export const RangeBefore: Story = {
  ...rangeStory,
  play: ({ canvasElement }) => {
    pressView({ canvas: canvasElement, selector: ".segment button", index: 0 });
  },
};

/** 範囲の差分で「描いた結果（変更後）」に切り替えた。今の範囲を描いた結果で、追加した段落に「足した」のマーカーと、「足した」「変わった」の凡例 */
export const RangeAfter: Story = {
  ...rangeStory,
  play: ({ canvasElement }) => {
    pressView({ canvas: canvasElement, selector: ".segment button", index: 1 });
  },
};
