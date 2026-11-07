// スレッドの行のストーリー（部品設計『スレッドの行.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ThreadRow } from "@/features/comments/shared/thread-row";


const meta = {
  title: "Comments/ThreadRow",
  component: ThreadRow,
  args: { onOpen: fn(), onTag: fn() },
  // 行は `<li>` なので、コメントの一覧と同じく `<ul>` で包む
  decorators: [
    (Story) => (
      <ul className="m-0 list-none p-0">
        <Story />
      </ul>
    ),
  ],
} satisfies Meta<typeof ThreadRow>;

export default meta;

type Story = StoryObj<typeof meta>;

/** オープンで AI が返信した。1 行目に状態の札「オープン」と要約（2 行まで）、2 行目に向けた項目の ID・最後の書き手「AI」・最後の書き込みの日時、行の下にタグ */
export const Replied: Story = { args: { thread: {"id": "TH-1", "status": "open", "tags": ["画面"], "summary": "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった", "target": "D-12", "posts": [{"id": "P-1", "author": "user", "body": "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", "created": "2026-10-12T01:20:00+00:00", "seen": true}, {"id": "P-2", "author": "ai", "body": "D-12 を案 B（写しから戻す）で決定にしました。", "created": "2026-10-12T01:24:00+00:00", "seen": true}], "events": [], "loc": null} } };

/** レビュー中の返信を持つ。2 行目の末尾に破線の枠・鉛筆の印・「レビュー中」の印 */
export const PendingReply: Story = { args: { thread: {"id": "TH-1", "status": "open", "tags": ["画面"], "summary": "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった", "target": "D-12", "posts": [{"id": "P-3", "author": "user", "body": "D-12 は案 B にしたい", "created": "2026-10-12T01:20:00+00:00", "seen": true}, {"id": "P-4", "author": "ai", "body": "D-12 を案 B で決定にしました。", "created": "2026-10-12T01:24:00+00:00", "seen": true}], "events": [], "loc": null}, hasPendingReply: true } };

/** AI が立てたスレッド（利用者の返事待ち）。最後の書き手は「AI」 */
export const Asking: Story = { args: { thread: {"id": "TH-2", "status": "open", "tags": ["起票"], "summary": "D-16 の比べた結果を Issue に起票してよいかの確認。返事待ち", "target": "D-16", "posts": [{"id": "P-5", "author": "ai", "body": "D-16 の比べた結果を Issue に起票してよいですか。", "created": "2026-10-12T04:02:00+00:00", "seen": true}], "events": [], "loc": null} } };

/** 要約がまだ無く、最後の書き手が利用者。題は最初の書き込みの 1 行目を太さを落として出し、書き手は「あなた」 */
export const NoSummary: Story = { args: { thread: {"id": "TH-3", "status": "open", "tags": ["資料"], "summary": null, "target": "A-1", "posts": [{"id": "P-6", "author": "user", "body": "A-1 の背景の節が長いので、3 行にまとめてほしい。経緯は会話ログへのリンクで足りる", "created": "2026-10-12T05:01:00+00:00", "seen": true}], "events": [], "loc": null} } };

/** まだ送っていない、項目へ向けた新しいスレッド。状態の札の代わりに鉛筆の印と「レビュー中」の札、行の枠を破線にする。題は最初の書き込みの 1 行目、書き手は「あなた」、日時は溜めた日時。タグは出さない */
export const PendingNewToItem: Story = { args: { pending: {"id": "C-41", "target": "D-5", "thread": null, "body": "写しは git のコミットで取るほうが戻しやすいと思う", "created": "2026-10-12T05:10:00+00:00", "loc": null} } };

/** まだ送っていない、項目を指さない新しいスレッド。2 行目に ID を出さない */
export const PendingNewFree: Story = { args: { pending: {"id": "C-42", "target": null, "thread": null, "body": "移し替えの手順の名前は版の番号だけでよい？", "created": "2026-10-12T05:12:00+00:00", "loc": null} } };

/** クローズ。状態の札をチェックの印と「クローズ」にし、薄い文字で出す。利用者と AI のどちらがクローズにしても同じ見た目 */
export const Closed: Story = { args: { thread: {"id": "TH-5", "status": "closed", "tags": ["画面"], "summary": "D-2 の版の置き場所の質問。config.yaml に書くと回答", "target": "D-2", "posts": [{"id": "P-7", "author": "user", "body": "版はどこに書く？", "created": "2026-10-12T02:00:00+00:00", "seen": true}, {"id": "P-8", "author": "ai", "body": "config.yaml の version に書きます。", "created": "2026-10-12T02:03:00+00:00", "seen": true}], "events": [{"kind": "closed", "author": "user", "reason": "config.yaml に書くと分かった", "created": "2026-10-12T02:10:00+00:00"}], "loc": null} } };

