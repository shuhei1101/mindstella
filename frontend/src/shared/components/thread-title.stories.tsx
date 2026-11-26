// スレッドの見出しのタイトルのストーリー（全文・1 行に省略・長い英字の 1 単語）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { ThreadTitle } from "@/shared/components/thread-title";
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

const SIX_LINES = "長文の書き込みで始めたスレッドのタイトルで、コメントの一覧のパネルの幅では何行にも折り返して見出しが高くなり、書き込みの並びと返信の入力欄を圧迫する。スクロールしたら 1 行にして、末尾を省略の記号にする。全文は乗せると出る説明で参照できる。一番上に戻ると全文に戻る。";

/** 見本の記録にある ID と中身（D-99 は記録に無い） */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

const meta = {
  title: "Shared/ThreadTitle",
  component: ThreadTitle,
  args: { title: SIX_LINES, collapsed: false, lookup },
  // コメントの一覧のパネルと同じ幅の見出しに配置する
  decorators: [
    (Story) => (
      <div className="w-96 max-w-full">
        <h2 className="m-0 flex items-center gap-2 border-b border-border px-3 py-2 text-body font-medium">
          <Story />
        </h2>
      </div>
    ),
  ],
} satisfies Meta<typeof ThreadTitle>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 書き込みの並びが一番上。6 行に折り返す長いタイトルを 2 行で省略し、下に「続きを表示」を出す */
export const FullSixLines: Story = {};

/** 「続きを表示」を押した後。全文を出し、下に「折りたたむ」を出す */
export const Expanded: Story = {
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole("button", { name: "タイトルの続きを表示" }));
  },
};

/** 改行の無い 3000 文字を超えるタイトル。2 行で省略し、パネルの右端を超えない */
export const LongText: Story = { args: { title: "長文の音声入力の書き込みから作ったスレッドのタイトル。".repeat(120) } };

/** 改行の無い 3000 文字を超えるタイトルの全文。見出しの中でスクロールし、書き込みの並びを押し出さない */
export const LongTextExpanded: Story = {
  args: { title: "長文の音声入力の書き込みから作ったスレッドのタイトル。".repeat(120) },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole("button", { name: "タイトルの続きを表示" }));
  },
};

/** 2 行に収まる短いタイトル。開閉のボタンを出さない */
export const Short: Story = { args: { title: "保存先の決め方の相談" } };

/** スクロールした後。1 行にして末尾を「…」にする */
export const Collapsed: Story = { args: { collapsed: true } };

/** 3 行のタイトル */
export const FullThreeLines: Story = { args: { title: "長文の書き込みで始めたスレッドのタイトル。コメントの一覧のパネルの幅では 3 行に折り返して、見出しが高くなる。" } };

/** 1 単語の長い英字。全文のときもパネルの幅で折り返す */
export const LongWord: Story = { args: { title: "configuration-of-the-preview-server-and-the-workspace-settings-file-path" } };

/** 1 単語の長い英字をスクロールした後。1 行にして末尾を「…」にする */
export const LongWordCollapsed: Story = { args: { title: "configuration-of-the-preview-server-and-the-workspace-settings-file-path", collapsed: true } };

/** 記録にある D-1・TH-1 と記録に無い D-99 を持つタイトル。D-1・TH-1 はリンク、D-99 は文字のまま */
export const TitleIdLinks: Story = { args: { title: "D-1 の決め方（TH-1 の続き、D-99 は除く）", collapsed: false } };

/** ID のリンクを持つタイトルをスクロールした後。1 行にして末尾を「…」にする */
export const TitleIdLinksCollapsed: Story = { args: { title: "D-1 の決め方（TH-1 の続き、D-99 は除く）", collapsed: true } };
