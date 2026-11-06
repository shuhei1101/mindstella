// shadcn/ui の Checkbox（ブラウザの checkbox をトークンの色で描く）
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const Checkbox = ({ className, ...props }: Omit<ComponentProps<"input">, "type">) => <input type="checkbox" className={cn("size-4 accent-primary", className)} {...props} />;
