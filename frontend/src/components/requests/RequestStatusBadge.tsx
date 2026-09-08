import { Badge } from "@/components/ui/badge";
import type { RequestStatus } from "@/types";
import { cn } from "@/lib/utils";

const CONFIG: Record<RequestStatus, { label: string; className: string }> = {
  submitted: { label: "Submitted", className: "bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/25" },
  under_review: { label: "Under Review", className: "bg-warning/15 text-warning border-warning/30" },
  approved: { label: "Approved", className: "bg-success/15 text-success border-success/30" },
  rejected: { label: "Rejected", className: "bg-destructive/15 text-destructive border-destructive/30" },
  on_hold: { label: "On Hold", className: "bg-muted text-muted-foreground border-border" },
};

export function RequestStatusBadge({ status, className }: { status: RequestStatus; className?: string }) {
  const c = CONFIG[status];
  return (
    <Badge variant="outline" className={cn(c.className, className)}>
      {c.label}
    </Badge>
  );
}
