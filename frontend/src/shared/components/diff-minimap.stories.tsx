// 差分のミニマップのストーリー（部品設計『差分のミニマップ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { DiffMinimap } from "@/shared/components/diff-minimap";

const SAMPLE_MINIMAP = (
  <div className="md">
    <ins className="df-blk">
      <p>足した段落</p>
    </ins>
    <del className="df-blk">
      <p>消した段落</p>
    </del>
  </div>
);

const meta = {
  title: "Shared/DiffMinimap",
  component: DiffMinimap,
  args: { shown: true, children: SAMPLE_MINIMAP },
} satisfies Meta<typeof DiffMinimap>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Kinds: Story = { args: {"shown": true} };

export const SingleMark: Story = { args: {"shown": true} };

export const NotScrollable: Story = { args: {"shown": true} };

export const ManyMarks: Story = { args: {"shown": true} };

export const Dragging: Story = { args: {"shown": true} };

export const NoMarks: Story = { args: {"shown": true} };

export const Hidden: Story = { args: {"shown": false} };

export const Narrow: Story = { args: {"shown": true} };

export const SideBySide: Story = { args: {"shown": true} };
