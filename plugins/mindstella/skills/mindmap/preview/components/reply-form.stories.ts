// 返信の入力のストーリー（部品設計『返信の入力』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/ReplyForm",
  render: (args) => MindmapPreview.replyForm(args),
  args: {
    thread: "TH-2",
    on: { input: fn(), save: fn() },
  },
} satisfies Meta<MindmapPreview.ReplyFormProps>;

export default meta;

type Story = StoryObj<MindmapPreview.ReplyFormProps>;

/** 入力欄が空。ラベル「返信」を常に見せ、「レビューに追加」を押せなくする */
export const Empty: Story = {};

/** 入力中。入力欄に印の色の輪。「レビューに追加」を押せる */
export const Typing: Story = {
  args: { body: "起票してよい。題は「版の範囲から当てる手順を返すコマンド」に縮めてほしい" },
  play: ({ canvasElement }) => {
    canvasElement.querySelector("textarea")?.focus();
  },
};

/** 溜めている。入力欄を読み取りだけにし、「レビューに追加」を押せなくする。回る印と「レビューに追加しています」 */
export const Saving: Story = { args: { body: "起票してよい", status: "saving" } };

/** 溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す。入力を始めたら消す */
export const Saved: Story = { args: { status: "saved", count: 3 } };

/** サーバーに届かなかった。本文を残し、印のアイコンと立ち上げ直しの案内を出す（自動で消さない） */
export const FailedUnreachable: Story = { args: { body: "起票してよい", status: "failed" } };

/** サーバーが溜めなかった理由を返した。本文を残し、理由を出す */
export const FailedDetail: Story = {
  args: { thread: "TH-5", body: "version は文字列で持つ？", status: "failed", detail: "スレッド TH-5 はクローズです" },
};

/** 長文。入力欄は 8 行まで広がり、それより長いと中でスクロールする */
export const Long: Story = {
  args: { body: Array.from({ length: 12 }, (_, index) => `${index + 1} 行目`).join("\n") },
};

/** 幅 390px。入力の幅が 360px 以下では、ボタンを右に置いたまま、結果を下の行に幅いっぱいで出す */
export const Narrow: Story = {
  args: { body: "起票してよい", status: "failed" },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
