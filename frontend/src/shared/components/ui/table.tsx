// shadcn/ui の Table
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

export const TableRoot = ({ className, ...props }: ComponentProps<"table">) => <table className={cn("w-full border-collapse text-small", className)} {...props} />;
export const TableHeader = (props: ComponentProps<"thead">) => <thead className="sticky top-0 z-10 bg-thead" {...props} />;
export const TableBody = (props: ComponentProps<"tbody">) => <tbody {...props} />;
export const TableRow = ({ className, ...props }: ComponentProps<"tr">) => <tr className={cn("border-b border-border-soft hover:bg-row-hover", className)} {...props} />;
export const TableHead = ({ className, ...props }: ComponentProps<"th">) => <th className={cn("px-2 py-1 text-left font-medium whitespace-nowrap", className)} {...props} />;
export const TableCell = ({ className, ...props }: ComponentProps<"td">) => <td className={cn("px-2 py-1 align-top", className)} {...props} />;
