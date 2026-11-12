// 全体の検索のストーリー。記録は props で渡す
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { SearchDialog } from "@/features/search/search/search-dialog";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { RECORDS } from "@/testing/msw/handlers";

const index = buildIndex(RECORDS as unknown as MindmapData);

/** 検索の言葉を自分で持って描く */
const WithQuery = ({ initial }: { initial: string }) => {
  const [query, setQuery] = useState(initial);
  return <SearchDialog index={index} query={query} onQueryChange={setQuery} onOpen={() => undefined} onClose={() => undefined} />;
};

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
