// 図の拡大の画面のストーリー。窓の端から余白を空けて重ね、外側を押すと閉じる
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { DiagramViewer } from "@/features/detail/diagram-viewer/diagram-viewer";

/** 横長の図（mermaid が描いた SVG の代わりに、同じ viewBox を持つ SVG） */
const WIDE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 240" role="img" aria-label="記録の流れ"><title>記録の流れ</title>
<rect x="10" y="90" width="140" height="60" rx="6" fill="none" stroke="currentColor"/><text x="80" y="125" text-anchor="middle" font-size="16" fill="currentColor">話し合い</text>
<path d="M150 120h90" stroke="currentColor" marker-end="url(#a)"/>
<rect x="250" y="90" width="140" height="60" rx="6" fill="none" stroke="currentColor"/><text x="320" y="125" text-anchor="middle" font-size="16" fill="currentColor">記録</text>
<path d="M390 120h90" stroke="currentColor" marker-end="url(#a)"/>
<rect x="490" y="90" width="140" height="60" rx="6" fill="none" stroke="currentColor"/><text x="560" y="125" text-anchor="middle" font-size="16" fill="currentColor">プレビュー</text>
<defs><marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0l10 5-10 5z" fill="currentColor"/></marker></defs></svg>`;

const meta = {
  title: "Features/Detail/DiagramViewerScreen",
  component: DiagramViewer,
  parameters: { layout: "fullscreen" },
  args: { svg: WIDE_SVG, onClose: fn() },
} satisfies Meta<typeof DiagramViewer>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 窓の端から 24px の余白を空けて重ね、図を余白 16px で収める。「本文へ戻る」のボタンを配置せず、外側の幕を押すか Esc で閉じる */
export const Default: Story = {};

/** 記法を持つ図。上部のバーの右端に Raw を配置する */
export const WithSource: Story = { args: { source: "flowchart LR\n  話し合い --> 記録 --> プレビュー" } };

/** 幅 390px。余白は同じ 24px で、外側の幕を押せる */
export const Narrow: Story = {
  parameters: { viewport: { options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } } } },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
