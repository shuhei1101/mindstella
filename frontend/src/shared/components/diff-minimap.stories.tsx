// 差分のミニマップのストーリー（部品設計『差分のミニマップ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import type { ReactNode } from "react";

import { DiffMinimap } from "@/shared/components/diff-minimap";

/** ストーリーの引数（本文はストーリーが作る） */
type Args = { shown: boolean };

/** 変わらない段落（本文のスクロール領域を超える長さにするための文） */
const plain = (no: number): ReactNode => <p key={`p-${String(no)}`}>{`変わらない段落 ${String(no)}。本文のスクロール領域を超える長さにするための文です。`}</p>;

/** 変わらない段落を `count` 個並べる */
const paragraphs = ({ from, count }: { from: number; count: number }): ReactNode[] => Array.from({ length: count }, (_, offset) => plain(from + offset));

/** mdmark が比較元の Markdown の色分けで描く、追加した・削除した差分のブロック */
const block = ({ op, text }: { op: "add" | "del"; text: string }): ReactNode => (
  <div key={text} className="mdmark-diff-block" data-kind={op}>
    <span className="mdmark-diff-block-sign" aria-hidden="true">
      {op === "add" ? "+" : "−"}
    </span>
    <p>{text}</p>
  </div>
);

/** キーの差分の行（前の値と今の値を並べる） */
const keyRow = ({ was, now }: { was: string; now: string }): ReactNode => (
  <div key={`${was}-${now}`}>
    <span className="df-kv">
      <del className="df-was">
        <span className="sr-only">前の値: </span>
        {was}
      </del>
      <span className="df-arrow" aria-hidden="true">
        →
      </span>
      <ins className="df-now">
        <span className="sr-only">今の値: </span>
        {now}
      </ins>
    </span>
  </div>
);

/** 本文（Markdown を描いた領域） */
const markdown = (children: ReactNode[]): ReactNode => <div className="md">{children}</div>;

/** 足した・消した・変わったの全ての種類の印を持つ本文 */
const KINDS_BODY = [
  // 前に無かったキーは足した、値が変わったキーは変わった
  keyRow({ was: "（なし）", now: "未決定" }),
  keyRow({ was: "保留", now: "決定済み" }),
  <div key="md" className="md">
    {paragraphs({ from: 1, count: 6 })}
    {block({ op: "add", text: "足した段落" })}
    {paragraphs({ from: 7, count: 6 })}
    {block({ op: "del", text: "消した段落" })}
    {paragraphs({ from: 13, count: 6 })}
    {/* 消した塊のすぐ後ろの足した塊は、変わった 1 つにまとめる */}
    {block({ op: "del", text: "書き換える前の段落" })}
    {block({ op: "add", text: "書き換えた後の段落" })}
    {paragraphs({ from: 19, count: 12 })}
  </div>,
];

/** 本文を置く舞台。部品は見出しと下端の間に置かれるため、高さの決まった縦並びの中に入れる */
const Stage = ({ body, shown }: Args & { body: ReactNode }) => (
  <div style={{ display: "flex", flexDirection: "column", width: "min(560px, 100%)", height: "480px", border: "1px solid var(--border)", background: "var(--surface)" }}>
    <DiffMinimap shown={shown}>{body}</DiffMinimap>
  </div>
);

/** 描画が落ち着くまで 2 フレーム待つ */
const settled = async (): Promise<void> =>
  new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => { resolve(); }));
  });

const meta = {
  title: "Shared/DiffMinimap",
  component: Stage,
  render: ({ shown }) => <Stage body={KINDS_BODY} shown={shown} />,
  args: { shown: true, body: null },
} satisfies Meta<typeof Stage>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 足した・消した・変わったの印。足したは塗りつぶし、消したは枠だけの中抜き、変わったは斜めの縞。前に無かったキーは足した、値が変わったキーは変わった。消した塊のすぐ後ろの足した塊は変わった 1 つにまとめる */
export const Kinds: Story = {};

/** 印が 1 つ。帯を出し、印の長さは最小の 12px */
export const SingleMark: Story = {
  render: ({ shown }) => <Stage body={markdown([...paragraphs({ from: 1, count: 40 }), block({ op: "add", text: "足した段落" }), ...paragraphs({ from: 41, count: 40 })])} shown={shown} />,
};

/** 本文がスクロール領域に収まる。帯と印は出し、見えている範囲の面は出さない */
export const NotScrollable: Story = {
  render: ({ shown }) => <Stage body={markdown([plain(1), block({ op: "add", text: "足した段落" }), plain(2)])} shown={shown} />,
};

/** 印が 30 か所。帯に収まるよう印の最小の長さを詰め（下限 4px）、重なる印は後ろへずらして全て並べる */
export const ManyMarks: Story = {
  render: ({ shown }) => (
    <Stage
      body={markdown(
        Array.from({ length: 30 }, (_, at) => [block({ op: at % 2 === 0 ? "add" : "del", text: `${at % 2 === 0 ? "追加した" : "削除した"}段落 ${String(at + 1)}` }), plain(at * 2 + 1), plain(at * 2 + 2)]).flat(),
      )}
      shown={shown}
    />
  ),
};

/** 見えている範囲の面をマウスでつかんで下へ動かしている間。面を 1 段濃くし、本文の文を選ばない */
export const Dragging: Story = {
  play: async ({ canvasElement }) => {
    // 印を置いた後に、本文を下へ送り、帯をドラッグ中の見た目にする
    await settled();
    canvasElement.querySelector<HTMLElement>(".panel-body")?.scrollTo({ top: 240 });
    canvasElement.querySelector<HTMLElement>(".df-map")?.classList.add("is-dragging");
    document.body.classList.add("df-map-dragging");
  },
};

/** 差分の表示だが、本文に変わった箇所の印が無い。帯を出さず、本文の幅は帯の無いときと同じ */
export const NoMarks: Story = {
  render: ({ shown }) => <Stage body={markdown(paragraphs({ from: 1, count: 20 }))} shown={shown} />,
};

/** 差分の表示でないか、表示の設定で差分のミニマップを外した。本文の差分の印があっても帯を出さない */
export const Hidden: Story = { args: { shown: false } };

/** 幅 390px。帯の太さと印の押せる的は変えず、本文の幅を帯の分だけ詰める */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
