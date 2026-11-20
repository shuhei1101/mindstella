// 確認済みの切り替えのストーリー（未確認・確認済み・書き込み中、詳細の見出しでの並び）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { ConfirmedToggle } from "@/shared/components/confirmed-toggle";
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";

const meta = {
  title: "Shared/ConfirmedToggle",
  component: ConfirmedToggle,
  args: { confirmed: false, saving: false, onToggle: () => undefined },
} satisfies Meta<typeof ConfirmedToggle>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 未確認。空のチェックと「確認済みにする」 */
export const Unconfirmed: Story = {};

/** 確認済み。チェックと「確認済み」を完了の色で出し、押すと解除する */
export const Confirmed: Story = { args: { confirmed: true } };

/** 書き込みの応答を待っている間。押せない */
export const Saving: Story = { args: { confirmed: false, saving: true } };

/** 詳細の見出しでの並び。種類と ID の後、編集するの前に置く。幅 640px 未満ではアイコンだけになる */
export const InDetailHeader: Story = {
  args: { confirmed: false },
  render: (args) => (
    <div className="flex items-center gap-1 border-b border-border-soft p-2">
      <span className="text-xs text-muted-foreground">
        <span className="max-sm:hidden">検討事項 </span>
        <span className="font-mono">D-1</span>
      </span>
      <span className="min-w-0 flex-1" />
      <ConfirmedToggle {...args} />
      <Button variant="outline" title="編集する">
        <Icon name="edit" />
        <span>編集する</span>
      </Button>
      <Button variant="ghost" size="icon" aria-label="D-1 のコメントの一覧を開く" title="この項目のコメントの一覧">
        <Icon name="comment" />
      </Button>
      <Button variant="ghost" size="icon" aria-label="全画面表示" title="全画面表示">
        <Icon name="expand" />
      </Button>
      <Button variant="ghost" size="icon" aria-label="詳細を閉じる">
        <Icon name="x" />
      </Button>
    </div>
  ),
};
