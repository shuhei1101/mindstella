// 選んだ検討事項のバーのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { BulkDecideBar } from "@/shared/components/bulk-decide-bar";

const meta = {
  title: "Shared/BulkDecideBar",
  component: BulkDecideBar,
  args: { count: 2, onDecide: fn(), onClear: fn() },
} satisfies Meta<typeof BulkDecideBar>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 検討事項を 2 件選んでいる。「推奨の案で決定」と「選択を解除」を出す */
export const Default: Story = {};

/** 決定している間。どちらのボタンも押せない */
export const Pending: Story = { args: { pending: true } };

/** 決定できない検討事項があり、どの検討事項も決定しなかった。選択は残る */
export const Failed: Story = {
  args: { failures: [{ id: "D-2", reason: "未決定ではありません（決定済み）" }, { id: "D-5", reason: "推奨の案がありません" }] },
};

/** 何も選んでいない。何も出さない */
export const Empty: Story = { args: { count: 0 } };
