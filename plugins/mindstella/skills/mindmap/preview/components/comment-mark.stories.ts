// コメントの印のストーリー（部品設計『コメントの印』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

const meta = {
  title: "Preview/CommentMark",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.commentMark(args));
    return stage;
  },
  args: { count: 1 },
} satisfies Meta<MindmapPreview.CommentMarkProps>;

export default meta;

type Story = StoryObj<MindmapPreview.CommentMarkProps>;

/** 1 件。吹き出しの線と「1」 */
export const One: Story = { args: { count: 1 } };

/** 2 桁。吹き出しの線と「12」 */
export const TwoDigits: Story = { args: { count: 12 } };

/** 100 件以上。画面には「99+」、読み上げは「コメント 128 件」 */
export const Overflow: Story = { args: { count: 128 } };
