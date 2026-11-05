// HTMLの本文の差分のストーリー（部品設計『HTMLの本文の差分.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { HtmlBodyDiff } from "@/shared/components/html-body-diff";

const meta = {
  title: "Shared/HtmlBodyDiff",
  component: HtmlBodyDiff,
  args: { before: "<p>前の段落</p>\n<p>同じ段落</p>\n", after: "<p>今の段落</p>\n<p>同じ段落</p>\n", marked: '<p data-line="1" data-line-end="1">今の段落</p>\n<p data-line="2" data-line-end="2">同じ段落</p>\n' },
} satisfies Meta<typeof HtmlBodyDiff>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Rendered: Story = { args: {} };

export const RawDiff: Story = { args: {} };

export const RemovedOnly: Story = { args: {} };

export const FromMarkdown: Story = { args: {"beforeFormat": "md"} };

export const SideRendered: Story = { args: {"layout": "side"} };

export const SideRaw: Story = { args: {"layout": "side"} };

export const SideFromMarkdown: Story = { args: {"layout": "side", "beforeFormat": "md"} };

export const RangeRaw: Story = { args: {"initial": "raw", "heading": "埋め込んだ HTML"} };

export const RangeBefore: Story = { args: {"initial": "raw", "heading": "埋め込んだ HTML"} };

export const RangeAfter: Story = { args: {"initial": "raw", "heading": "埋め込んだ HTML"} };
