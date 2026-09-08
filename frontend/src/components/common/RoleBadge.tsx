import { Badge } from "@/components/ui/badge";
import type { Role } from "@/types";
import { cn } from "@/lib/utils";

const ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  member: "Member",
  requestor: "Requestor",
};

const ROLE_CLASS: Record<Role, string> = {
  admin: "bg-primary/15 text-primary border-primary/25",
  member: "bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/25",
  requestor: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/25",
};

export function RoleBadge({ role, className }: { role: Role; className?: string }) {
  return (
    <Badge variant="outline" className={cn(ROLE_CLASS[role], className)}>
      {ROLE_LABEL[role]}
    </Badge>
  );
}
