import { Button as BaseButton } from "@base-ui/react/button";
import type { ComponentProps } from "react";

import { cn } from "@/shared/lib/cn";

type ButtonProps = ComponentProps<typeof BaseButton>;

export const Button = ({ className, ...props }: ButtonProps) => (
  <BaseButton
    className={cn("rounded-md bg-primary px-3 py-1 text-primary-foreground", className)}
    {...props}
  />
);
