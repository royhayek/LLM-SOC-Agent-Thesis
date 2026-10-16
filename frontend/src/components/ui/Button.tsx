import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap " +
    "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 " +
    "disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        primary: "bg-accent text-ink hover:bg-accent/90",
        outline:
          "border border-line-strong bg-transparent text-text hover:bg-panel-2 hover:border-accent/50",
        ghost: "bg-transparent text-muted hover:text-text hover:bg-panel-2",
        danger: "border border-sev-critical/40 text-sev-critical hover:bg-sev-critical/10",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-9 px-4",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type Props = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button>;

export function Button({ className, variant, size, ...props }: Props) {
  return <button className={cn(button({ variant, size }), className)} {...props} />;
}
