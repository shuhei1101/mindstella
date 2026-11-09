// コメントの入力のストーリー（部品設計『コメントの入力』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/SendForm",
  render: (args) => MindmapPreview.sendForm(args),
  args: {
    target: "D-022",
    on: { input: fn(), save: fn(), unquote: fn(), copy: fn(), focus: fn(), blur: fn(), toggle: fn(), voiceStart: fn(), voiceCancel: fn(), voiceDone: fn(), voiceBlocked: fn() },
  },
} satisfies Meta<MindmapPreview.SendFormProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SendFormProps>;

/** 入力欄が空。本文と線で区切って下端に置き、ラベルで向ける項目の ID を示す。「レビューに追加」は入力欄の右のアイコンだけのボタン */
export const Idle: Story = {};

/** 入力中。入力欄に印の色の輪 */
export const Typing: Story = {
  args: { body: "案 A にする" },
  play: ({ canvasElement }) => {
    canvasElement.querySelector("textarea")?.focus();
  },
};

/** 本文の箇所を添えた。入力欄の上に「本文 3 行目」と選んだ文を出し、× で外せる */
export const WithBodyLocation: Story = {
  args: { target: "A-005", loc: { kind: "body", start: 3, end: 3, text: "受け取る人へ渡す形" } },
};

/** 値の箇所を添えた。箇所の名前にキーの名前を出し、選んだ文は 3 行までにして末尾を省く */
export const WithValueLocation: Story = {
  args: {
    loc: {
      kind: "value",
      key: "options[C].cons",
      text: "表の密度が下がる。表の列を詰めて並べるため、1 行に出せる項目の数が減り、ID と状態の列が画面の外へ押し出される。狭い幅では横に送らないと読めない列が増え、比べるのに手間がかかる",
    },
    body: "ここは別の言い方にしたい",
  },
};

/** 溜めている。入力欄を書き換えられなくし、ボタンを押せなくする。1 秒を超えたら回る印と「レビューに追加しています」を出す */
export const Saving: Story = { args: { body: "案 A にする", status: "saving" } };

/** 溜めた。入力欄を空にし、「レビューに追加しました（レビュー中 3 件）。」を出す。入力を始めたら消す */
export const Saved: Story = { args: { status: "saved", count: 3 } };

/** 本文が空で溜めようとした。入力欄の枠と印を要見直しの赤にし、入れてから追加するよう出す。ボタンは押せるまま */
export const Empty: Story = { args: { status: "empty" } };

/** サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して本文のコピーのボタンを添える */
export const FailedUnreachable: Story = { args: { body: "案 A にする", status: "failed" } };

/** サーバーが溜めなかった理由を返した。本文を残し、理由を出す（本文のコピーのボタンは出さない） */
export const FailedDetail: Story = {
  args: {
    target: "A-005",
    body: "ここは言い換える",
    status: "failed",
    detail: "選んだ文が本文の 3 行目にありません",
  },
};

/** 長文。8 行を超えたら入力欄の中を送る */
export const Long: Story = {
  args: {
    body: [
      "案 A にする。",
      "理由: 読み返す画面なので、表と数値を長く読んでも疲れない無彩色の骨格がよい。",
      "印の色は 1 色に絞る。",
      "状態の色は状態の表示だけに使う。",
      "B のカード中心は一覧が長くなると縦に伸びる。",
      "C のダークは明暗の切り替えで足りる。",
      "トップバーは暗い帯にしておきたい。",
      "ID の等幅は残す。",
      "以上。",
    ].join("\n"),
  },
};

/** 項目を指さないコメント（コメントの一覧の下端）。見出しを出さず、入力欄と「レビューに追加」だけにする */
export const NoTarget: Story = { args: { target: null } };

