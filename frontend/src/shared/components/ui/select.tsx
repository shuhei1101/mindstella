// shadcn/ui の Select の代わりに、ブラウザの select をトークンの色で描く
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const Select = ({ className, ...props }: ComponentProps<"select">) => <select className={cn("h-8 w-full rounded-control border border-input bg-card px-2 text-small focus-visible:outline-2 focus-visible:outline-ring", className)} {...props} />;
