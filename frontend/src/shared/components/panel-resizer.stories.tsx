// 幅の区切りのストーリー（部品設計『幅の区切り.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState, type ComponentProps } from "react";
import { fn } from "storybook/test";

import { PanelResizer } from "@/shared/components/panel-resizer";

/** 区切りを端に持つパネルを描き、変えた幅を自分の状態に持つ台 */
const PanelStage = (props: ComponentProps<typeof PanelResizer>) => {
  const [width, setWidth] = useState(props.width);
  return (
    <div className="relative h-80 border border-border bg-card" style={{ width, maxWidth: "100%", marginLeft: props.side === "left" ? "auto" : undefined }}>
      <p className="m-0 p-3 text-small text-muted-foreground">{`${props.label}: ${width}px`}</p>
      <PanelResizer
        {...props}
        width={width}
        onChange={(next) => {
          props.onChange(next);
          setWidth(next);
        }}
      />
    </div>
  );
};

const meta = {
  title: "Shared/PanelResizer",
  component: PanelResizer,
  render: (args) => <PanelStage {...args} />,
  args: { onChange: fn(), onCommit: fn(), step: 16 },
  // 区切りは 900px 以下では描かないため、区切りを描く幅で開く
  parameters: {
    viewport: {
      options: { wide: { name: "幅 1280px", styles: { width: "1280px", height: "900px" } } },
    },
  },
  globals: { viewport: { value: "wide", isRotated: false } },
} satisfies Meta<typeof PanelResizer>;

export default meta;

type Story = StoryObj<typeof meta>;

/** パネルの左端の区切り（詳細パネル）。左へドラッグすると広がる */
export const Left: Story = { args: { side: "left", width: 640, min: 480, max: 1040, label: "詳細パネルの幅" } };

/** パネルの右端の区切り（コメントの一覧）。右へドラッグすると広がる */
export const Right: Story = { args: { side: "right", width: 384, min: 320, max: 800, label: "コメントの一覧の幅" } };

/** 下限の幅。狭める向きにドラッグ・キーを押しても下限のまま */
export const AtMin: Story = { args: { side: "right", width: 320, min: 320, max: 800, label: "コメントの一覧の幅" } };

/** 上限の幅。広げる向きにドラッグ・キーを押しても上限のまま */
export const AtMax: Story = { args: { side: "right", width: 800, min: 320, max: 800, label: "コメントの一覧の幅" } };

/** 指の端末（`pointer: coarse`）。区切りの幅を 44px にし、パネルの端の線を中央に挟む（確かめるときは、区切りを描く幅 901px 以上で pointer: coarse を模して開く） */
export const Touch: Story = { args: { side: "right", width: 384, min: 320, max: 800, label: "コメントの一覧の幅" } };
