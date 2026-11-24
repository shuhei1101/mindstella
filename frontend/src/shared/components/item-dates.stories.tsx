// カードの作成日時・更新日時のストーリー（部品設計『項目の日時.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { ItemDates } from "@/shared/components/item-dates";

/** 去年の日時の見え方を確かめるときの今日 */
const FIXED_NOW = "2026-11-24T03:00:00+00:00";

const meta = {
  title: "Shared/ItemDates",
  component: ItemDates,
  args: { created: "2026-11-02T01:15:00+00:00", updated: "2026-11-20T09:40:00+00:00" },
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

/** 作成の後に更新した項目。「作成 11/02 10:15・更新 11/20 18:40」 */
export const Updated: Story = {};

/** 作成から更新していない項目。作成と更新に同じ日時を出す */
export const NotUpdated: Story = { args: { updated: "2026-11-02T01:15:00+00:00" } };

/** 幅 240px。「作成 {日時}」と「更新 {日時}」の組ごとに折り返し、組の中の文字は折り返さない */
export const Narrow: Story = {
  decorators: [
    (Story) => (
      <div className="w-60">
        <Story />
      </div>
    ),
  ],
};

/** 去年に作成して今年更新した項目。「作成 2025/12/28 09:00・更新 11/20 18:40」。今日を 2026-11-24 に固定する */
export const LastYear: Story = {
  args: { created: "2025-12-28T00:00:00+00:00" },
  beforeEach: () => {
    const RealDate = globalThis.Date;
    const fixed = RealDate.parse(FIXED_NOW);
    class FixedDate extends RealDate {
      constructor(...args: [] | [string | number | Date]) {
        if (args.length === 0) super(fixed);
        else super(args[0]);
      }

      static override now(): number {
        return fixed;
      }
    }
    globalThis.Date = FixedDate as DateConstructor;
    return () => {
      globalThis.Date = RealDate;
    };
  },
};
