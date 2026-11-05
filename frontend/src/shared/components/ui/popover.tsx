// shadcn/ui の Popover（Base UI 版）
import { Popover as BasePopover } from "@base-ui/react/popover";
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const Popover = BasePopover.Root;
export const PopoverTrigger = BasePopover.Trigger;
export const PopoverTitle = BasePopover.Title;

export const PopoverContent = ({ className, ...props }: Omit<ComponentProps<typeof BasePopover.Popup>, "className"> & { className?: string }) => (
  <BasePopover.Portal>
    <BasePopover.Positioner sideOffset={6} className="z-50">
      <BasePopover.Popup className={cn("rounded-card border border-border bg-popover p-2 text-popover-foreground shadow-lg", className)} {...props} />
    </BasePopover.Positioner>
  </BasePopover.Portal>
);
