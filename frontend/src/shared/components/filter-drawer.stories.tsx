// 絞り込みのストーリー（部品設計『絞り込み.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { FilterDrawer, type FilterGroup } from "@/shared/components/filter-drawer";

/** タスク 8 件の、種類・状態・タグの条件（何も選んでいない） */
const taskGroups: FilterGroup[] = [
  {
    key: "kind",
    label: "種類",
    values: [
      { value: "作業", count: 4 },
      { value: "検証", count: 2 },
      { value: "調査", count: 2 },
    ],
  },
  {
    key: "status",
    label: "状態",
    mark: "status",
    values: [
      { value: "未着手", count: 3 },
      { value: "進行中", count: 2 },
      { value: "保留", count: 1 },
      { value: "完了", count: 2 },
      { value: "中止", count: 0 },
    ],
  },
  {
    key: "tags",
    label: "タグ",
    values: [
      { value: "プレビュー", count: 5 },
      { value: "サーバー", count: 3 },
    ],
  },
];

/** 検討事項 36 件の、状態とタグの条件（タグ「プレビュー」で絞った件数） */
const decisionGroups: FilterGroup[] = [
  {
    key: "status",
    label: "状態",
    mark: "status",
    values: [
      { value: "要見直し", count: 1 },
      { value: "未決定", count: 1 },
      { value: "未整理", count: 0 },
      { value: "保留", count: 1 },
      { value: "決定済み", count: 6 },
      { value: "対象外", count: 0 },
      { value: "取り下げ", count: 0 },
    ],
  },
  {
    key: "tags",
    label: "タグ",
    values: [
      { value: "プレビュー", count: 3 },
      { value: "サーバー", count: 2 },
      { value: "スキル", count: 1 },
    ],
  },
];

const meta = {
  title: "Shared/FilterDrawer",
  component: FilterDrawer,
  args: { groups: taskGroups, selected: {}, total: 8, shown: 8, onToggleValue: fn(), onClearGroup: fn(), onClearAll: fn(), onClose: fn(), onTextChange: fn() },
} satisfies Meta<typeof FilterDrawer>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 何も選んでいない（タスク: 種類・状態・タグ）。見出しの右は「8 件」で、「解除」と「すべて解除」を出さない */
export const Default: Story = {};

/** 検討事項で状態に 4 つ・タグに 1 つを選んでいる。見出しの右は「36 件中 3 件」、選んだ条件に「{件数} 件を選択」と「解除」、下端に「すべて解除」と「3 件を表示」 */
export const Selected: Story = {
  args: {
    groups: decisionGroups,
    selected: { status: ["要見直し", "未決定", "保留", "未整理"], tags: ["プレビュー"] },
    total: 36,
    shown: 3,
  },
};

/** 今の条件では 0 件になる値がある。その値は文字と件数を薄くし、選べるまま残す */
export const ZeroValue: Story = {
  args: { groups: decisionGroups, selected: { tags: ["プレビュー"] }, total: 36, shown: 11 },
};

/** 長いタグ。値の文字を折り返し、件数の列を押し出さない */
export const LongTag: Story = {
  args: {
    groups: [
      {
        key: "tags",
        label: "タグ",
        values: [
          { value: "絞り込みのドロワーとコメントの一覧を同時に開かない出し方の話題", count: 12 },
          { value: "プレビュー", count: 5 },
        ],
      },
    ],
    total: 17,
    shown: 17,
  },
};

/** 該当なし。見出しの右は「8 件中 0 件」、下端のボタンは「0 件を表示」 */
export const NoMatch: Story = {
  args: { selected: { kind: ["作業"], status: ["未着手"] }, shown: 0 },
};

/** 幅 390px。トップバーの下から画面の幅いっぱいに重ねる */
export const Narrow: Story = {
  args: { narrow: true },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 用語集で、用語の欄に「移し」を入れている。値の条件より上に「文字を含む」と ID・用語・意味・別名・使わない表記の欄を並べ、見出しの右は「6 件中 1 件」。タグの件数は文字で絞った 1 件で数える。入っている欄は中身を消す × を出す */
export const TextConditions: Story = {
  args: {
    groups: [{ key: "tags", label: "タグ", values: [{ value: "mindstella", count: 1 }] }],
    texts: [
      { key: "id", label: "ID", value: "" },
      { key: "title", label: "用語", value: "移し" },
      { key: "meaning", label: "意味", value: "" },
      { key: "aliases", label: "別名", value: "" },
      { key: "avoid", label: "使わない表記", value: "" },
    ],
    selected: { "~title": ["移し"] },
    total: 6,
    shown: 1,
  },
};

/** タスクでタグ「プレビュー」と「サーバー」を選び、組み合わせ方は既定の「すべて含む」。タグの条件の見出しの下に「すべて含む / どれかを含む」の切り替えを出し、「すべて含む」が押された状態 */
export const TagMatchAll: Story = {
  args: { selected: { tags: ["プレビュー", "サーバー"] }, shown: 2, tagMatch: "all", onTagMatchChange: fn() },
};

/** 組み合わせ方を「どれかを含む」に切り替えた。見出しの右の件数がどちらかのタグを持つ 6 件になる */
export const TagMatchAny: Story = {
  args: { selected: { tags: ["プレビュー", "サーバー"] }, shown: 6, tagMatch: "any", onTagMatchChange: fn() },
};

/** プリセットを 4 件渡した。値の条件より上にプリセットを並べ、件数が 0 の「通知」は破線の枠線と薄い文字で出す */
export const Presets: Story = {
  args: {
    presets: [
      { name: "画面の設計", count: 2, applied: false },
      { name: "廃止する画面", count: 1, applied: false },
      { name: "保存の仕組み", count: 1, applied: false },
      { name: "通知", count: 0, applied: false },
    ],
    onApplyPreset: fn(),
  },
};

/** 今のタグの条件が「廃止する画面」と同じ。そのプリセットのボタンを選択済みの見た目にする */
export const PresetApplied: Story = {
  args: {
    selected: { tags: ["プレビュー", "サーバー"] },
    presets: [
      { name: "画面の設計", count: 2, applied: false },
      { name: "廃止する画面", count: 1, applied: true },
    ],
    onApplyPreset: fn(),
  },
};

/** タグの条件が簡易で表せない式。指定方法を「詳細」にし、簡易を選択できなくする */
export const TagDetail: Story = {
  args: {
    shown: 3,
    tagExpr: { and: [{ field: "tags", op: "eq", values: ["プレビュー"] }, { field: "tags", op: "ne", values: ["サーバー"] }] },
    onTagExprChange: fn(),
    onTagMatchChange: fn(),
  },
};
