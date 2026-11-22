// 詳細パネルの画面のストーリー。検討事項の案のカード（記号のアイコン・推奨と採用のバッジ・一覧の下の推奨の理由）を描く
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

const DATA = { ...RECORDS, decisions: DECISIONS } as unknown as MindmapData;

const respond = () => worker.use(http.get("*/api/records", () => HttpResponse.json(DATA)));

const panelOf = (id: string) => {
  const Panel = () => <DetailPanel id={id} index={buildIndex(DATA)} />;
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

/** 未決定の検討事項。記号を左上の丸いアイコン、推奨を本文と分けたバッジにし、案の一覧の下に推奨の案と推奨の理由を出す */
export const Recommended: Story = {};

/** 決定済みの検討事項。採用・不採用をバッジにし、理由はカードの中に出す */
export const Decided: Story = { args: { path: "/?tab=decisions&id=D-8", screen: panelOf("D-8") } };
