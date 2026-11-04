// 概要の画面のストーリー。記録・レビュー中のコメント・保存待ちの編集・スレッドは MSW の handler（testing/msw/handlers.ts）が返す
import type { Meta, StoryObj } from "@storybook/react-vite";

import { OverviewScreen } from "@/features/overview/overview/overview-screen";

const meta = {
  title: "Features/Overview/OverviewScreen",
  component: OverviewScreen,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof OverviewScreen>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 記録でトップバーと 6 つのタイルを描く */
export const Default: Story = {};
