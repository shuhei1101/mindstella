// 文字のトークンの書体の候補を、見本の文と決定事項の画面（ボード・表）で見比べるストーリー。候補ごとに Google Fonts を参照し、`--font-stack-sans` を上書きする
import type { Decorator, Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";
import type { CSSProperties } from "react";

import { DecisionsScreen } from "@/features/decisions/decisions/decisions-screen";
import { worker } from "@/testing/msw/browser";
import { STORY_RECORDS } from "@/testing/msw/story-records";
import { InStoryRouter } from "@/testing/story-router";

type FontCandidate = {
  /** Google Fonts の css2 の family の指定 */
  family: string;
  /** `--font-stack-sans` に入れる値 */
  stack: string;
};

const FONT_CANDIDATES = {
  current: { family: "Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700", stack: '"Inter", "Noto Sans JP", system-ui, sans-serif' },
  ibmPlexSansJp: { family: "IBM+Plex+Sans+JP:wght@400;500;600;700", stack: '"IBM Plex Sans JP", system-ui, sans-serif' },
  bizUdpGothic: { family: "BIZ+UDPGothic:wght@400;700", stack: '"BIZ UDPGothic", system-ui, sans-serif' },
  mPlus2: { family: "M+PLUS+2:wght@400;500;600;700", stack: '"M PLUS 2", system-ui, sans-serif' },
} satisfies Record<string, FontCandidate>;

/** 候補の書体を参照し、子の文字のトークンを上書きする */
const withFont = (candidate: FontCandidate): Decorator => {
  const FontDecorator: Decorator = (Story) => (
    <>
      <link rel="stylesheet" href={`https://fonts.googleapis.com/css2?family=${candidate.family}&display=swap`} />
      <div style={{ "--font-stack-sans": candidate.stack, "--font-sans": candidate.stack, fontFamily: candidate.stack } as CSSProperties}>
        <Story />
      </div>
    </>
  );
  return FontDecorator;
};

/** 見本の文: 見出し・本文・600 の太さ・補足・英数の混ざる文・大きな数字 */
const Specimen = () => (
  <section className="space-y-2 border-b border-border bg-background p-4 text-foreground">
    <h1 className="text-2xl font-bold">検討事項の詳細を読む</h1>
    <p className="text-body">推奨: B — 参照は壊れず、計算式は読める名前で記載できるため。MindStella の TH-150 で決めた方針に従う。</p>
    <p className="text-body font-semibold">未決定の検討事項 3 件・要見直し 1 件（太さ 600）</p>
    <p className="text-small text-muted-foreground">更新 2026-11-22 10:24 JST・Claude Code が 3 件の項目を変更しました</p>
    <p className="text-body">ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 Il1| O0</p>
    <p className="text-4xl font-bold">128</p>
  </section>
);

/** 見本の文の下に、決定事項の画面を描く */
const SpecimenAndDecisions = () => (
  <>
    <Specimen />
    <DecisionsScreen drawerOpen={false} onCloseDrawer={() => undefined} />
  </>
);

const respond = () => worker.use(http.get("*/api/records", () => HttpResponse.json(STORY_RECORDS)));

const BOARD = { args: { path: "/?tab=decisions&view=board", screen: SpecimenAndDecisions } };
const TABLE = { args: { path: "/?tab=decisions&view=table", screen: SpecimenAndDecisions } };

const meta = {
  title: "Pages/FontCandidates",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  beforeEach: respond,
  args: BOARD.args,
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 今の指定（Inter・Noto Sans JP）のボード */
export const CurrentBoard: Story = { ...BOARD, decorators: [withFont(FONT_CANDIDATES.current)] };

/** 今の指定（Inter・Noto Sans JP）の表 */
export const CurrentTable: Story = { ...TABLE, decorators: [withFont(FONT_CANDIDATES.current)] };

/** 案 A: IBM Plex Sans JP（英字と和文を 1 つの書体で統一する）のボード */
export const IbmPlexSansJpBoard: Story = { ...BOARD, decorators: [withFont(FONT_CANDIDATES.ibmPlexSansJp)] };

/** 案 A: IBM Plex Sans JP の表 */
export const IbmPlexSansJpTable: Story = { ...TABLE, decorators: [withFont(FONT_CANDIDATES.ibmPlexSansJp)] };

/** 案 B: BIZ UDPゴシック（ユニバーサルデザインの字形で、小さい字でも読み分けやすい）のボード */
export const BizUdpGothicBoard: Story = { ...BOARD, decorators: [withFont(FONT_CANDIDATES.bizUdpGothic)] };

/** 案 B: BIZ UDPゴシックの表 */
export const BizUdpGothicTable: Story = { ...TABLE, decorators: [withFont(FONT_CANDIDATES.bizUdpGothic)] };

/** 案 C: M PLUS 2（字面が大きく、やわらかい）のボード */
export const MPlus2Board: Story = { ...BOARD, decorators: [withFont(FONT_CANDIDATES.mPlus2)] };

/** 案 C: M PLUS 2 の表 */
export const MPlus2Table: Story = { ...TABLE, decorators: [withFont(FONT_CANDIDATES.mPlus2)] };
