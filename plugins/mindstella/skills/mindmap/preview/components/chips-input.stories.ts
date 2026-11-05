// チップの入力のストーリー（部品設計『チップの入力』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** チップの入力の引数（台の幅を足す） */
type ChipsInputArgs = MindmapPreview.ChipsInputProps & { width?: number };

const meta = {
  title: "Preview/ChipsInput",
  render: ({ width, ...props }) => {
    const stage = document.createElement("div");
    stage.style.cssText = `width:${width ?? 480}px;max-width:100%`;
    stage.append(MindmapPreview.chipsInput(props));
    return stage;
  },
  args: {
    controlId: "pe-chips",
    name: "タグ",
    hint: "タグを入れる",
    values: [],
    suggestions: null,
    monospace: false,
    mainToggle: false,
    disabled: false,
    onChange: fn(),
  },
} satisfies Meta<ChipsInputArgs>;

export default meta;

type Story = StoryObj<ChipsInputArgs>;

/** 参照の ID を等幅の文字のチップで並べる。主題のトグルを持たない */
export const Default: Story = { args: { name: "関係", hint: "ID を入れる", values: ["D-1", "T-3"], monospace: true } };

/** 項目のタグ。主題のタグ 1 つ（トグルが押した状態の二重丸）と、主題でないタグ 2 つ（押していない状態の輪） */
export const MainToggle: Story = {
  args: {
    values: [{ name: "画面", main: true }, { name: "記録の形" }, { name: "通知" }],
    mainToggle: true,
    suggestions: ["画面", "記録の形", "通知", "タスク"],
  },
};

/** 削除を溜めた項目のタグ。入力欄・外すボタン・主題のトグルを押せない */
export const MainToggleDisabled: Story = {
  args: { values: [{ name: "画面", main: true }, { name: "記録の形" }], mainToggle: true, disabled: true },
};

/** 幅 320px で長い名前の主題のタグを並べる。収まらないチップは次の行へ回し、トグルは名前と同じ行に残す */
export const MainToggleLongNarrow: Story = {
  args: {
    values: [{ name: "すべての画面の絞り込みとドロワーの並び", main: true }, { name: "ゴールと設定" }],
    mainToggle: true,
    width: 320,
  },
};
