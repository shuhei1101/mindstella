// スレッドの書き込みのストーリー（部品設計『スレッドの書き込み』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 記録にある項目のタイトル */
const TITLES: Record<string, string> = {
  "D-12": "移し替えが途中で失敗したときの扱い",
  "T-14": "移し替えの失敗の扱いを書く",
  "T-6": "移し替えの手順の YAML を点検する",
  "A-9": "#50 スキルの手順を直す",
  "D-15": "手順の YAML で使える操作の種類",
};

/** 項目のタイトル（記録に無ければ null） */
const titles = (id: string): string | null => TITLES[id] ?? null;

const meta = {
  title: "Preview/ThreadPost",
  render: (args) => {
    const list = document.createElement("ol");
    list.className = "posts";
    list.append(MindmapPreview.threadPost(args));
    return list;
  },
  args: { titles, on: { openId: fn(), edit: fn(), saveEdit: fn(), cancelEdit: fn(), remove: fn() } },
} satisfies Meta<MindmapPreview.ThreadPostProps>;

export default meta;

type Story = StoryObj<MindmapPreview.ThreadPostProps>;

/** レビュー中の返信 */
const PENDING = {
  id: "C-43",
  thread: "TH-1",
  target: null,
  target_title: null,
  loc: null,
  body: "了解。T-14 は今週中に書いてほしい",
  created: "2026-10-12T05:14:00+00:00",
};

/** 利用者の書き込み。右に寄せ、頭に「あなた」と日時 */
export const UserPost: Story = {
  args: { post: { id: "TH-1-1", author: "user", body: "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", created: "2026-10-12T01:20:00+00:00" } },
};

/** AI の書き込み。左に寄せて面の色を変え、頭に「AI」と日時。本文の中の記録にある項目の ID（D-12・T-14）はその項目を開くリンク、改行は保つ */
export const AiPost: Story = {
  args: {
    post: {
      id: "TH-1-2",
      author: "ai",
      body: "D-12 を案 B（写しから戻す）で決定にしました。\n戻す手順を書くタスクを T-14 に足しています。",
      created: "2026-10-12T01:24:00+00:00",
    },
  },
};

/** 本文の中の記録に無い ID（D-99）は文字のまま出す */
export const UnknownId: Story = {
  args: {
    post: { id: "TH-6-1", author: "ai", body: "D-99 は D-12 と重なっているので消してよいですか。", created: "2026-10-12T03:10:00+00:00" },
  },
};

/** 利用者がクローズにした記録。枠の無い 1 行にチェックの印・「あなたがクローズにしました」・日時、次の行に理由 */
export const ClosedEvent: Story = {
  args: { event: { kind: "closed", author: "user", reason: "config.yaml に書くと分かった", created: "2026-10-12T02:10:00+00:00" } },
};

/** 利用者が理由を書かずにオープンに戻した記録。戻す印と「あなたがオープンに戻しました」・日時の 1 行だけ */
export const ReopenedEvent: Story = {
  args: { event: { kind: "reopened", author: "user", reason: null, created: "2026-10-12T00:29:00+00:00" } },
};

/** AI がクローズにした記録。書き手を「AI が」にする */
export const AiClosedEvent: Story = {
  args: { event: { kind: "closed", author: "ai", reason: "了解を受けた", created: "2026-10-12T04:36:00+00:00" } },
};

/** AI がオープンに戻した記録。「AI がオープンに戻しました」と理由 */
export const AiReopenedEvent: Story = {
  args: { event: { kind: "reopened", author: "ai", reason: "質問に答えるため", created: "2026-10-12T02:50:00+00:00" } },
};

/** レビュー中の返信。利用者の書き込みと同じく右に寄せ、破線の枠と頭に「レビュー中」の印、右上に「修正」「削除」を出す */
export const Pending: Story = { args: { pending: PENDING } };

/** レビュー中の返信を書き換えている。本文の代わりに書き換えの入力欄と「キャンセル」「修正」を出し、「修正」「削除」のアイコンは出さない */
export const PendingEditing: Story = { args: { pending: PENDING, editing: true } };

/** 書き換えを保てなかった。入力を残し、印のアイコンと理由を出す */
export const PendingEditFailed: Story = {
  args: { pending: PENDING, editing: true, editError: "サーバーが止まっています。立ち上げ直してから直してください。" },
};

/** 幅 390px。利用者と AI の寄せは保ち、書き込みの幅を部品の幅の 9 割までに広げる */
export const Narrow: Story = {
  args: {
    post: {
      id: "TH-4-4",
      author: "ai",
      body: "T-6 の点検の結果を、版ごとの一覧にした資料 A-9 を足しました。操作の種類は D-15 で決めた 5 つに揃えています。",
      created: "2026-10-12T00:41:00+00:00",
    },
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
