import { getRouteApi } from "@tanstack/react-router";

import { useGetRecords } from "@/shared/api/generated/preview";
import { Topbar } from "@/shared/components/topbar";

const route = getRouteApi("/");

export const OverviewScreen = () => {
  const { tab } = route.useSearch();
  const { data } = useGetRecords();
  if (data === undefined) {
    return <p>読み込み中</p>;
  }
  return (
    <main>
      <Topbar title={data.data.settings.summary} onSearch={() => undefined} />
      <p data-testid="tab">{tab}</p>
      <p data-testid="decision-count">{data.data.decisions.length}</p>
    </main>
  );
};
