// shadcn/ui の Dialog（Base UI 版）。外側の押下と Esc で閉じる
import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

export const Dialog = BaseDialog.Root;
export const DialogTitle = BaseDialog.Title;
export const DialogClose = BaseDialog.Close;

/** 幕と中身を文書の末尾に描く */
export const DialogContent = ({ className, children, ...props }: Omit<ComponentProps<typeof BaseDialog.Popup>, "className" | "children"> & { className?: string; children: ReactNode }) => (
  <BaseDialog.Portal>
    <BaseDialog.Backdrop className="fixed inset-0 z-40 bg-foreground/40" />
    <BaseDialog.Popup className={cn("fixed top-1/2 left-1/2 z-50 max-h-full w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-card border border-border bg-popover text-popover-foreground shadow-lg", className)} {...props}>
      {children}
    </BaseDialog.Popup>
  </BaseDialog.Portal>
);