/** 長い要約・タグが 2 つ・項目を指さない。要約は 2 行で末尾を省き、2 行目に ID を出さない */
export const Long: Story = { args: { thread: {"id": "TH-4", "status": "open", "tags": ["調査", "画面"], "summary": "移し替えの手順を画面で見られるかの質問。今は見られず、T-6 の点検の結果を、版ごとの操作の一覧にした資料 A-9 にまとめることになった", "target": null, "posts": [{"id": "P-9", "author": "user", "body": "移し替えの手順は、プレビューのどこかで見られる？", "created": "2026-10-12T00:10:00+00:00", "seen": true}, {"id": "P-10", "author": "ai", "body": "資料 A-9 を足しました。", "created": "2026-10-12T00:41:00+00:00", "seen": true}], "events": [], "loc": null} } };

/** タグ「画面」で絞っている。そのタグの札を枠の全体と面で示し、押した状態として読み上げる */
export const Tagged: Story = { args: { thread: {"id": "TH-4", "status": "open", "tags": ["調査", "画面"], "summary": "移し替えの手順を画面で見られるかの質問", "target": null, "posts": [{"id": "P-11", "author": "ai", "body": "資料 A-9 を足しました。", "created": "2026-10-12T00:41:00+00:00", "seen": true}], "events": [], "loc": null}, activeTag: "画面" } };

/** 幅 390px。2 行目の値は折り返さず、日時を残して ID から詰める。タグは行の下で折り返す */
export const Narrow: Story = { args: { thread: {"id": "TH-1", "status": "open", "tags": ["画面"], "summary": "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった", "target": "D-12", "posts": [{"id": "P-12", "author": "ai", "body": "D-12 を案 B で決定にしました。", "created": "2026-10-12T01:24:00+00:00", "seen": true}], "events": [], "loc": null}, hasPendingReply: true } };

/** オープンで AI の返信が利用者の未読。2 行目の先頭に塗りつぶしの札「● 未読」を出し、向けた項目の ID・最後の書き手「AI」・日時をその右に並べる */
export const Unread: Story = { args: { thread: {"id": "TH-2", "status": "open", "tags": ["起票"], "summary": "D-16 の比べた結果を Issue に起票してよいかの確認。返事待ち", "target": "D-16", "posts": [{"id": "P-13", "author": "ai", "body": "D-16 の比べた結果を Issue に起票してよいですか。", "created": "2026-10-12T04:02:00+00:00", "seen": false}], "events": [], "loc": null} } };

/** 未読で、レビュー中の返信も持つ。2 行目の先頭に「● 未読」、末尾に破線の枠の「レビュー中」を出し、形（塗りつぶしと破線の枠）で見分ける */
export const UnreadPendingReply: Story = { args: { thread: {"id": "TH-1", "status": "open", "tags": ["画面"], "summary": "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった", "target": "D-12", "posts": [{"id": "P-14", "author": "user", "body": "D-12 は案 B にしたい", "created": "2026-10-12T01:20:00+00:00", "seen": true}, {"id": "P-15", "author": "ai", "body": "D-12 を案 B で決定にしました。", "created": "2026-10-12T01:24:00+00:00", "seen": false}], "events": [], "loc": null}, hasPendingReply: true } };

/** AI が返信してからクローズにし、返信が利用者の未読。状態の札「クローズ」のまま、2 行目の先頭に「● 未読」を出す */
export const UnreadClosed: Story = { args: { thread: {"id": "TH-6", "status": "closed", "tags": ["起票"], "summary": "T-4 の Issue の起票の確認。起票して完了", "target": "T-4", "posts": [{"id": "P-16", "author": "user", "body": "起票してよい", "created": "2026-10-12T03:00:00+00:00", "seen": true}, {"id": "P-17", "author": "ai", "body": "T-4 の Issue を起票しました。", "created": "2026-10-12T03:07:00+00:00", "seen": false}], "events": [{"kind": "closed", "author": "ai", "reason": "起票した", "created": "2026-10-12T03:07:00+00:00"}], "loc": null} } };
