// 全体の検索のストーリー。記録は props で渡す
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { SearchDialog, type FilterCandidate } from "@/features/search/search/search-dialog";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";

const index = buildIndex(RECORDS as unknown as MindmapData);

/** 検索の言葉を自分で持って描く */
const WithQuery = ({ initial, filterCandidates }: { initial: string; filterCandidates?: FilterCandidate[] }) => {
  const [query, setQuery] = useState(initial);
  return <SearchDialog index={index} query={query} onQueryChange={setQuery} onOpen={() => undefined} onClose={() => undefined} filterCandidates={filterCandidates} onApplyFilter={filterCandidates === undefined ? undefined : () => undefined} />;
};

/** 資料の画面の絞り込みの条件の値 */
const docFilters: FilterCandidate[] = [
  { key: "status", label: "状態", value: "下書き", count: 1 },
  { key: "status", label: "状態", value: "確認中", count: 1 },
  { key: "status", label: "状態", value: "完成", count: 0 },
  { key: "tags", label: "タグ", value: "下書きの整理", count: 1 },
];

const meta = {
  title: "Features/Search/SearchDialog",
  component: WithQuery,
  args: { initial: "" },
} satisfies Meta<typeof WithQuery>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 開いたとき（言葉が空） */
export const Empty: Story = {};

/** 段ごとの見出しの下に結果を並べる */
export const Hits: Story = { args: { initial: "D-1" } };

/** 当たらない */
export const NoHit: Story = { args: { initial: "無い言葉" } };

/** 開いている画面の絞り込みの値が検索の文字で始まる。結果の先頭に絞り込みの候補を並べる */
export const FilterCandidates: Story = { args: { initial: "下書き", filterCandidates: docFilters } };

/** 絞り込みの値が当たり、項目は当たらない */
export const FilterCandidatesOnly: Story = { args: { initial: "確認", filterCandidates: docFilters } };
