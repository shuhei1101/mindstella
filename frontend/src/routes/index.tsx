// 概要のルート（/）。search を検証し、決めた値以外の search は URL から外して開き直す
import { createFileRoute, redirect } from "@tanstack/react-router";

import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { overviewQueries } from "@/features/overview/overview/queries";
import { parseOverviewSearch } from "@/features/overview/overview/search";

export const Route = createFileRoute("/")({
  validateSearch: parseOverviewSearch,
  beforeLoad: ({ search, location }) => {
    const expected = search.tab === undefined ? "" : `?tab=${search.tab}`;
    if (location.searchStr !== expected) {
      // eslint-disable-next-line @typescript-eslint/only-throw-error -- TanStack Router は redirect を投げて送り直す
      throw redirect({ to: "/", search, replace: true });
    }
  },
  loader: async ({ context: { queryClient } }) => {
    const [records, comments, edits, threads] = overviewQueries();
    await Promise.all([
      queryClient.prefetchQuery(records),
      queryClient.prefetchQuery(comments),
      queryClient.prefetchQuery(edits),
      queryClient.prefetchQuery(threads),
    ]);
  },
  component: OverviewScreen,
});
