// 検討事項の画面のストーリー。記録は MSW が返却し、誰が決めたかは仮の値（利用者・AI）で持つ
import type { Meta, StoryObj } from "@storybook/react-vite";
import { delay, http, HttpResponse } from "msw";
import { expect, userEvent, within } from "storybook/test";

import { DecisionsScreen } from "@/features/decisions/decisions/decisions-screen";
import { worker } from "@/testing/msw/browser";
import { STORY_RECORDS } from "@/testing/msw/story-records";
import { InStoryRouter } from "@/testing/story-router";

const Screen = () => <DecisionsScreen drawerOpen={false} onCloseDrawer={() => undefined} />;

/** 記録を返し、まとめて決める API の応答を差し替える */
const respond = (decide: Parameters<typeof http.post>[1]) => () =>
  worker.use(
    http.get("*/api/records", () => HttpResponse.json(STORY_RECORDS)),
    http.post("*/api/decisions/decide", decide),
  );

/** 推奨の案を持つ未決定の D-2・D-3 を選ぶ */
const pickTwo = async (canvasElement: HTMLElement): Promise<void> => {
  const canvas = within(canvasElement);
  await userEvent.click(await canvas.findByRole("checkbox", { name: "D-2 を選ぶ" }));
  await userEvent.click(canvas.getByRole("checkbox", { name: "D-3 を選ぶ" }));
};

const meta = {
  title: "Features/Decisions/DecisionsScreen",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  args: { path: "/?tab=decisions", screen: Screen },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 未決定の検討事項に選ぶチェックボックスを出す。推奨の案を持たない D-4 は選べない。決定済みのカードに誰が決めたかを出す（既定の絞り込みは決定済みの列を除外する） */
export const Default: Story = { beforeEach: respond(() => HttpResponse.json({ decided: [] })) };

/** D-2・D-3 を選んだ。ボードの上に選んだ件数と「推奨の案で決定」を出す */
export const Picked: Story = {
  beforeEach: respond(() => HttpResponse.json({ decided: [] })),
  play: async ({ canvasElement }) => {
    await pickTwo(canvasElement);
    await expect(within(canvasElement).getByRole("region", { name: "選んだ検討事項" })).toHaveTextContent("2 件を選択");
  },
};

/** 決定している間。「決定しています」を読める濃さで出し、チェックボックスを押せなくする */
export const Pending: Story = {
  beforeEach: respond(async () => {
    await delay("infinite");
    return HttpResponse.json({ decided: [] });
  }),
  play: async ({ canvasElement }) => {
    await pickTwo(canvasElement);
    await userEvent.click(within(canvasElement).getByRole("button", { name: "推奨の案で決定" }));
  },
};

/** 決定できない検討事項を含む。どの検討事項も決定せず、理由を出して選択を残す */
export const Failed: Story = {
  beforeEach: respond(() =>
    HttpResponse.json(
      { type: "decision-not-decidable", title: "決定できない検討事項があります", status: 409, detail: "決定できない検討事項があります", failures: [{ id: "D-3", reason: "未決定ではありません（決定済み）" }] },
      { status: 409, headers: { "Content-Type": "application/problem+json" } },
    ),
  ),
  play: async ({ canvasElement }) => {
    await pickTwo(canvasElement);
    await userEvent.click(within(canvasElement).getByRole("button", { name: "推奨の案で決定" }));
    await expect(await within(canvasElement).findByRole("alert")).toHaveTextContent("D-3");
  },
};

/** 誰が決めたかの「AI が決定」で絞った表。D-1 だけが並ぶ */
export const DecidedByAi: Story = {
  beforeEach: respond(() => HttpResponse.json({ decided: [] })),
  args: { path: "/?tab=decisions&view=table&f.decided_by=AI%20%E3%81%8C%E6%B1%BA%E5%AE%9A" },
};
