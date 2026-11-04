// 概要のルートの search params。`tab` は `overview` だけを受け、他の値と無い値は既定に落とす
import { z } from "zod";

export const OverviewSearchSchema = z.object({
  tab: z.enum(["overview"]).optional().catch(undefined),
});

export type OverviewSearch = z.infer<typeof OverviewSearchSchema>;

/** 概要のルートの `validateSearch` */
export const parseOverviewSearch = (search: Record<string, unknown>): OverviewSearch => OverviewSearchSchema.parse(search);
