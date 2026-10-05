// コメントの入力のストーリー（部品設計『コメントの入力』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/SendForm",
  render: (args) => MindmapPreview.sendForm(args),
  args: {
    target: "D-022",
    on: { input: fn(), save: fn(), unquote: fn(), copy: fn(), focus: fn(), blur: fn() },
  },
} satisfies Meta<MindmapPreview.SendFormProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SendFormProps>;

/** 入力欄が空。本文と線で区切って下端に置き、ラベルで向ける項目の ID を示す */
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

/** サーバーに届かなかった。本文を残し、立ち上げ直して新しい URL で開くよう出して「本文を写す」を添える */
export const FailedUnreachable: Story = { args: { body: "案 A にする", status: "failed" } };

/** サーバーが溜めなかった理由を返した。本文を残し、理由を出す（「本文を写す」は出さない） */
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

/** 幅 390px。入力の幅が 360px 以下では、結果を下の行に幅いっぱいで出す */
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
