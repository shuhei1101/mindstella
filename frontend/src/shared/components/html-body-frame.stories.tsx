// HTMLの本文の枠のストーリー（部品設計『HTMLの本文の枠.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { HtmlBodyFrame } from "@/shared/components/html-body-frame";

const meta = {
  title: "Shared/HtmlBodyFrame",
  component: HtmlBodyFrame,
  args: { source: "<h1>見出し</h1><p>本文の段落</p>", selectable: true, label: "本文（HTML）" },
} satisfies Meta<typeof HtmlBodyFrame>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Rendered: Story = { args: {} };

export const StyleIsolated: Story = { args: {} };

export const Loading: Story = { args: {} };

export const WithScripts: Story = { args: {} };

export const CodeBlock: Story = { args: {"selectable": false, "label": "html のコードブロック"} };

export const DiffMarks: Story = { args: {"marks": {"added": [5], "changed": [3]}} };

export const Narrow: Story = { args: {} };

export const ViewportRelative: Story = { args: {} };

export const Links: Story = { args: {} };

export const AnchorLinks: Story = { args: {} };
