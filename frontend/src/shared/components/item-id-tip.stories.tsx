// 項目の ID のツールチップのモック（#147）。本文の項目の ID のリンクに乗せる・フォーカスしたときに出す、本文のマーカーのツールチップと同じ外観のブロック
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { StatusMark } from "@/shared/components/icon";
import { KIND_LABEL, type Item, type Kind } from "@/shared/core/records";

/** ストーリーの引数（ID のリンクが指す項目と種類、リンクを配置する段落の上の余白） */
type Args = { item: Item; kind: Kind; markTop: string };

/** 見本の項目を作る */
const item = ({ id, title, extra = {} }: { id: string; title: string; extra?: Partial<Item> }): Item => ({ id, title, created: "2026-10-01T00:00:00+00:00", updated: "2026-10-01T00:00:00+00:00", ...extra });

/** 本文の CSS（`body.css`）が外観を持つクラスを要素に付ける（Tailwind のクラスではないため、描いた後に付ける） */
const withClass = (name: string) => (node: HTMLElement | null): void => {
  node?.classList.add(name);
};

/** ツールチップの中身。1 行目にタイトルと ID、2 行目に種類と状態（状態を持たない種類は種類だけ） */
const ItemIdTipBody = ({ item: target, kind }: { item: Item; kind: Kind }) => (
  <>
    <span ref={withClass("tt-head")}>
      {target.title}
      <span className="mono">{target.id}</span>
    </span>
    <span ref={withClass("tt-body")} className="flex items-center gap-1.5">
      {KIND_LABEL[kind]}
      {target.status === undefined ? null : (
        <>
          <span aria-hidden="true">・</span>
          <StatusMark status={target.status} />
          {target.status}
        </>
      )}
      {target.withdrawn === true ? <span>・取り下げ</span> : null}
    </span>
  </>
);

/** 本文の項目の ID のリンク（`a.idref`）を持つ段落と、リンクの上に出したツールチップ */
const Host = ({ item: target, kind, markTop }: Args) => {
  const [anchor, setAnchor] = useState<HTMLAnchorElement | null>(null);
  const rect = anchor?.getBoundingClientRect();
  return (
    <div className="md">
      <p style={{ marginTop: markTop }}>
        保存先の扱いは
        <a ref={(node) => { setAnchor(node); withClass("idref")(node); }} href={`#${target.id}`} aria-describedby="item-id-tip">
          {target.id}
        </a>
        で決めたとおりにする。
      </p>
      {rect === undefined ? null : (
        <div id="item-id-tip" role="tooltip" ref={withClass("term-tip")} style={{ position: "fixed", left: rect.left, bottom: innerHeight - rect.top + 6 }}>
          <ItemIdTipBody item={target} kind={kind} />
        </div>
      )}
    </div>
  );
};

const meta = {
  title: "Shared/ItemIdTip",
  component: Host,
  args: { item: item({ id: "D-3", title: "保存先の決め方", extra: { status: "未決定" } }), kind: "decisions", markTop: "45vh" },
} satisfies Meta<typeof Host>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 未決定の検討事項。タイトルと ID、種類と状態のマーカー・状態名を出す */
export const Decision: Story = {};

/** 進行中のタスク */
export const Task: Story = { args: { item: item({ id: "T-12", title: "変更履歴の差分を mdmark の色分けに置き換える", extra: { status: "進行中" } }), kind: "tasks" } };

/** 状態を持たない資料。種類だけを出す */
export const DocWithoutStatus: Story = { args: { item: item({ id: "A-4", title: "話し合いの進め方の手引き" }), kind: "docs" } };

/** 取り下げた調査。種類と状態の後ろに取り下げを出す */
export const Withdrawn: Story = { args: { item: item({ id: "R-2", title: "描画の負荷の測り方", extra: { status: "完了", withdrawn: true } }), kind: "research" } };

/** 長いタイトル。折り返し、画面の端から 8px の内側に収める */
export const LongTitle: Story = {
  args: { item: item({ id: "D-28", title: "配信の途中で視聴者のコメントの量に合わせて補正効果の強さを上げ下げするときの閾値と、急に変えないための遅らせ方", extra: { status: "要見直し" } }), kind: "decisions" },
};
