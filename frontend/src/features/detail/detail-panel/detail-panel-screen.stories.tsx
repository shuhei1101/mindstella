// 詳細パネルの画面のストーリー。検討事項の案のカード（記号のアイコン・推奨と採用のバッジ・一覧の下の推奨の理由）と、本文と補足の欄の見分け方・本文の目次を描く
import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";

import { DetailPanel } from "@/features/detail/detail-panel/detail-panel";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";
import { worker } from "@/testing/msw/browser";
import { InStoryRouter } from "@/testing/story-router";

const DECISIONS = [
  {
    id: "D-7",
    title: "計算式の参照の書き方",
    status: "未決定",
    lead: "表の計算式で、ほかの表の値を**どう指すか**を決める。",
    options: [
      { key: "A", content: "セルの番地で指す", pros: "書き方が短い", cons: "行を足すと参照が壊れる" },
      { key: "B", content: "列の名前で指す", pros: "行を足しても参照が壊れない", cons: "名前を付ける手間がかかる", recommended: true, reason: "参照は壊れず、計算式は読める名前で記載できるため" },
    ],
  },
  {
    id: "D-8",
    title: "記録の保存先",
    status: "決定済み",
    answer: "ワークスペースの直下に置く",
    options: [
      { key: "A", content: "ワークスペースの直下", adopted: true, reason: "記録とコードを同じリポジトリで扱える" },
      { key: "B", content: "ホームの設定フォルダ", adopted: false, reason: "端末を移ると記録を持ち出せない" },
    ],
  },
];

/** 本文に見出しを持ち、関連・リンク・参照元を持つ資料 */
const DOCS = [
  {
    id: "A-9",
    title: "記録の保存先の調べ",
    status: "完成",
    description: "記録をどこに置くかを比べた資料",
    body: "docs/A-9.mark.md",
    related: [{ to: "D-8", type: "see_also" }],
    links: [{ title: "保存先の比較の表", url: "https://example.com/storage" }],
  },
  { id: "A-10", title: "セリフの音声", status: "完成", body: "docs/A-10.mark.md" },
];

const NOTES = [{ id: "N-1", title: "保存先のメモ", status: "未整理", content: "A-9 を読み返す", related: [{ to: "A-9", type: "see_also" }] }];

const BODY_A9 = ["# 目的", "", "記録の保存先を決める。", "", "## 保存先", "", "ワークスペースの直下とホームの設定フォルダを比べる。", "", "### 決め方", "", "記録とコードを同じリポジトリで扱えるかで決める。", "", "## 残る論点", "", "端末を移ったときの持ち出し。"].join("\n");

/** 音声を埋め込んだ本文（`files/sample.wav` は Storybook の静的なファイル） */
const BODY_A10 = ["セリフの音声を確かめる。", "", "![セリフの音声](../files/sample.wav)", "", "音声の後ろの段落。"].join("\n");

const DATA = { ...RECORDS, decisions: DECISIONS, docs: DOCS, notes: NOTES, bodies: { "docs/A-9.mark.md": BODY_A9, "docs/A-10.mark.md": BODY_A10 } } as unknown as MindmapData;

const respond = () => worker.use(http.get("*/api/records", () => HttpResponse.json(DATA)));

const panelOf = (id: string, sibling?: { position: number; total: number }) => {
  const Panel = () => <DetailPanel id={id} index={buildIndex(DATA)} {...(sibling === undefined ? {} : { sibling: { ...sibling, onPrev: () => undefined, onNext: () => undefined } })} />;
  return Panel;
};

const meta = {
  title: "Features/Detail/DetailPanelScreen",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  beforeEach: respond,
  args: { path: "/?tab=decisions&id=D-7", screen: panelOf("D-7") },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 未決定の検討事項。記号を左上の丸いアイコン、推奨を本文と分けたバッジにし、推奨の案 B のカードの一番下に「推奨理由」の欄を出す */
export const Recommended: Story = {};

/** 決定済みの検討事項。採用・不採用をバッジにし、理由はカードの中に出す */
export const Decided: Story = { args: { path: "/?tab=decisions&id=D-8", screen: panelOf("D-8") } };

/** 本文に見出しを持つ資料。ヘッダーの目次のボタンから本文の目次を開く */
export const BodyToc: Story = { args: { path: "/?tab=docs&id=A-9", screen: panelOf("A-9") } };


/** 一覧・表・ボードから開いた検討事項。見出しに、元の画面の今の並びで前後の項目へ移るボタンと位置（2 / 3）を出す */
export const SiblingNav: Story = { args: { path: "/?tab=decisions&id=D-7", screen: panelOf("D-7", { position: 2, total: 3 }) } };

/** 並びの末尾の項目。次の項目へ移るボタンは押せない */
export const SiblingNavLast: Story = { args: { path: "/?tab=decisions&id=D-8", screen: panelOf("D-8", { position: 3, total: 3 }) } };

/** 音声を埋め込んだ資料の本文。再生バーの上下を切らずに全体を表示する */
export const AudioBody: Story = { args: { path: "/?tab=docs&id=A-10", screen: panelOf("A-10") } };
