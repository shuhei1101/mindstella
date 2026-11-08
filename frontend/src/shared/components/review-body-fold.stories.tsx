// 本文の折りたたみのストーリー（部品設計『本文の折りたたみ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { ReviewBodyFold } from "@/shared/components/review-body-fold";


/** ID から名前を引く関数 */
const lookup =
  (names: Record<string, string>) =>
  (id: string): string | null =>
    names[id] ?? null;

const meta = {
  title: "Shared/ReviewBodyFold",
  component: ReviewBodyFold,
  args: { id: "C-51", label: "項目を指さないコメント", body: "", open: false, onToggle: fn(), onOpenItem: fn(), onOpenChangeSet: fn(), children: (content, toggle) => <>{content}{toggle}</> },
  // コメントの一覧のパネルと同じ幅に置く（見た目の行の数がパネルの幅で決まる）
  decorators: [
    (Story) => (
      <div className="w-96 max-w-full">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof ReviewBodyFold>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 5 行以下の本文。畳まず、開閉のボタンを出さない（`hidden`） */
export const Short: Story = { args: { id: "C-53", label: "TH-1 への返信", body: "書き直しを読みました。\n表はこれで分かりやすくなった" } };

/** 改行で 8 行の本文。行の高さの 5 行分までを出してはみ出しを隠し、下向きの印と「続きを読む」を出す */
export const FoldedLines: Story = { args: { id: "C-51", label: "項目を指さないコメント", body: "全体を読み返して気になった点をまとめます。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい" } };

/** 改行の無い長文。折り返した後の見た目の行で 5 行を超えるので畳まれ、「続きを読む」を出す */
export const FoldedWrap: Story = { args: { id: "C-52", label: "A-14 へのコメント", body: "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、冒頭で「何と何を比べているのか」を一文で言い切ってから、選んだ時点の決め方、足した・変えた・消した項目の印の読み方、本文の差分の並べ方の切り替え、図の差分の見方の順に並べると読みやすい。今は印の説明が先に来ていて、何を比べているかが分かる前に細かい話に入っている。" } };

/** 開いた本文。全文を出し、上向きの印と「折りたたむ」を出す（`aria-expanded="true"`） */
export const Opened: Story = { args: { id: "C-51", label: "項目を指さないコメント", open: true, body: "全体を読み返して気になった点をまとめます。\n1. 概要のタイルの並びが毎回変わる\n2. 検討事項の表で列の幅が狭い\n3. タスクのボードで完了の列が長い\n4. 資料のカードの日付が読みにくい\n5. ネットワークの玉の色が近い\n6. 詳細パネルの本文の図が小さい\n7. 変更履歴の時点の並びが分かりにくい" } };

/** 台の幅 390px。幅が狭くても見た目の 5 行で畳み、「続きを読む」の文字をボタンの中で折り返さない */
export const Narrow: Story = { args: { id: "C-52", label: "A-14 へのコメント", body: "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、冒頭で「何と何を比べているのか」を一文で言い切ってから、選んだ時点の決め方、足した・変えた・消した項目の印の読み方、本文の差分の並べ方の切り替え、図の差分の見方の順に並べると読みやすい。" } };

/** `titles` を渡した本文。記録にある T-14 は項目を開くボタン、対応に無い D-99 は文字のまま出す */
export const IdLink: Story = { args: { id: "C-55", label: "TH-1 への返信", body: "T-14 は今週中に書いてほしい。\nD-99 は重なっているので消してよい", titles: lookup({"T-14": "移し替えの失敗の扱いを書く"}) } };
