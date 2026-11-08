// 返信の入力のストーリー（部品設計『返信の入力.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ReplyForm } from "@/features/comments/shared/reply-form";


const meta = {
  title: "Comments/ReplyForm",
  component: ReplyForm,
  args: { thread: "TH-2", body: "", status: "idle", onSubmit: fn(), onInput: fn() },
} satisfies Meta<typeof ReplyForm>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 入力欄が空。ラベル「返信」を常に見せ、「レビューに追加」を押せなくする */
export const Empty: Story = { args: { thread: "TH-2" } };

/** 入力中。入力欄に印の色の輪。「レビューに追加」を押せる */
export const Typing: Story = { args: { thread: "TH-2", body: "起票してよい。題は「版の範囲から当てる手順を返すコマンド」に縮めてほしい" } };

/** 溜めている。入力欄を読み取りだけにし、「レビューに追加」を押せなくする。回る印と「レビューに追加しています」 */
export const Saving: Story = { args: { thread: "TH-2", body: "起票してよい", status: "saving" } };

/** 溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す。入力を始めたら消す */
export const Saved: Story = { args: { thread: "TH-2", status: "saved", count: 3 } };

/** サーバーに届かなかった。本文を残し、印のアイコンと「レビューに追加できませんでした。サーバーが止まっています。立ち上げ直してから追加してください。」を出す（自動で消さない） */
export const FailedUnreachable: Story = { args: { thread: "TH-2", body: "起票してよい", status: "failed" } };

/** サーバーが溜めなかった理由を返した。本文を残し、「レビューに追加できませんでした。{理由}」を出す */
export const FailedDetail: Story = { args: { thread: "TH-5", body: "version は文字列で持つ？", status: "failed", detail: "スレッド TH-5 はクローズです" } };

/** 長文。入力欄は 8 行まで広がり、それより長いと中でスクロールする */
export const Long: Story = { args: { thread: "TH-2", body: "1 行目\n2 行目\n3 行目\n4 行目\n5 行目\n6 行目\n7 行目\n8 行目\n9 行目\n10 行目\n11 行目\n12 行目" } };

/** 幅 390px。部品の幅によらず入力欄と「レビューに追加」を 1 行に並べ、結果は入力欄の下に幅いっぱいで出す */
export const Narrow: Story = { args: { thread: "TH-2", body: "起票してよい", status: "failed" } };
