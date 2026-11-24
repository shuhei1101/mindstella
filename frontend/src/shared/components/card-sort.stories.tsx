// カード・ボードの並べ替えのストーリー（既定・日時を初めて選んだ・もう一度選んだ）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { fn } from "storybook/test";

import { CardSort, INITIAL_CARD_SORT, type CardSortProps } from "@/shared/components/card-sort";

/** 押した結果を自分の状態に持つ台 */
const SortStage = (props: CardSortProps) => {
  const [value, setValue] = useState(props.value);
  return (
    <CardSort
      value={value}
      onChange={(next) => {
        props.onChange(next);
        setValue(next);
      }}
    />
  );
};

const meta = {
  title: "Shared/CardSort",
  component: CardSort,
  render: (args) => <SortStage {...args} />,
  args: { value: INITIAL_CARD_SORT.other, onChange: fn() },
} satisfies Meta<typeof CardSort>;

export default meta;

type Story = StoryObj<typeof meta>;

/** タスク・検討事項などを開いた直後（連番）。押すと、日時の項目は新しい順で選ばれる */
export const Default: Story = {};

/** 資料を開いた直後。更新日時の新しい順が選ばれ、向きを矢印で出す */
export const DocsInitial: Story = { args: { value: INITIAL_CARD_SORT.docs } };

/** 更新日時を初めて選んだ状態。新しい順 */
export const UpdatedDesc: Story = { args: { value: { key: "updated", dir: "desc" } } };

/** 作成日時をもう一度選んだ状態。古い順 */
export const CreatedAsc: Story = { args: { value: { key: "created", dir: "asc" } } };
