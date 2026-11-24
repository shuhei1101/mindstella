// プリセットの保存のストーリー（部品設計『プリセットの保存.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { PresetSave, type PresetSaveResult } from "@/shared/components/preset-save";

const meta = {
  title: "Shared/PresetSave",
  component: PresetSave,
  args: { hasTagCondition: true, hasOtherConditions: false, onSave: fn((): Promise<PresetSaveResult> => Promise.resolve({ error: null })) },
  decorators: [
    (Story) => (
      <div className="w-full max-w-96 p-2">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof PresetSave>;

export default meta;
type Story = StoryObj<typeof meta>;

/** タグの条件があり、保存の操作を押せる */
export const Default: Story = {};

/** タグの条件が無く、保存の操作を押せない理由を出す */
export const NoTagCondition: Story = { args: { hasTagCondition: false } };

/** 名前の入力を開いた */
export const Open: Story = { args: { defaultOpen: true, defaultName: "廃止する画面" } };

/** タグの条件のほかに状態などの条件があり、タグの条件だけを保存する旨を出す */
export const WithOtherConditions: Story = { args: { defaultOpen: true, defaultName: "廃止する画面", hasOtherConditions: true } };

/** 名前が既にあるプリセットと重なった */
export const NameTaken: Story = {
  args: {
    defaultOpen: true,
    defaultName: "画面の設計",
    defaultError: "同じ名前のプリセット「画面の設計」が既にあります。別の名前を入れてください。",
    onSave: fn((): Promise<PresetSaveResult> => Promise.resolve({ error: "同じ名前のプリセット「画面の設計」が既にあります。別の名前を入れてください。" })),
  },
};

/** 最大の長さ（40 文字）の名前 */
export const LongName: Story = { args: { defaultOpen: true, defaultName: "画面の設計の見直しで使用する廃止予定の画面と部品をまとめて開くためのプリセット" } };
