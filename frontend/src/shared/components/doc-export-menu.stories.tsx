// 資料のエクスポートのメニューのストーリー（部品設計『資料のエクスポートのメニュー.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { DocExportMenu } from "@/shared/components/doc-export-menu";

const meta = {
  title: "Shared/DocExportMenu",
  component: DocExportMenu,
  args: { onFormat: fn(), onConfirm: fn(), onBack: fn(), onRetry: fn() },
} satisfies Meta<typeof DocExportMenu>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Choose: Story = { args: {} };

export const Warn: Story = { args: {"view": "warn"} };

export const Busy: Story = { args: {"view": "busy"} };

export const Error: Story = { args: {"view": "error"} };

export const BackFromWarn: Story = { args: {"focus": "md"} };

export const Narrow: Story = { args: {} };

export const WarnNarrow: Story = { args: {"view": "warn"} };
