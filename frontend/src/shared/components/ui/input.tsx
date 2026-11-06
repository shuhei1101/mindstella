// shadcn/ui の Input
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const Input = ({ className, ...props }: ComponentProps<"input">) => <input className={cn("h-8 w-full rounded-control border border-input bg-card px-2 text-small placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring", className)} {...props} />;
