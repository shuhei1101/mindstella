// 絞り込みのプリセットの並びのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { PresetBar } from "@/shared/components/preset-bar";

const PRESETS = [
  { name: "画面の設計", description: "タグ「画面」を持ち「廃止」を持たない項目", count: 12 },
  { name: "保存の仕組み", description: "タグ「保存」を持つ項目", count: 5 },
  { name: "通知", description: "タグ「通知」を持つ項目", count: 0 },
];

const meta = {
  title: "Shared/PresetBar",
  component: PresetBar,
  args: { presets: PRESETS, selected: null, onSelect: fn() },
} satisfies Meta<typeof PresetBar>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 何も選んでいない。該当する件数が 0 の「通知」は破線の枠線と「0 件」で示し、押せるまま残す */
export const Default: Story = {};

/** 「画面の設計」を選んでいる。押された見た目にし、もう一度押すと `onSelect(null)` で解除する */
export const Selected: Story = { args: { selected: "画面の設計" } };

/** 該当する件数が 0 のプリセットを選んでいる */
export const SelectedEmpty: Story = { args: { selected: "通知" } };

/** 幅 390px。プリセットが多いと折り返す */
export const Narrow: Story = {
  args: { presets: [...PRESETS, { name: "ログインの方式", count: 3 }, { name: "エクスポートの形式", count: 8 }, { name: "検索", count: 2 }] },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** プリセットが無い。何も出さない */
export const Empty: Story = { args: { presets: [] } };
