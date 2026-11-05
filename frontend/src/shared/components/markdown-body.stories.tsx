// Markdownの本文のストーリー（部品設計『Markdownの本文.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { MarkdownBody } from "@/shared/components/markdown-body";

const SAMPLE_MD = ["## 料金", "", "| ID | 名前 | 説明 |", "| --- | --- | --- |", "| A-1 | 無料 | 本文の表の行 |", "", "> [!NOTE]", "> 補足の文", "", "```python", "print(1)", "```"].join("\n");

const meta = {
  title: "Shared/MarkdownBody",
  component: MarkdownBody,
  args: { source: SAMPLE_MD },
} satisfies Meta<typeof MarkdownBody>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ColumnWidths: Story = { args: {} };

export const SmallTable: Story = { args: {} };

export const PinHover: Story = { args: {} };

export const Pinned: Story = { args: {} };

export const PinOff: Story = { args: {"display": {"pin": false, "head": true, "stripes": false, "fold": true}} };

export const HeadStuck: Story = { args: {} };

export const HeadOff: Story = { args: {"display": {"pin": true, "head": false, "stripes": false, "fold": true}} };

export const Stripes: Story = { args: {"display": {"pin": true, "head": true, "stripes": true, "fold": true}} };

export const StripesInDiff: Story = { args: {"display": {"pin": true, "head": true, "stripes": true, "fold": true}, "fold": false} };

export const Sections: Story = { args: {} };

export const Folded: Story = { args: {} };

export const FoldOff: Story = { args: {"display": {"pin": true, "head": true, "stripes": false, "fold": false}} };

export const CodeBlock: Story = { args: {} };

export const CodeCopied: Story = { args: {} };

export const Callouts: Story = { args: {} };

export const Narrow: Story = { args: {} };

export const InThreadPost: Story = { args: {"tables": false, "fold": false} };

export const EmbeddedHtml: Story = { args: {} };
