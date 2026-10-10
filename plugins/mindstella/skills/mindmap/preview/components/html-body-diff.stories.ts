// HTML の本文の差分のストーリー（部品設計『HTMLの本文の差分』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** 選んだ時点の本文（段落を 1 行ずつ持つ） */
const BEFORE = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>二つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 今の本文（2 つ目の段落を書き換えた） */
const AFTER = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>書き換えた二つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 今の本文の行の印つきの HTML */
const MARKED = [
  '<h1 data-line="1">画面の流れ</h1>',
  '<p data-line="2">一つ目の段落</p>',
  '<p data-line="3">書き換えた二つ目の段落</p>',
  '<p data-line="4">三つ目の段落</p>',
].join("\n");

/** 2 つ目の段落を消した今の本文 */
const REMOVED = ["<h1>画面の流れ</h1>", "<p>一つ目の段落</p>", "<p>三つ目の段落</p>"].join("\n");

/** 消した今の本文の行の印つきの HTML */
const REMOVED_MARKED = ['<h1 data-line="1">画面の流れ</h1>', '<p data-line="2">一つ目の段落</p>', '<p data-line="3">三つ目の段落</p>'].join("\n");

const meta = {
  title: "Preview/HtmlBodyDiff",
  render: (args) => {
    const stage = document.createElement("div");
    const diff = MindmapPreview.htmlBodyDiff(args);
    if (diff !== null) stage.append(diff);
    return stage;
  },
  args: { before: BEFORE, after: AFTER, marked: MARKED },
} satisfies Meta<MindmapPreview.HtmlBodyDiffProps>;

export default meta;

type Story = StoryObj<MindmapPreview.HtmlBodyDiffProps>;

/** 既定。描いた結果で、変えた 2 つ目の段落に「変わった」の印。上に「描いた結果」「原文の差分」の切り替えと、「足した」「変わった」の凡例 */
export const Rendered: Story = {};

/** 「原文の差分」に切り替えた。消した行と足した行を記号と色で出し、変わっていない長い並びは前後 3 行を残して「変わっていない {数} 行」に畳む */
export const RawDiff: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLButtonElement>('.segment button[aria-pressed="false"]')?.click();
  },
};

/** 段落を消しただけ。描いた結果には印を付けられないため、凡例に「消した箇所は原文の差分で見られます」を添える */
export const RemovedOnly: Story = { args: { before: BEFORE, after: REMOVED, marked: REMOVED_MARKED } };

/** 選んだ時点の本文が Markdown。切り替えを出さず、原文の差分だけを出す */
export const FromMarkdown: Story = {
  args: { before: "# 画面の流れ\n\n一つ目の段落\n", after: AFTER, marked: MARKED, beforeFormat: "md" },
};
