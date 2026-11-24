// カードの作成日時・更新日時のストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";

import { ItemDates } from "@/shared/components/item-dates";

const meta = {
  title: "Shared/ItemDates",
  component: ItemDates,
  args: { created: "2026-11-01T01:00:00+00:00", updated: "2026-11-20T01:00:00+00:00" },
  decorators: [
    (Story) => (
      <div className="w-64">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof ItemDates>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 作成日時と更新日時が違う項目 */
export const Updated: Story = {};

/** 作ってから書き換えていない項目。作成日時と更新日時が同じ */
export const NotUpdated: Story = { args: { updated: "2026-11-01T01:00:00+00:00" } };

/** カードの幅が狭いとき。作成日時と更新日時の 2 行に分かれ、日時の中では折り返さない */
export const Narrow: Story = {
  decorators: [
    (Story) => (
      <div className="w-36">
        <Story />
      </div>
    ),
  ],
};
