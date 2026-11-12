// 返信の入力のストーリー（部品設計『返信の入力.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ReplyForm } from "@/features/comments/shared/reply-form";


const meta = {
  title: "Comments/ReplyForm",
  component: ReplyForm,
  args: { thread: "TH-2", body: "", status: "idle", onSubmit: fn(), onInput: fn(), onVoiceStart: fn(), onVoiceCancel: fn(), onVoiceDone: fn(), onVoiceBlocked: fn() },
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

/** 録音中。マイクと「レビューに追加」の位置に × の「キャンセル」（枠だけ）と ✓ の「文字起こし」（塗り）を置き、結果の行に失敗の色の丸と経過の時間だけを出す（丸は点滅させない）。入力欄の中身とカーソルの位置を残したまま入力欄を隠してキーボードの入力を受け付けず、同じ場所・同じ大きさに `levels` の縦の棒の波形を出す（新しい音量を右端に足し、枠からはみ出した古い棒は左で切る） */
export const Recording: Story = { args: { thread: "TH-1", voice: "recording", elapsed: 12, levels: [0.25, 0.4, 0.7, 0.55, 0.9, 0.6, 0.35, 0.8, 1, 0.65] } };

/** 文字起こし中。2 つのボタンを押せなくし、✓ の位置と結果の行に回る印だけを出す。入力欄は読み取りだけ */
export const Transcribing: Story = { args: { thread: "TH-1", voice: "transcribing", body: "確認: " } };

/** 送信した。入力欄を空にし、元のボタンに戻して「送信し、Claude Code へ入力しました。」 */
export const Sent: Story = { args: { thread: "TH-1", status: "sent", entered: true } };

/** 送信したが Claude Code へ入力しなかった。「送信しました。Claude Code へは入力していません。」 */
export const SentNotEntered: Story = { args: { thread: "TH-1", status: "sent", entered: false } };

/** 入力欄へ挿入した（既定）。カーソルは挿入した文字の後ろで、「文字起こしの結果を挿入しました。」。「レビューに追加」で返信をレビュー中に溜める */
export const Inserted: Story = { args: { thread: "TH-1", status: "inserted", body: "案 A にする" } };

/** 文字起こしのサービスが起動していない。マイクのボタンを押せない見た目にし、ホバーとフォーカスで理由のツールチップを出す。「レビューに追加」は押せるまま */
export const VoiceDisabled: Story = { args: { thread: "TH-1", voice: "disabled", voiceReason: "文字起こしのサービスが起動していないため、音声で入力できません。" } };

/** 文字起こしに失敗した。入力欄の中身を残し、元のボタンに戻して理由を結果の行に出す */
export const VoiceFailed: Story = { args: { thread: "TH-1", status: "voice-failed", detail: "文字起こしできませんでした。もう一度お試しください。", body: "案 B も見たい" } };

/** 最も狭い幅（320px）の録音中。2 つのボタンはマイクと「レビューに追加」と同じ大きさで、入力欄の右に並んだまま収まる */
export const RecordingNarrow: Story = { args: { thread: "TH-1", voice: "recording", elapsed: 12, levels: [0.25, 0.4, 0.7, 0.55, 0.9, 0.6, 0.35, 0.8, 1, 0.65] } };
