// スレッドの見出しのタイトルのストーリー（全文・1 行に省略・長い英字の 1 単語）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { ThreadTitle } from "@/shared/components/thread-title";

const SIX_LINES = "長文の書き込みで始めたスレッドのタイトルで、コメントの一覧のパネルの幅では何行にも折り返して見出しが高くなり、書き込みの並びと返信の入力欄を圧迫する。スクロールしたら 1 行にして、末尾を省略の記号にする。全文は乗せると出る説明で参照できる。一番上に戻ると全文に戻る。";

const meta = {
  title: "Shared/ThreadTitle",
  component: ThreadTitle,
  args: { title: SIX_LINES, collapsed: false },
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

/** 書き込みの並びが一番上。6 行に折り返す長いタイトルを全文で出す */
export const FullSixLines: Story = {};

/** スクロールした後。1 行にして末尾を「…」にする */
export const Collapsed: Story = { args: { collapsed: true } };

/** 3 行のタイトル */
export const FullThreeLines: Story = { args: { title: "長文の書き込みで始めたスレッドのタイトル。コメントの一覧のパネルの幅では 3 行に折り返して、見出しが高くなる。" } };

/** 1 単語の長い英字。全文のときもパネルの幅で折り返す */
export const LongWord: Story = { args: { title: "configuration-of-the-preview-server-and-the-workspace-settings-file-path" } };

/** 1 単語の長い英字をスクロールした後。1 行にして末尾を「…」にする */
export const LongWordCollapsed: Story = { args: { title: "configuration-of-the-preview-server-and-the-workspace-settings-file-path", collapsed: true } };
