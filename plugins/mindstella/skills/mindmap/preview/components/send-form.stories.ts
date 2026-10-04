// 回答・意見の送信のストーリー（部品設計『回答・意見の送信』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/SendForm",
  render: (args) => MindmapPreview.sendForm(args),
  args: {
    target: "D-22",
    onInput: fn(),
    onSend: fn(),
    onCopy: fn(),
  },
} satisfies Meta<MindmapPreview.SendFormProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SendFormProps>;

/** 入力欄が空。本文と線で区切って下端に置き、ラベルで送る先の ID を示す */
export const Idle: Story = {};

/** 入力中。入力欄に印の色の輪 */
export const Typing: Story = {
  args: { body: "案 A にする" },
  play: ({ canvasElement }) => {
    canvasElement.querySelector("textarea")?.focus();
  },
};

/** 送っている。送るボタンを押せず、入力欄を書き換えられない。1 秒を超えたら回る印と「送っています」を出す */
export const Sending: Story = { args: { body: "案 A にする", status: "sending" } };

/** 送った。入力欄を空にし、送った旨と日時を出す */
export const Sent: Story = { args: { status: "sent", sentAt: "2026-10-04T02:23:00+00:00" } };

/** 本文が空で送った。入力欄の枠と印を要見直しの赤にし、入れてから送るよう出す。送るボタンは押せるまま */
export const Empty: Story = { args: { status: "empty" } };

/** サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して「本文を写す」を添える */
export const FailedUnreachable: Story = { args: { body: "案 A にする", status: "failed" } };

/** サーバーが送らなかった理由を返した。本文を残し、理由を出す（「本文を写す」は出さない） */
export const FailedDetail: Story = {
  args: { body: "案 A にする", status: "failed", detail: "項目 D-22 がワークスペースにありません" },
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

/** 幅 390px。入力の幅が 360px 以下では、結果を下の行に幅いっぱいで出す */
export const Narrow: Story = {
  args: { body: "案 A にする", status: "failed" },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
