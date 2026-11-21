// タスクの画面のストーリー。プリセットの並びの置き場所の案 A（表示形式の切り替えの下）・B（同じ行の右）を並べる
import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";

import { TasksScreen } from "@/features/tasks/tasks/tasks-screen";
import { worker } from "@/testing/msw/browser";
import { STORY_RECORDS } from "@/testing/msw/story-records";
import { InStoryRouter } from "@/testing/story-router";

const Below = () => <TasksScreen drawerOpen={false} onCloseDrawer={() => undefined} presetPlacement="below" />;
const Inline = () => <TasksScreen drawerOpen={false} onCloseDrawer={() => undefined} presetPlacement="inline" />;

const respond = () => worker.use(http.get("*/api/records", () => HttpResponse.json(STORY_RECORDS)));

/** 「画面の設計」を選んだ URL */
const SELECTED = `/?tab=tasks&preset=${encodeURIComponent("画面の設計")}`;

const meta = {
  title: "Features/Tasks/TasksScreen",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  beforeEach: respond,
  args: { path: "/?tab=tasks", screen: Below },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 案 A: プリセットの並びを表示形式の切り替えの下に配置する。何も選んでいない */
export const PresetBelow: Story = {};

/** 案 A で「画面の設計」を選んだ。T-1 だけが並び、条件のチップの先頭にプリセットのチップを出す */
export const PresetBelowSelected: Story = { args: { path: SELECTED } };

/** 案 B: プリセットの並びを表示形式の切り替えと同じ行の右に配置し、「画面の設計」を選んだ */
export const PresetInlineSelected: Story = { args: { path: SELECTED, screen: Inline } };

/** 案 A で、該当する件数が 0 の「通知」を選んだ。該当なしの表示を出す */
export const PresetEmptySelected: Story = { args: { path: `/?tab=tasks&preset=${encodeURIComponent("通知")}` } };

/** 案 A の幅 390px。プリセットの並びを折り返す */
export const PresetBelowNarrow: Story = {
  args: { path: SELECTED },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 案 B の幅 390px */
export const PresetInlineNarrow: Story = {
  args: { path: SELECTED, screen: Inline },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
