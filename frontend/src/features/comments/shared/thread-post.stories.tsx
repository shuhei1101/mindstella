// スレッドの書き込みのストーリー（部品設計『スレッドの書き込み.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ThreadPost } from "@/features/comments/shared/thread-post";


/** ID から名前を引く関数 */
const lookup =
  (names: Record<string, string>) =>
  (id: string): string | null =>
    names[id] ?? null;

const meta = {
  title: "Comments/ThreadPost",
  component: ThreadPost,
  args: { onOpenItem: fn(), onEditStart: fn(), onEditSubmit: fn(), onEditCancel: fn(), onRemove: fn(), onOpenChangeSet: fn(), onToggle: fn() },
} satisfies Meta<typeof ThreadPost>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 利用者の書き込み。右に寄せ、頭に「あなた」と日時 */
export const UserPost: Story = { args: { post: {"id": "TH-1-1", "author": "user", "body": "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", "created": "2026-10-12T01:20:00+00:00"}, titles: lookup({"D-12": "移し替えが途中で失敗したときの扱い"}) } };

/** AI の書き込み。左に寄せて面の色を変え、頭に「AI」と日時。本文の中の記録にある項目の ID（D-12・T-14）はその項目を開くリンク、改行は保つ */
export const AiPost: Story = { args: { post: {"id": "TH-1-2", "author": "ai", "body": "D-12 を案 B（写しから戻す）で決定にしました。\n戻す手順を書くタスクを T-14 に足しています。", "created": "2026-10-12T01:24:00+00:00"}, titles: lookup({"D-12": "移し替えが途中で失敗したときの扱い", "T-14": "移し替えの失敗の扱いを書く"}) } };

/** 本文の中の記録に無い ID（D-99）は文字のまま出す */
export const UnknownId: Story = { args: { post: {"id": "TH-6-1", "author": "ai", "body": "D-99 は D-12 と重なっているので消してよいですか。", "created": "2026-10-12T03:10:00+00:00"}, titles: lookup({"D-12": "移し替えが途中で失敗したときの扱い"}) } };

/** 利用者がクローズにした記録。枠の無い 1 行にチェックの印・「あなたがクローズにしました」・日時、次の行に理由 */
export const ClosedEvent: Story = { args: { event: {"kind": "closed", "author": "user", "reason": "config.yaml に書くと分かった", "created": "2026-10-12T02:10:00+00:00"} } };

/** 利用者が理由を書かずにオープンに戻した記録。戻す印と「あなたがオープンに戻しました」・日時の 1 行だけ */
export const ReopenedEvent: Story = { args: { event: {"kind": "reopened", "author": "user", "reason": null, "created": "2026-10-12T00:29:00+00:00"} } };

/** AI がクローズにした記録。書き手を「AI が」にする */
export const AiClosedEvent: Story = { args: { event: {"kind": "closed", "author": "ai", "reason": "了解を受けた", "created": "2026-10-12T04:36:00+00:00"} } };

/** AI がオープンに戻した記録。「AI がオープンに戻しました」と理由 */
export const AiReopenedEvent: Story = { args: { event: {"kind": "reopened", "author": "ai", "reason": "質問に答えるため", "created": "2026-10-12T02:50:00+00:00"} } };

/** レビュー中の返信。利用者の書き込みと同じく右に寄せ、破線の枠と頭に「レビュー中」の印、右上に「修正」「削除」を出す。日時は出さない */
export const Pending: Story = { args: { pending: {"id": "C-43", "thread": "TH-1", "target": null, "body": "了解。T-14 は今週中に書いてほしい", "created": "2026-10-12T05:14:00+00:00", "loc": null}, titles: lookup({"T-14": "移し替えの失敗の扱いを書く"}) } };

/** レビュー中の返信を書き換えている。本文の代わりに書き換えの入力欄と「キャンセル」「修正」を出し、「修正」「削除」のアイコンは出さない */
export const PendingEditing: Story = { args: { pending: {"id": "C-43", "thread": "TH-1", "target": null, "body": "了解。T-14 は今週中に書いてほしい", "created": "2026-10-12T05:14:00+00:00", "loc": null}, editing: true } };

/** 書き換えを保てなかった。入力を残し、印のアイコンと理由を出す */
export const PendingEditFailed: Story = { args: { pending: {"id": "C-43", "thread": "TH-1", "target": null, "body": "了解。T-14 は今週中に書いてほしい", "created": "2026-10-12T05:14:00+00:00", "loc": null}, editing: true, editError: "サーバーが止まっています。立ち上げ直してから直してください。" } };

/** 幅 390px。利用者と AI の寄せは保ち、寄せの余白を 32px から 16px に詰める。条件はコメントの一覧のほかの行と同じく画面の幅（720px 以下）で持つ */
export const Narrow: Story = { args: { post: {"id": "TH-4-4", "author": "ai", "body": "T-6 の点検の結果を、版ごとの一覧にした資料 A-9 を足しました。操作の種類は D-15 で決めた 5 つに揃えています。", "created": "2026-10-12T00:41:00+00:00"}, titles: lookup({"T-6": "移し替えの手順の YAML を点検する", "A-9": "#50 スキルの手順を直す", "D-15": "手順の YAML で使える操作の種類"}) } };

