// タグの式の編集の状態ごとのストーリー
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { TagExprEditor, type TagChoice } from "@/shared/components/tag-expr-editor";
import type { PresetFilter } from "@/shared/core/presets";

const TAGS: TagChoice[] = [
  { value: "画面", count: 3 },
  { value: "廃止", count: 1 },
  { value: "保存", count: 1 },
  { value: "通知", count: 0 },
];

const Editable = ({ initial }: { initial: PresetFilter }) => {
  const [expr, setExpr] = useState(initial);
  return (
    <div className="w-96 max-w-full">
      <TagExprEditor expr={expr} tags={TAGS} onChange={setExpr} />
    </div>
  );
};

const meta = {
  title: "Shared/TagExprEditor",
  component: Editable,
} satisfies Meta<typeof Editable>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 条件が 1 つで、タグを選んでいない */
export const Empty: Story = { args: { initial: { and: [{ field: "tags", op: "eq", values: [] }] } } };

/** 「画面」を含み「廃止」を含まない */
export const IncludeExclude: Story = { args: { initial: { and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] } } };

/** グループを入れ子にした式（「保存」を含む、または「画面」と「廃止」を両方含む） */
export const Nested: Story = { args: { initial: { or: [{ field: "tags", op: "eq", values: ["保存"] }, { and: [{ field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" }] }] } } };

const Many = () => {
  const tags: TagChoice[] = Array.from({ length: 50 }, (_, index) => ({ value: `タグ${String(index + 1)}`, count: index % 7 }));
  const [expr, setExpr] = useState<PresetFilter>({ and: [{ field: "tags", op: "eq", values: ["タグ3", "タグ12"], match: "all" }, { field: "tags", op: "ne", values: ["タグ40"] }] });
  return (
    <div className="w-96 max-w-full">
      <TagExprEditor expr={expr} tags={tags} onChange={setExpr} />
    </div>
  );
};

/** タグが 50 件あっても、選択したタグだけをチップで出し、残りは入力欄の候補から追加する */
export const ManyTags: Story = { args: { initial: { and: [] } }, render: () => <Many /> };
