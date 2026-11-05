// アプリで 1 つの QueryClient（knowledge の規約『QueryClient』の defaultOptions）
import { QueryClient } from "@tanstack/react-query";

/** QueryClient の既定 */
export const QUERY_DEFAULT_OPTIONS = {
  staleTime: 60 * 1000,
  refetchOnWindowFocus: false,
  retry: false,
} as const;

export const createQueryClient = (): QueryClient => new QueryClient({ defaultOptions: { queries: QUERY_DEFAULT_OPTIONS } });