/** AI の書き込みの中のまとまりのリンク。「A-14 の手引きの書き直し」だけが色の付いた文字と下線のリンクで、中の A-14 はボタンにしない。外の A-14・D-12 は項目を開くボタン。`[古い手引き](#diff=V-99)` はリンクにせず「古い手引き」だけを出す */
export const ChangeSetLink: Story = { args: { post: {"id": "TH-1-2", "author": "ai", "body": "A-14 の手引きを書き直しました。直したところは [A-14 の手引きの書き直し](#diff=V-6) で見られます。\n表の行の消し方は D-12 で決めたとおりにしています。\n前に相談した版は [古い手引き](#diff=V-99) にありましたが、保持する回数を超えて消えています。", "created": "2026-10-12T01:24:00+00:00"}, titles: lookup({"A-14": "プレビューの差分の読み方（手引き）", "D-12": "移し替えが途中で失敗したときの扱い"}), changeSets: lookup({"V-6": "A-14 の手引きを書き直す"}) } };

/** 利用者の書き込みの中の、まとまりのリンクにしない書き方。`[since から](#diff=since)`・`[ハッシュの例](#tab=docs)` はリンクにせず文言だけを出し、`[その他](#tab=docs&id=A-11&diff=V-5)` は `diff` だけを読んでリンクにする */
export const ChangeSetLinkNotLinked: Story = { args: { post: {"id": "TH-1-3", "author": "user", "body": "[since から](#diff=since) と [ハッシュの例](#tab=docs) は押せなくてよい。[その他](#tab=docs&id=A-11&diff=V-5) は押せる", "created": "2026-10-12T01:31:00+00:00"}, changeSets: lookup({"V-5": "A-11 の段落を直す"}) } };

/** レビュー中の返信の中のまとまりのリンク。破線の枠の中でも同じ見た目のリンクにする */
export const PendingChangeSetLink: Story = { args: { pending: {"id": "C-44", "thread": "TH-1", "target": null, "body": "[A-14 の手引きの書き直し](#diff=V-6) で消した表の行は戻してほしい。T-14 にも関わる", "created": "2026-10-12T05:20:00+00:00", "loc": null}, titles: lookup({"T-14": "移し替えの失敗の扱いを書く"}), changeSets: lookup({"V-6": "A-14 の手引きを書き直す"}) } };

/** 長い文言のまとまりのリンク。行の中で書き込みの幅で折り返す */
export const ChangeSetLinkLong: Story = { args: { post: {"id": "TH-2-1", "author": "ai", "body": "A-11 の段落を [設定のパネルの画面の流れのうち、既定として保存するまでの段落と確かめのダイアログの説明](#diff=V-5) のとおりに直しました。", "created": "2026-10-12T04:02:00+00:00"}, titles: lookup({"A-11": "設定のパネルの画面の流れ（モック）"}), changeSets: lookup({"V-5": "A-11 の段落を直す"}) } };

/** AI の書き込みの Markdown。見出しは `h2`、表は `table`、`python` のコードは言語の札とコピーのボタンを持つ `pre`、`mermaid` は図、`> [!NOTE]` は「補足」の囲みで描かれ、記法の文字は出ない。段落の中の D-1 は項目を開くボタン。生の HTML の `onerror` は取り除かれて動かない */
export const MarkdownPost: Story = { args: { post: {"id": "TH-1-1", "author": "ai", "body": "## 比べた結果\n\nD-1 は案 A が合う。\n\n| 案 | 結果 |\n| --- | --- |\n| A | 成立 |\n\n```python\nprint(\"ok\")\n```\n\n```mermaid\nflowchart LR\n  A --> B\n```\n\n> [!NOTE]\n> 案 B は試していない。\n\n<img src=\"x\" alt=\"無害化の確認の画像\" onerror=\"window.injected = true\">", "created": "2026-10-12T01:24:00+00:00"}, titles: lookup({"D-1": "描画のライブラリ"}) } };

/** レビュー中の返信の Markdown。破線の枠の中で「起票してよい」を太字（`strong`）で描き、`**` は出ない */
export const PendingMarkdown: Story = { args: { pending: {"id": "C-45", "thread": "TH-1", "target": null, "body": "**起票してよい**", "created": "2026-10-12T05:30:00+00:00", "loc": null} } };

/** 改行で 8 行のレビュー中の返信。行の高さの 5 行分までを出し、本文の下の行に下向きの印と「続きを読む」を出す */
export const PendingFolded: Story = { args: { pending: {"id": "C-61", "thread": "TH-1", "target": null, "body": "挙げてもらった点に、優先する順を付けました。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい", "created": "2026-11-04T05:10:00+00:00", "loc": null} } };

/** 開いたレビュー中の返信。全文を出し、本文の下の行に上向きの印と「折りたたむ」を出す（`aria-expanded="true"`） */
export const PendingOpened: Story = { args: { pending: {"id": "C-61", "thread": "TH-1", "target": null, "body": "挙げてもらった点に、優先する順を付けました。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい", "created": "2026-11-04T05:10:00+00:00", "loc": null}, open: true } };

/** 改行で 8 行の AI の書き込み。送った書き込みは畳まず全文を出し、「続きを読む」を出さない */
export const LongAiPost: Story = { args: { post: {"id": "TH-1-2", "author": "ai", "body": "見直して気になった点を挙げます。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい", "created": "2026-11-04T01:24:00+00:00"} } };
