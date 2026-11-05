// SPA のルート（/）。search を検証し、記録に合わない値は画面が外す
import { createFileRoute } from "@tanstack/react-router";

import { OverviewScreen } from "@/features/overview/overview/overview-screen";
import { parsePreviewSearch } from "@/shared/core/preview-search";
import { previewQueries } from "@/shared/hooks/preview-queries";

export const Route = createFileRoute("/")({
  validateSearch: parsePreviewSearch,
  loader: async ({ context: { queryClient } }) => {
    // 失敗は画面が query の error で出すので、先読みでは握りつぶす
    const ignore = (): undefined => undefined;
    const [records, comments, edits, threads] = previewQueries();
    await Promise.all([
      queryClient.query(records).catch(ignore),
      queryClient.query(comments).catch(ignore),
      queryClient.query(edits).catch(ignore),
      queryClient.query(threads).catch(ignore),
    ]);
  },
  component: OverviewScreen,
});
