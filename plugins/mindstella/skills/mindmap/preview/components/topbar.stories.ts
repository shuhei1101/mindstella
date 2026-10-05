// トップバーのストーリー（部品設計『トップバー』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/Topbar",
  // ダークのときは、画面全体の色の組も切り替える（アプリが `data-theme` に持つ値と同じ）
  render: (args) => {
    document.documentElement.dataset["theme"] = args.theme;
    return MindmapPreview.topbar(args);
  },
  args: {
    title: "要件出しのスキル mindmap を設計する",
    tabs: [
      { key: "overview", label: "概要", icon: "home" },
      { key: "decisions", label: "検討事項", icon: "decision", count: 12 },
      { key: "tasks", label: "タスク", icon: "task", count: 8 },
      { key: "research", label: "調査", icon: "research", count: 3 },
      { key: "docs", label: "資料", icon: "doc", count: 5 },
      { key: "terms", label: "用語集", icon: "term", count: 9 },
      { key: "notes", label: "メモ", icon: "note", count: 4 },
      { key: "logs", label: "会話ログ", icon: "log", count: 20 },
    ],
    current: "overview",
    theme: "light",
    onNavigate: fn(),
    onSearch: fn(),
    onTheme: fn(),
  },
} satisfies Meta<MindmapPreview.TopbarProps>;

export default meta;

type Story = StoryObj<MindmapPreview.TopbarProps>;

/** 概要を開いている。開いている画面のタブに印の色の下線 */
export const Overview: Story = { args: { current: "overview" } };

/** つながりを開いている。つながりの入口だけを選んだ見た目にする */
export const Graph: Story = { args: { current: "graph" } };

/** 題名が長い。1 行で末尾を省略し、検索の入口とテーマの切り替えを押し出さない */
export const LongTitle: Story = {
  args: {
    title:
      "プレビューの画面（概要・検討事項・タスク・資料・つながり・詳細パネル）を見本に沿って作るための話し合いの記録",
  },
};

/** ダーク */
export const Dark: Story = { args: { theme: "dark" } };

/** 幅 390px。検索の入口を虫眼鏡だけにし、題名を隠す。タブは帯の中で横に送る */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** サーバーにつながらない。検索の入口の左に、印と読んだ日時つきの接続の状態を出す */
export const Offline: Story = {
  args: { connection: "offline", readAt: "2026-10-04T02:21:00+00:00" },
};

/** 幅 390px でサーバーにつながらない。「つながりません」だけを出し、読んだ日時を title に持つ */
export const OfflineNarrow: Story = {
  args: { connection: "offline", readAt: "2026-10-04T02:21:00+00:00" },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 変更履歴で「前回開いてから」を選んだ間。「変更履歴」の右に札と ×、検討事項・資料のタブに点 */
export const DiffOn: Story = {
  args: {
    diffPoint: { name: "前回開いてから", sub: "10/04 13:05 より後" },
    onHistory: fn(),
    onDiffOff: fn(),
    tabs: [
      { key: "overview", label: "概要", icon: "home" },
      { key: "decisions", label: "検討事項", icon: "decision", count: 12, marked: true },
      { key: "tasks", label: "タスク", icon: "task", count: 8 },
      { key: "research", label: "調査", icon: "research", count: 3 },
      { key: "docs", label: "資料", icon: "doc", count: 5, marked: true },
      { key: "terms", label: "用語集", icon: "term", count: 9 },
      { key: "notes", label: "メモ", icon: "note", count: 4 },
      { key: "logs", label: "会話ログ", icon: "log", count: 20 },
    ],
  },
};

/** 幅 390px のサーバーの配信で、差分の表示の間。「変更履歴」とコメントのボタンをアイコン（コメントは件数も）だけにし、札の名前の末尾を省略して、コメントのボタンと × を押し出さずに収める */
export const DiffOnNarrow: Story = {
  args: {
    diffPoint: { name: "フェーズの切り方を見直しに戻す", sub: "10/04 14:45" },
    onHistory: fn(),
    onDiffOff: fn(),
    comments: true,
    commentCount: 3,
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** コメントのボタンを右端に置き、全体の検索の入口を中央へ寄せる。件数を塗りで出す */
export const Comments: Story = { args: { comments: true, commentCount: 3 } };

/** レビュー中のコメントが 0 件。押せるまま、件数の塗りを外して目立たせない */
export const CommentsZero: Story = { args: { comments: true, commentCount: 0 } };

/** 100 件以上。件数を 99+ にし、読み上げの名前には実際の件数を持つ */
export const CommentsMany: Story = { args: { comments: true, commentCount: 120 } };

/** コメントの一覧を開いている。ボタンを枠と面で選んだ見た目にする */
export const CommentsOpen: Story = { args: { comments: true, commentCount: 3, commentsOpen: true } };

/** 幅 390px。コメントのボタンの文字を隠し、印と件数だけにする */
export const CommentsNarrow: Story = {
  args: { comments: true, commentCount: 3 },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
