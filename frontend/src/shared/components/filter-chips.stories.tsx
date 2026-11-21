// 絞り込みの条件のチップのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { FilterChips } from "@/shared/components/filter-chips";

const meta = {
  title: "Shared/FilterChips",
  component: FilterChips,
  args: { filters: {}, labels: { status: "状態", tags: "タグ" }, onFilter: fn() },
} satisfies Meta<typeof FilterChips>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 状態とタグ 2 つで絞り、タグの組み合わせ方は既定の「すべて含む」。タグのチップは「タグ: {名前}」 */
export const TagMatchAll: Story = {
  args: { filters: { status: ["未着手"], tags: ["保存", "画面"] }, tagMatch: "all" },
};

/** タグの組み合わせ方を「どれかを含む」にした。タグのチップは「タグ（どれかを含む）: {名前}」 */
export const TagMatchAny: Story = {
  args: { filters: { status: ["未着手"], tags: ["保存", "画面"] }, tagMatch: "any" },
};

/** プリセット「画面の設計」と状態で絞っている。プリセットのチップを先頭に出し、× と「すべて解除」で `onClearPreset` を呼ぶ */
export const WithPreset: Story = {
  args: { filters: { status: ["未着手"] }, preset: "画面の設計", onClearPreset: fn() },
};

/** プリセットだけで絞っている */
export const PresetOnly: Story = {
  args: { filters: {}, preset: "画面の設計", onClearPreset: fn() },
};
