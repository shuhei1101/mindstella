// 差分のミニマップのストーリー（部品設計『差分のミニマップ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import type { ReactNode } from "react";

import { DiffMinimap } from "@/shared/components/diff-minimap";
import { cn } from "@/shared/lib/cn";

/** ストーリーの引数（本文はストーリーが作る） */
type Args = { shown: boolean };

/** 変わらない段落（本文のスクロール領域を超える長さにするための文） */
const plain = (no: number): ReactNode => <p key={`p-${String(no)}`}>{`変わらない段落 ${String(no)}。本文のスクロール領域を超える長さにするための文です。`}</p>;

/** 変わらない段落を `count` 個並べる */
const paragraphs = ({ from, count }: { from: number; count: number }): ReactNode[] => Array.from({ length: count }, (_, offset) => plain(from + offset));

/** 足した塊・消した塊（差分の記号を頭に置いた囲み） */
const block = ({ op, text }: { op: "add" | "del"; text: string }): ReactNode => {
  const sign = (
    <span className="df-sign" aria-hidden="true">
      {op === "add" ? "+" : "−"}
    </span>
  );
  return op === "add" ? (
    <ins key={text} className="df-blk">
      {sign}
      <p>{text}</p>
    </ins>
  ) : (
    <del key={text} className="df-blk">
      {sign}
      <p>{text}</p>
    </del>
  );
};

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

/** 左右に並べた本文の 1 行（`sbs-row`）。`blocks` が空なら向かいにしか無い行の空き */
const sideRow = ({ key, blocks, changed }: { key: string; blocks: ReactNode[]; changed: boolean }): ReactNode => {
  const gap = blocks.length === 0;
  return (
    <div key={key} className={cn("sbs-row", changed && "sbs-chg", gap && "sbs-gap")} aria-hidden={gap ? "true" : undefined}>
      {gap ? null : markdown(blocks)}
    </div>
  );
};

/** 変えていない段落 6 つの行 */
const unchanged = (from: number): ReactNode[] => paragraphs({ from, count: 6 }).map((paragraph, offset) => sideRow({ key: `u-${String(from + offset)}`, blocks: [paragraph], changed: false }));

/** 本文を左右に並べた状態（左の消した段落と右の足した段落が向かい合う箇所、変えていない段落、右だけの足した段落） */
const SIDE_BY_SIDE_BODY = (
  <div className="sbs">
    <div className="sbs-cols">
      <section className="sbs-col sbs-before" aria-label="選んだ時点の本文">
        {unchanged(1)}
        {sideRow({ key: "c1", blocks: [block({ op: "del", text: "書き換える前の段落" })], changed: true })}
        {unchanged(7)}
        {sideRow({ key: "c2", blocks: [], changed: true })}
      </section>
      <section className="sbs-col sbs-after" aria-label="今の本文">
        {unchanged(1)}
        {sideRow({ key: "c1", blocks: [block({ op: "add", text: "書き換えた後の段落" })], changed: true })}
        {unchanged(7)}
        {sideRow({ key: "c2", blocks: [block({ op: "add", text: "末尾に足した段落" })], changed: true })}
      </section>
    </div>
  </div>
);

/** 本文を置く舞台。部品は見出しと下端の間に置かれるため、高さの決まった縦並びの中に入れる */
const Stage = ({ body, shown, width = 560 }: Args & { body: ReactNode; width?: number }) => (
  <div style={{ display: "flex", flexDirection: "column", width: `min(${String(width)}px, 100%)`, height: "480px", border: "1px solid var(--border)", background: "var(--surface)" }}>
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
        Array.from({ length: 30 }, (_, at) => [block({ op: at % 2 === 0 ? "add" : "del", text: `${at % 2 === 0 ? "足した" : "消した"}段落 ${String(at + 1)}` }), plain(at * 2 + 1), plain(at * 2 + 2)]).flat(),
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

/** 本文を左右に並べている。左の消した塊と右の足した塊が向かい合う箇所は「変わった」1 つ、片側だけの塊はその種類の印を、高さの順に並べる */
export const SideBySide: Story = {
  // 左右に並べるのは本文の幅が 560px 以上のときなので、舞台を広げる
  render: ({ shown }) => <Stage body={SIDE_BY_SIDE_BODY} shown={shown} width={760} />,
};
