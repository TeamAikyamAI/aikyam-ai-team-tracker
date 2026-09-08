import * as React from "react";
import { cn } from "@/lib/utils";

export const VisuallyHidden = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "absolute h-px w-px overflow-hidden whitespace-nowrap border-0 p-0",
        "[clip:rect(0,0,0,0)] [clip-path:inset(50%)]",
        className
      )}
      {...props}
    />
  )
);
VisuallyHidden.displayName = "VisuallyHidden";
