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

export const StyleIsolated: Story = { args: {"source": "<style>*{color:red !important}p{margin:40px !important}</style><p>枠の中</p>"} };

export const Loading: Story = { args: {} };

export const WithScripts: Story = { args: {"source": "<h1>見出し</h1><script>document.title=\"x\"</script><img src=x onerror=\"document.title='x'\"><button onclick=\"document.title='x'\">押す</button>"} };

export const CodeBlock: Story = { args: {"selectable": false, "label": "html のコードブロック"} };

export const DiffMarks: Story = { args: {"marks": {"added": [5], "changed": [3]}, "source": "<p data-line=\"1\" data-line-end=\"1\">一</p>\n<p data-line=\"2\" data-line-end=\"2\">二</p>\n<p data-line=\"3\" data-line-end=\"3\">三</p>\n<p data-line=\"4\" data-line-end=\"4\">四</p>\n<p data-line=\"5\" data-line-end=\"5\">五</p>"} };

export const Narrow: Story = { args: {} };

export const ViewportRelative: Story = { args: {"source": "<style>html,body{height:100%}body{min-height:100vh}</style><p>本文</p>"} };

export const Links: Story = { args: {"source": "<a href=\"https://example.com/\">外</a><a href=\"mailto:a@example.com\">メール</a><a href=\"javascript:void(0)\">実行</a>"} };

export const AnchorLinks: Story = { args: {"source": "<a href=\"#usage\">使い方</a><a href=\"#none\">無い</a><div style=\"height:1200px\"></div><h2 id=\"usage\">使い方</h2>"} };
