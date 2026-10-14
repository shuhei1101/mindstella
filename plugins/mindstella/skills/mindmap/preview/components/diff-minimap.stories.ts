// 差分のミニマップのストーリー（部品設計『差分のミニマップ』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** ストーリーの引数（部品の引数は `shown` だけで、本文はストーリーが作る） */
type Args = Pick<MindmapPreview.DiffMinimapFrameProps, "shown">;

const { h } = MindmapPreview;

/** 変わらない段落（本文のスクロール領域を超える長さにするための文） */
function plain(number: number): HTMLElement {
  return h({ tag: "p", children: [`変わらない段落 ${number}。本文のスクロール領域を超える長さにするための文です。`] });
}

/** 変わらない段落を `count` 個並べる */
function paragraphs({ from, count }: { from: number; count: number }): HTMLElement[] {
  return Array.from({ length: count }, (_, offset) => plain(from + offset));
}

/** 足した塊・消した塊（差分の記号を頭に置いた囲み） */
function block({ op, text }: { op: "add" | "del"; text: string }): HTMLElement {
  return h({
    tag: op === "add" ? "ins" : "del",
    attrs: { class: "df-blk" },
    children: [h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [op === "add" ? "+" : "−"] }), h({ tag: "p", children: [text] })],
  });
}

/** キーの差分の行（前の値と今の値を並べる） */
function keyRow({ was, now }: { was: string; now: string }): HTMLElement {
  return h({
    tag: "div",
    attrs: { class: "d-value" },
    children: [
      h({
        tag: "span",
        attrs: { class: "df-kv" },
        children: [
          h({ tag: "del", attrs: { class: "df-was" }, children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["前の値: "] }), was] }),
          h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }),
          h({ tag: "ins", attrs: { class: "df-now" }, children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["今の値: "] }), now] }),
        ],
      }),
    ],
  });
}

/** 本文のスクロール領域 */
function bodyOf(children: HTMLElement[]): HTMLElement {
  return h({ tag: "div", attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" }, children });
}

/** 本文（Markdown を描いた領域） */
function markdown(children: HTMLElement[]): HTMLElement {
  return h({ tag: "div", attrs: { class: "md" }, children });
}

/** 足した・消した・変わったの全ての種類の印を持つ本文 */
function kindsBody(): HTMLElement {
  return bodyOf([
    // 前に無かったキーは足した、値が変わったキーは変わった
    keyRow({ was: "（なし）", now: "未決定" }),
    keyRow({ was: "保留", now: "決定済み" }),
    markdown([
      ...paragraphs({ from: 1, count: 6 }),
      block({ op: "add", text: "足した段落" }),
      ...paragraphs({ from: 7, count: 6 }),
      block({ op: "del", text: "消した段落" }),
      ...paragraphs({ from: 13, count: 6 }),
      // 消した塊のすぐ後ろの足した塊は、変わった 1 つにまとめる
      block({ op: "del", text: "書き換える前の段落" }),
      block({ op: "add", text: "書き換えた後の段落" }),
      ...paragraphs({ from: 19, count: 12 }),
    ]),
  ]);
}

/** 本文を置く舞台。部品は見出しと下端の間に置かれるため、高さの決まった縦並びの中に入れる */
function stage({ body, shown }: { body: HTMLElement } & Args): HTMLElement {
  return h({
    tag: "div",
    attrs: {
      style: "display:flex;flex-direction:column;width:min(560px,100%);height:480px;border:1px solid var(--border);background:var(--surface)",
    },
    children: [MindmapPreview.diffMinimapFrame({ body, shown })],
  });
}

const meta = {
  title: "Preview/DiffMinimap",
  render: (args) => stage({ body: kindsBody(), shown: args.shown }),
  args: { shown: true },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 足した・消した・変わったの印。足したは塗りつぶし、消したは枠だけの中抜き、変わったは斜めの縞。前に無かったキーは足した、値が変わったキーは変わった。消した塊のすぐ後ろの足した塊は変わった 1 つにまとめる */
export const Kinds: Story = {};

/** 印が 1 つ。帯を出し、印の長さは最小の 12px */
export const SingleMark: Story = {
  render: (args) => stage({ body: bodyOf([markdown([...paragraphs({ from: 1, count: 20 }), block({ op: "add", text: "足した段落" }), ...paragraphs({ from: 21, count: 20 })])]), shown: args.shown }),
};

/** 本文がスクロール領域に収まる。帯と印は出し、見えている範囲の面は出さない */
export const NotScrollable: Story = {
  render: (args) => stage({ body: bodyOf([markdown([plain(1), block({ op: "add", text: "足した段落" }), plain(2)])]), shown: args.shown }),
};

/** 印が 30 か所。帯に収まるよう印の最小の長さを詰め（下限 4px）、重なる印は後ろへずらして全て並べる */
export const ManyMarks: Story = {
  render: (args) =>
    stage({
      body: bodyOf([
        markdown(
          Array.from({ length: 30 }, (_, at) => [
            block({ op: at % 2 === 0 ? "add" : "del", text: `${at % 2 === 0 ? "足した" : "消した"}段落 ${at + 1}` }),
            plain(at * 2 + 1),
            plain(at * 2 + 2),
          ]).flat(),
        ),
      ]),
      shown: args.shown,
    }),
};

/** 見えている範囲の面をマウスでつかんで下へ動かしている間。面を 1 段濃くし、本文の文を選ばない */
export const Dragging: Story = {
  play: async ({ canvasElement }) => {
    // 印を置いた後に、本文を下へ送り、帯をドラッグ中の見た目にする
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    canvasElement.querySelector<HTMLElement>(".panel-body")?.scrollTo({ top: 240 });
    canvasElement.querySelector<HTMLElement>(".df-map")?.classList.add("is-dragging");
  },
};

/** 差分の表示だが、本文に変わった箇所の印が無い。帯を出さず、本文の幅は帯の無いときと同じ */
export const NoMarks: Story = {
  render: (args) => stage({ body: bodyOf([markdown(paragraphs({ from: 1, count: 20 }))]), shown: args.shown }),
};

/** 差分の表示でないか、表示の設定で差分のミニマップを外した。本文の差分の印があっても帯を出さない */
export const Hidden: Story = {
  args: { shown: false },
};

/** 幅 390px。帯の太さと印の押せる的は変えず、本文の幅を帯の分だけ詰める */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
