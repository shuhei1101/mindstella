// 本文の折りたたみのストーリー（部品設計『本文の折りたたみ』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 改行で 8 行の本文 */
const EIGHT_LINES = [
  "全体を読み返して気になった点をまとめます。",
  "1. 概要のタイルの並びが毎回変わる",
  "2. 検討事項の表で列の幅が狭い",
  "3. タスクのボードで完了の列が長い",
  "4. 資料のカードの日付が読みにくい",
  "5. ネットワークの玉の色が近い",
  "6. 詳細パネルの本文の図が小さい",
  "7. 変更履歴の時点の並びが分かりにくい",
].join("\n");

/** 改行の無い長文（折り返した後の見た目の行で 5 行を超える） */
const LONG_TEXT =
  "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、冒頭で「何と何を比べているのか」を一文で言い切ってから、選んだ時点の決め方、足した・変えた・消した項目の印の読み方、本文の差分の並べ方の切り替え、図の差分の見方の順に並べると読みやすい。今は印の説明が先に来ていて、何を比べているかが分かる前に細かい話に入っている。";

const meta = {
  title: "Preview/ReviewBodyFold",
  // 本文の下に、開閉のボタンだけの行を並べて描く
  render: (args) => {
    const { body, more } = MindmapPreview.reviewBodyFold(args);
    const list = document.createElement("ul");
    list.className = "comments-list";
    list.style.width = "min(var(--drawer-w), 100%)";
    const row = document.createElement("li");
    row.className = "row";
    row.dataset.comment = args.id;
    const main = document.createElement("div");
    main.className = "row-main";
    const moreRow = document.createElement("div");
    moreRow.className = "review-more-row";
    moreRow.append(more);
    main.append(body, moreRow);
    // 行の左端は送るチェックの列
    row.append(document.createElement("span"), main);
    list.append(row);
    return list;
  },
  args: { id: "C-51", label: "項目を指さないコメント", body: EIGHT_LINES, on: { toggle: fn(), changeSet: fn() } },
} satisfies Meta<MindmapPreview.ReviewBodyFoldProps>;

export default meta;

type Story = StoryObj<MindmapPreview.ReviewBodyFoldProps>;

/** 5 行以下の本文。畳まず、開閉のボタンを出さない（`hidden`） */
export const Short: Story = {
  args: { id: "C-53", label: "TH-1 への返信", body: "書き直しを読みました。\n表はこれで分かりやすくなった" },
};

/** 改行で 8 行の本文。見た目の 5 行目までを出して末尾を「…」で省き、下向きの印と「続きを読む」を出す */
export const FoldedLines: Story = {};

/** 改行の無い長文。折り返した後の見た目の行で 5 行を超えるので畳まれ、「続きを読む」を出す */
export const FoldedWrap: Story = {
  args: { id: "C-52", label: "A-14 へのコメント", body: LONG_TEXT },
};

/** 開いた本文。全文を出し、上向きの印と「折りたたむ」を出す（`aria-expanded="true"`） */
export const Opened: Story = {
  args: { open: true },
};

/** 台の幅 390px。幅が狭くても見た目の 5 行で畳み、「続きを読む」の文字をボタンの中で折り返さない */
export const Narrow: Story = {
  args: {
    id: "C-52",
    label: "A-14 へのコメント",
    body: "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、冒頭で「何と何を比べているのか」を一文で言い切ってから、選んだ時点の決め方、足した・変えた・消した項目の印の読み方、本文の差分の並べ方の切り替え、図の差分の見方の順に並べると読みやすい。",
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
