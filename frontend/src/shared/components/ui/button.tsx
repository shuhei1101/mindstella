// shadcn/ui の Button（Base UI 版）。見た目の違いは variants で持つ。pending の間は押せなくし、1 秒を超えたら中身の上に回るマーカーを重ねる
import { Button as BaseButton } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";
import { useEffect, useState, type ComponentProps } from "react";

import { Icon } from "@/shared/components/icon";
import { cn } from "@/shared/lib/cn";

/** 待つ間に回るマーカーを出すまでのミリ秒（1 秒未満の待ちでは出さない） */
const PENDING_SPINNER_DELAY_MS = 1000;

export const buttonVariants = cva(
  "inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-control text-small font-medium whitespace-nowrap disabled:cursor-default disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-accent",
        ghost: "bg-transparent hover:bg-accent hover:text-accent-foreground",
        outline: "border border-border bg-transparent hover:bg-accent",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        default: "h-8 px-2.5",
        icon: "size-8",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

type ButtonProps = Omit<ComponentProps<typeof BaseButton>, "className"> &
  VariantProps<typeof buttonVariants> & {
    className?: string;
    /** 書き込みの応答を待つ間か。真の間は押せなくし、1 秒を超えたら中身を透明にして回るマーカーを重ねる（中身は残すので幅とボタンの名前を変えない） */
    pending?: boolean;
  };

/** `pending` が真になってから 1 秒を超えたかを返す */
const useSpinnerShown = (pending: boolean): boolean => {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!pending) return undefined;
    const timer = window.setTimeout(() => { setShown(true); }, PENDING_SPINNER_DELAY_MS);
    // 待つ間が終わったら、次に待つときに 1 秒を数え直す
    return () => {
      window.clearTimeout(timer);
      setShown(false);
    };
  }, [pending]);
  return pending && shown;
};

export const Button = ({ className, variant, size, pending = false, disabled, children, ...props }: ButtonProps) => {
  const spinner = useSpinnerShown(pending);
  return (
    <BaseButton
      type="button"
      className={cn(buttonVariants({ variant, size }), pending && "relative", className)}
      disabled={pending || disabled}
      aria-busy={pending || undefined}
      {...props}
    >
      {pending ? (
        <>
          <span className={cn("inline-flex items-center gap-1.5", spinner && "opacity-0")}>{children}</span>
          {spinner ? (
            <span data-part="pending-spinner" aria-hidden="true" className="absolute inset-0 flex items-center justify-center">
              <Icon name="spin" className="animate-spin" />
            </span>
          ) : null}
        </>
      ) : (
        children
      )}
    </BaseButton>
  );
};
