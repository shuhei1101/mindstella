// お気に入りの星のストーリー（部品設計『お気に入りの星.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { FavoriteToggle } from "@/shared/components/favorite-toggle";

const meta = {
  title: "Shared/FavoriteToggle",
  component: FavoriteToggle,
  args: { title: "画面の配色の比較", on: false, onToggle: fn() },
} satisfies Meta<typeof FavoriteToggle>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 登録していない。線だけの星を薄い色で出し、`aria-pressed` は false */
export const Off: Story = {};

/** 登録している。塗った星を印の色で出し、`aria-pressed` は true */
export const On: Story = { args: { on: true } };

/** キーボードで移った。フォーカスの輪を出し、Enter で `onToggle` を呼ぶ */
export const Focused: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "画面の配色の比較をお気に入りに登録" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(args.onToggle).toHaveBeenCalledOnce();
  },
};