/** 幅 390px。部品の幅によらず入力欄と「レビューに追加」を 1 行に並べ、結果は入力欄の下に幅いっぱいで出す */
export const Narrow: Story = {
  args: {
    target: "A-005",
    loc: { kind: "body", start: 3, end: 3, text: "受け取る人へ渡す形" },
    body: "案 A にする",
    status: "failed",
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 項目を指さないコメントを畳んだ形。読み上げのラベルと 1 行の入力欄だけを出す */
export const NoTargetCollapsed: Story = {
  args: { target: null, collapsed: true },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 項目を指さないコメントを狭い幅で広げた形。入力欄と「レビューに追加」を出す */
export const NoTargetExpanded: Story = {
  args: { target: null, collapsed: false, body: "全体に目を通した" },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 閉じた。「{ID} へのコメント」の 1 行と、右端の ^ の開閉のボタンだけを出す */
export const Closed: Story = { args: { open: false } };

/** 書きかけを残して閉じた。「{ID} へのコメント」の右に鉛筆の印と「書きかけ」を出す */
export const ClosedWithDraft: Story = { args: { open: false, body: "案 A にする" } };

/** 録音中。マイクと「レビューに追加」の位置に × の「キャンセル」（枠だけ）と ✓ の「文字起こし」（塗り）を置き、結果の行に失敗の色の丸と経過の時間だけを出す（丸は点滅させない） */
export const Recording: Story = { args: { target: "D-022", voice: "recording", elapsed: 12 } };

/** 文字起こし中。2 つのボタンを押せなくし、✓ の位置と結果の行に回る印だけを出す。入力欄は読み取りだけ */
export const Transcribing: Story = { args: { target: "D-022", voice: "transcribing", body: "確認: " } };

/** 打ちかけがある録音中。入力欄の「確認: 」とカーソルの位置を残し、文字起こしの結果はカーソルの位置へ挿入する */
export const RecordingWithDraft: Story = { args: { target: "D-022", voice: "recording", elapsed: 12, body: "確認: " } };

/** 送信した。入力欄を空にし、元のボタンに戻して「送信し、Claude Code へ入力しました。」 */
export const Sent: Story = { args: { target: "D-022", status: "sent", entered: true } };

/** 送信したが Claude Code へ入力しなかった。「送信しました。Claude Code へは入力していません。」 */
export const SentNotEntered: Story = { args: { target: "D-022", status: "sent", entered: false } };

/** 入力欄へ挿入した。カーソルは挿入した文字の後ろで、「文字起こしの結果を挿入しました。」 */
export const Inserted: Story = { args: { target: "D-022", status: "inserted", body: "確認: 案 A にする" } };

/** 文字起こしのサービスが起動していない。マイクのボタンを押せない見た目にし、ホバーとフォーカスで理由のツールチップを出す。「レビューに追加」は押せるまま */
export const VoiceDisabled: Story = { args: { target: "D-022", voice: "disabled", voiceReason: "文字起こしのサービスが起動していないため、音声で入力できません。" } };

/** 文字起こしのサービスが音声の受け付けに対応していない。押せない理由のツールチップ */
export const VoiceUnsupported: Story = { args: { target: "D-022", voice: "disabled", voiceReason: "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。" } };

/** ブラウザがマイクを使えない（HTTPS でない経路から外の端末で開いた）。押せない理由のツールチップ */
export const VoiceNoMicrophone: Story = { args: { target: "D-022", voice: "disabled", voiceReason: "このページではマイクを使用できません。HTTPS か localhost の URL で開いてください。" } };

/** 文字起こしに失敗した。入力欄の中身を残し、元のボタンに戻して理由を結果の行に出す */
export const VoiceFailed: Story = { args: { target: "D-022", status: "voice-failed", detail: "文字起こしできませんでした。もう一度お試しください。", body: "案 B も見たい" } };

/** マイクの許可を拒否した。録音を始めず、許可が要ることを結果の行に出す */
export const VoiceDenied: Story = { args: { target: "D-022", status: "voice-failed", detail: "マイクを使用できませんでした。ブラウザの設定でこのページのマイクを許可してください。" } };

/** 最も狭い幅（320px）の録音中。2 つのボタンはマイクと「レビューに追加」と同じ大きさで、入力欄の右に並んだまま収まる */
export const RecordingNarrow: Story = { args: { target: "D-022", voice: "recording", elapsed: 12 },
  parameters: {
    viewport: {
      options: { narrowest: { name: "幅 320px", styles: { width: "320px", height: "640px" } } },
    },
  },
  globals: { viewport: { value: "narrowest", isRotated: false } } };

/** 文字起こしはできたが送信できなかった。挿入した全文を入力欄に残す */
export const VoiceSendFailed: Story = { args: { target: "D-022", status: "voice-failed", detail: "送信できませんでした。文字起こしの結果は入力欄に残しています。", body: "確認: 案 A にする" } };
