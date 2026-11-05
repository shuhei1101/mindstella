// shadcn/ui の Textarea
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const Textarea = ({ className, ...props }: ComponentProps<"textarea">) => <textarea className={cn("w-full rounded-control border border-input bg-card p-2 text-small focus-visible:outline-2 focus-visible:outline-ring", className)} {...props} />;
