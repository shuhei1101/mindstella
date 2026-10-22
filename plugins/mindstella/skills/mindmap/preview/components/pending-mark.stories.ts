// 保存待ちの印のストーリー（部品設計『保存待ちの印』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/PendingMark",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.pendingEditMark(args));
    return stage;
  },
  args: { kind: "pending" },
} satisfies Meta<MindmapPreview.PendingEditMarkProps>;

export default meta;

type Story = StoryObj<MindmapPreview.PendingEditMarkProps>;

/** 書き換え・追加の編集。印の色の破線の枠、重ねた紙の印と「保存待ち」 */
export const Pending: Story = { args: { kind: "pending" } };

/** 削除の編集。文字色の破線の枠、ゴミ箱の印と「保存で削除」 */
export const Remove: Story = { args: { kind: "remove" } };

/** 保存で書き込めなかった編集。失敗の赤の実線の枠、警告の印と「書き込めない」 */
export const Blocked: Story = { args: { kind: "blocked" } };

/** 印だけの書き換え・追加。幅 20px・高さ 18px の破線の枠に重ねた紙の印だけ */
export const PendingCompact: Story = { args: { kind: "pending", compact: true } };

/** 印だけの削除 */
export const RemoveCompact: Story = { args: { kind: "remove", compact: true } };

/** 印だけの書き込めない編集 */
export const BlockedCompact: Story = { args: { kind: "blocked", compact: true } };

/** ダークで 3 種類を並べる。印の色・文字色・失敗の赤はダークのトークンで読める濃さにする */
export const Dark: Story = {
  render: () => {
    document.documentElement.dataset["theme"] = "dark";
    const stage = document.createElement("div");
    stage.style.cssText = "display:flex;gap:12px;align-items:center;";
    for (const kind of ["pending", "remove", "blocked"] as const) {
      stage.append(MindmapPreview.pendingEditMark({ kind }));
    }
    return stage;
  },
};
