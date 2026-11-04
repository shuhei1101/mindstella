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
    // 失敗は画面が query の error で出すので、先読みでは握りつぶす
    const ignore = (): undefined => undefined;
    await Promise.all([
      queryClient.query(records).catch(ignore),
      queryClient.query(comments).catch(ignore),
      queryClient.query(edits).catch(ignore),
      queryClient.query(threads).catch(ignore),
    ]);
  },
  component: OverviewScreen,
});
