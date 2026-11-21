// タスクの画面のストーリー。絞り込みのドロワーでプリセットを選択し、タグの条件（簡易・詳細）に入れる前後を並べる
import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";
import { expect, userEvent, within } from "storybook/test";

import { TasksScreen } from "@/features/tasks/tasks/tasks-screen";
import { worker } from "@/testing/msw/browser";
import { STORY_RECORDS } from "@/testing/msw/story-records";
import { InStoryRouter } from "@/testing/story-router";

const WithDrawer = () => <TasksScreen drawerOpen onCloseDrawer={() => undefined} />;
const WithoutDrawer = () => <TasksScreen drawerOpen={false} onCloseDrawer={() => undefined} />;

const respond = () => worker.use(http.get("*/api/records", () => HttpResponse.json(STORY_RECORDS)));

/** 除外を含む「画面の設計」の式 */
const EXPR = STORY_RECORDS.settings.presets[0]?.filter;

const NARROW = {
  parameters: { viewport: { options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } } } },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

const meta = {
  title: "Features/Tasks/TasksScreen",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  beforeEach: respond,
  args: { path: "/?tab=tasks", screen: WithDrawer },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** ドロワーの先頭にプリセットを件数つきで並べる。該当が 0 件の「通知」は破線の枠線で出す */
export const DrawerPresets: Story = {};

/** ドロワーで「廃止する画面」を選択した。簡易で表せる式のため、タグのチェックに「画面」「廃止」が入り、組み合わせが「すべて含む」になる */
export const DrawerPresetApplied: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /廃止する画面/ }));
    await expect(await canvas.findByRole("button", { name: /廃止する画面/, pressed: true })).toBeInTheDocument();
  },
};

/** ドロワーで除外を含む「画面の設計」を選択した。タグの条件が詳細の表示になり、続けて編集できる */
export const DrawerExprPresetApplied: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /画面の設計/ }));
    await expect(await canvas.findByRole("button", { name: /画面の設計/, pressed: true })).toBeInTheDocument();
  },
};

/** 「詳細」に切り替え、プリセットを使用せずにタグの条件を組む */
export const DrawerExprWriting: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("radio", { name: "詳細" }));
  },
};

/** 簡易で表せるプリセットを選択してドロワーを閉じた後の一覧。条件のチップは今のタグの絞り込みと同じ表示になる */
export const AfterPresetApplied: Story = { args: { path: `/?tab=tasks&f.tags=${encodeURIComponent("画面|廃止")}`, screen: WithoutDrawer } };

/** 除外を含む詳細の条件で絞った後の一覧。条件のチップに条件を文で出す */
export const AfterExprPresetApplied: Story = { args: { path: `/?tab=tasks&tx=${encodeURIComponent(JSON.stringify(EXPR))}`, screen: WithoutDrawer } };

/** 幅 390px のドロワー（除外を含む詳細の条件を選択した） */
export const DrawerExprNarrow: Story = { ...NARROW, args: { path: `/?tab=tasks&tx=${encodeURIComponent(JSON.stringify(EXPR))}` } };
