import * as React from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  hint?: string;
  loading?: boolean;
  accent?: "primary" | "success" | "warning" | "default";
  index?: number;
}

const ACCENT: Record<string, string> = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  default: "bg-brand-sky/15 text-brand-navy-2 dark:text-brand-sky",
};

const BAR: Record<string, string> = {
  primary: "from-brand-violet to-brand-sky",
  success: "from-success to-success/40",
  warning: "from-warning to-warning/40",
  default: "from-brand-navy-2 to-brand-sky",
};

export function StatCard({ label, value, icon, hint, loading, accent = "default", index = 0 }: StatCardProps) {
  return (
    // h-full on both: the grid cell already stretches to the tallest card in the
    // row, but without this the Card collapses to its own content, so a label
    // that wraps onto three lines ends up a visibly taller box than one that
    // fits on one.
    <motion.div
      className="h-full"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      <Card className="surface-hover relative h-full overflow-hidden">
        <span aria-hidden="true" className={cn("absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r", BAR[accent])} />
        <CardContent className="flex h-full items-center justify-between gap-3 p-5">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
            {loading ? (
              <Skeleton className="mt-2 h-7 w-16" />
            ) : (
              <p className="mt-1.5 text-[1.75rem] font-semibold leading-none tabular-nums tracking-tight text-foreground">{value}</p>
            )}
            {hint && !loading && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
          </div>
          {icon && (
            <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", ACCENT[accent])}>
              {icon}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
