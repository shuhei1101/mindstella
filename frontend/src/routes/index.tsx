import { createRoute } from "@tanstack/react-router";
import { z } from "zod";

import { rootRoute } from "@/routes/root";
import { OverviewScreen } from "@/features/overview/overview/overview-screen";

const searchSchema = z.object({ tab: z.enum(["overview", "decisions"]).catch("overview") });

export const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: searchSchema,
  component: OverviewScreen,
});
