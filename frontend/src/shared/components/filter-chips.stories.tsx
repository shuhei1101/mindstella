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

/** 簡易で表せないタグの条件で絞った。先頭に式を文にしたチップと、状態のチップを並べる */
export const TagExpr: Story = {
  args: { filters: { status: ["未着手"] }, tagExprText: "「画面」を含む かつ 「廃止」を含まない", onClearTagExpr: fn() },
};

/** 「お気に入りだけを表示する」をオンにした。先頭に「お気に入りだけ」のチップを出し、× と「すべて解除」で解除する */
export const FavoritesOnly: Story = { args: { onClearFavoritesOnly: fn() } };

/** 「お気に入りだけを表示する」と状態の条件を重ねた。「お気に入りだけ」を先頭に、状態のチップを後ろに並べる */
export const FavoritesOnlyWithStatus: Story = { args: { filters: { status: ["未着手"] }, onClearFavoritesOnly: fn() } };
