// 保存待ちの印のストーリー（部品設計『保存待ちの印.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { PendingMark } from "@/shared/components/pending-mark";

const meta = {
  title: "Shared/PendingMark",
  component: PendingMark,
  args: { kind: "pending" },
} satisfies Meta<typeof PendingMark>;

export default meta;

type Story = StoryObj<typeof meta>;

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
    return (
      <div className="flex items-center gap-3 bg-background p-3">
        <PendingMark kind="pending" />
        <PendingMark kind="remove" />
        <PendingMark kind="blocked" />
      </div>
    );
  },
};
