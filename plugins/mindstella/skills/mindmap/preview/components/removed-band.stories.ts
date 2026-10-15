// 消した項目の帯のストーリー（部品設計『消した項目の帯』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/RemovedBand",
  render: (args) => {
    const stage = document.createElement("div");
    const band = MindmapPreview.removedBand(args);
    if (band !== null) stage.append(band);
    return stage;
  },
  args: { items: [{ id: "N-6", title: "ゴールを後から変える・足す・無しで始める" }] },
} satisfies Meta<MindmapPreview.RemovedBandProps>;

export default meta;

type Story = StoryObj<MindmapPreview.RemovedBandProps>;

/** 1 件。見出し「消した項目」と件数 1 の右に、消した印・ID・タイトルを 1 つ並べる */
export const One: Story = {};

/** 3 件で長いタイトルを含む。項目を横に並べて折り返し、タイトルは途中で切らずに折り返す */
export const ManyLongTitles: Story = {
  args: {
    items: [
      { id: "D-53", title: "差分の印の色を、項目の種類ごとに変えるか" },
      { id: "D-54", title: "変更履歴のモーダルを時系列の一覧にして、未読の印を付け、読んだ時点から後の書き換えだけを数えるか" },
      { id: "D-55", title: "印の凡例を置くか" },
    ],
  },
};

/** 幅 390px。見出しの下に項目を折り返す */
export const Narrow: Story = {
  args: {
    items: [
      { id: "N-6", title: "ゴールを後から変える・足す・無しで始める" },
      { id: "N-7", title: "読み返したい点をメモする" },
    ],
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
