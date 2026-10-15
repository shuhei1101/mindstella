// 左右に並べた本文の差分のストーリー（部品設計『左右に並べた本文の差分』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** ストーリーの引数（語の差分を打ち切る時刻はストーリーが決める） */
type Args = Pick<MindmapPreview.SideBySideBodyDiffProps, "before" | "after" | "lined">;

/** 1 つ目の段落を消し、末尾に段落を足した前後 */
const PARAGRAPHS_BEFORE = "消した一つ目の段落です。\n\n変えていない二つ目の段落です。\n\n変えていない三つ目の段落です。\n";
const PARAGRAPHS_AFTER = "変えていない二つ目の段落です。\n\n変えていない三つ目の段落です。\n\n足した四つ目の段落です。\n";

/** 2 つ目の段落の語を書き換えた前後 */
const REWRITTEN_BEFORE = "一つ目の段落です。\n\n二つ目の段落は、来週に決めます。\n\n三つ目の段落です。\n";
const REWRITTEN_AFTER = "一つ目の段落です。\n\n二つ目の段落は、今週に決めます。\n\n三つ目の段落です。\n";

/** 箇条書きの項目と表の行を変えた前後 */
const TABLE_AND_LIST_BEFORE = [
  "- ボードとカードは、タイトルの左に印が付く",
  "- 表は、ID の列の右に印が付く",
  "- マップは、節の左上に印が付く",
  "",
  "| 印 | 意味 |",
  "| --- | --- |",
  "| + | 足した |",
  "| 〜 | 並べ替えた |",
  "",
].join("\n");
const TABLE_AND_LIST_AFTER = [
  "- ボードとカードは、タイトルの左に印が付く",
  "- 表は、ID の列の右に印が付く",
  "- マップは、節の右上に印が付く",
  "",
  "| 印 | 意味 |",
  "| --- | --- |",
  "| + | 足した |",
  "| 濃い面 | 変わった語 |",
  "",
].join("\n");

/** 図の記法を変えた前後 */
const DIAGRAM_BEFORE = "図の前の段落です。\n\n```mermaid\nflowchart LR\n  A[一覧] --> B[詳細]\n```\n";
const DIAGRAM_AFTER = "図の前の段落です。\n\n```mermaid\nflowchart LR\n  A[一覧] --> B[詳細パネル]\n  B --> C[全画面]\n```\n";

const meta = {
  title: "Preview/SideBySideBodyDiff",
  render: (args) => {
    const stage = document.createElement("div");
    stage.style.width = "min(960px, 100%)";
    const diff = MindmapPreview.sideBySideBodyDiff({ ...args, deadline: performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS });
    if (diff === null) return stage;
    stage.append(diff.root);
    diff.markWords();
    // 図は描いた後に、右の変えた図へ色・凡例・Raw の差分を付ける
    void MindmapPreview.renderDiagrams(diff.root).then(() => diff.decorate());
    return stage;
  },
  args: { before: PARAGRAPHS_BEFORE, after: PARAGRAPHS_AFTER, lined: true },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 既定。1 つ目の段落を消し、末尾に段落を足した。左に消した段落と向かいの縞の空き、右に足した段落と向かいの縞の空きを出し、変えていない段落は左右の同じ高さに印なしで並ぶ */
export const Paragraphs: Story = {};

/** 段落の中の語を書き換えた。左の消した段落と右の足した段落が向かい合い、変わった語だけに濃い面を付ける */
export const Rewritten: Story = { args: { before: REWRITTEN_BEFORE, after: REWRITTEN_AFTER } };

/** 表の行と箇条書きの項目を変えた。左に消した行・項目、右に足した行・項目の印を付け、消した箇条書きの項目は消した色の面と取り消し線で出す */
export const TableAndList: Story = { args: { before: TABLE_AND_LIST_BEFORE, after: TABLE_AND_LIST_AFTER } };

/** 図の記法を変えた。左は選んだ時点の図に消した色の破線の枠だけを付け、右は今の図に今と同じ色付けと凡例を付ける */
export const Diagram: Story = { args: { before: DIAGRAM_BEFORE, after: DIAGRAM_AFTER } };
