// スレッドの画面のストーリー。AI の通知のスレッドに並んだ検討事項から選んで決める
import type { Meta, StoryObj } from "@storybook/react-vite";
import { delay, http, HttpResponse } from "msw";
import { expect, userEvent, within } from "storybook/test";

import { useCommentData } from "@/features/comments/shared/use-comment-data";
import { ThreadView } from "@/features/comments/thread/thread-view";
import { worker } from "@/testing/msw/browser";
import { STORY_RECORDS, STORY_THREADS } from "@/testing/msw/story-records";
import { InStoryRouter } from "@/testing/story-router";

const Screen = () => {
  const data = useCommentData();
  return (
    <div className="flex h-screen w-full max-w-md flex-col">
      <ThreadView id="TH-1" data={data} onBack={() => undefined} onOpenItem={() => undefined} onOpenChangeSet={() => undefined} />
    </div>
  );
};

const respond = (decide: Parameters<typeof http.post>[1]) => () =>
  worker.use(
    http.get("*/api/records", () => HttpResponse.json(STORY_RECORDS)),
    http.get("*/api/threads", () => HttpResponse.json(STORY_THREADS)),
    http.post("*/api/decisions/decide", decide),
  );

const meta = {
  title: "Features/Comments/ThreadView",
  component: InStoryRouter,
  parameters: { layout: "fullscreen" },
  args: { path: "/?panel=comments&thread=TH-1", screen: Screen },
} satisfies Meta<typeof InStoryRouter>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 通知の書き込みの下に、並べた検討事項の一覧を出す。AI が決めた D-1 は選べない */
export const NoticeDecisions: Story = { beforeEach: respond(() => HttpResponse.json({ decided: [] })) };

/** D-2・D-3 を選んだ。一覧の下に選んだ件数と「推奨の案で決定」を出す */
export const NoticeDecisionsPicked: Story = {
  beforeEach: respond(async () => {
    await delay("infinite");
    return HttpResponse.json({ decided: [] });
  }),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("checkbox", { name: "D-2 を選ぶ" }));
    await userEvent.click(canvas.getByRole("checkbox", { name: "D-3 を選ぶ" }));
    await expect(canvas.getByRole("region", { name: "選んだ検討事項" })).toHaveTextContent("2 件を選択");
  },
};
