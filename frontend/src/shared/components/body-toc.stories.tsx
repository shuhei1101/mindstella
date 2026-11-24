// 本文の目次のストーリー（部品設計『本文の目次.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { BodyToc } from "@/shared/components/body-toc";

const meta = {
  title: "Shared/BodyToc",
  component: BodyToc,
  args: {
    entries: [
      { level: 1, text: "目的", slug: "目的" },
      { level: 2, text: "保存先", slug: "保存先" },
      { level: 3, text: "決め方", slug: "決め方" },
      { level: 2, text: "残る論点", slug: "残る論点" },
    ],
    onHeading: fn(),
  },
  decorators: [
    (Story) => (
      <div className="flex justify-end p-2">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof BodyToc>;

export default meta;
type Story = StoryObj<typeof meta>;

/** 閉じた目次のボタン */
export const Default: Story = {};

/** 開いた目次。下の階層の見出しを字下げする */
export const Open: Story = { args: { defaultOpen: true } };

/** 長い見出しを 1 行で省略し、ポインターを乗せると全文を出す */
export const LongHeading: Story = {
  args: {
    defaultOpen: true,
    entries: [
      { level: 2, text: "記録をワークスペースの直下とホームの設定フォルダのどちらに置くかを比べた結果と、それぞれの持ち出しやすさ", slug: "long" },
      { level: 3, text: "決め方", slug: "決め方" },
    ],
  },
};
