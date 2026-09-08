import * as React from "react";
import { Link } from "react-router-dom";
import { ArrowUpDown } from "lucide-react";
import type { Project, Status, UserBrief, Vertical } from "@/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatDate, initials } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface ProjectTableProps {
  projects: Project[];
  statuses: Status[];
  verticals: Vertical[];
  users: UserBrief[];
}

type SortKey = "name" | "vertical" | "status" | "target_date" | "updated_at";

export function ProjectTable({ projects, statuses, verticals, users }: ProjectTableProps) {
  const [sortKey, setSortKey] = React.useState<SortKey>("updated_at");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc");

  const verticalById = React.useMemo(() => new Map(verticals.map((v) => [v.id, v])), [verticals]);
  const statusById = React.useMemo(() => new Map(statuses.map((s) => [s.id, s])), [statuses]);
  const userById = React.useMemo(() => new Map(users.map((u) => [u.id, u])), [users]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = React.useMemo(() => {
    const arr = [...projects];
    arr.sort((a, b) => {
      let av = "";
      let bv = "";
      switch (sortKey) {
        case "name":
          av = a.name;
          bv = b.name;
          break;
        case "vertical":
          av = verticalById.get(a.vertical_id)?.name ?? "";
          bv = verticalById.get(b.vertical_id)?.name ?? "";
          break;
        case "status":
          av = statusById.get(a.status_id)?.name ?? "";
          bv = statusById.get(b.status_id)?.name ?? "";
          break;
        case "target_date":
          av = a.target_date ?? "";
          bv = b.target_date ?? "";
          break;
        case "updated_at":
        default:
          av = a.updated_at ?? "";
          bv = b.updated_at ?? "";
      }
      const cmp = av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [projects, sortKey, sortDir, verticalById, statusById]);

  const SortHead = ({ label, sortKeyName }: { label: string; sortKeyName: SortKey }) => (
    <TableHead>
      <button
        onClick={() => toggleSort(sortKeyName)}
        className={cn(
          "flex items-center gap-1 transition-colors hover:text-foreground",
          sortKey === sortKeyName && "text-foreground"
        )}
      >
        {label}
        <ArrowUpDown className="h-3 w-3" />
      </button>
    </TableHead>
  );

  return (
    <div className="rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <SortHead label="Project" sortKeyName="name" />
            <SortHead label="Vertical" sortKeyName="vertical" />
            <SortHead label="Status" sortKeyName="status" />
            <TableHead>Owners</TableHead>
            <SortHead label="Target date" sortKeyName="target_date" />
            <SortHead label="Updated" sortKeyName="updated_at" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((p) => {
            const vertical = verticalById.get(p.vertical_id);
            const status = statusById.get(p.status_id);
            const owners = (p.owner_ids ?? []).map((id) => userById.get(id)).filter(Boolean) as UserBrief[];
            return (
              <TableRow key={p.id} className="group">
                <TableCell className="max-w-[260px]">
                  <Link to={`/projects/${p.id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                    {p.name}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{vertical?.name ?? "—"}</TableCell>
                <TableCell>
                  {status ? <StatusBadge name={status.name} color={status.color} /> : "—"}
                </TableCell>
                <TableCell>
                  <div className="flex -space-x-1.5">
                    {owners.length === 0 && <span className="text-xs text-muted-foreground">Unassigned</span>}
                    {owners.slice(0, 4).map((o) => (
                      <Tooltip key={o.id}>
                        <TooltipTrigger asChild>
                          <Avatar className="h-6 w-6 border-2 border-card">
                            <AvatarFallback className="text-[9px]">{initials(o.name)}</AvatarFallback>
                          </Avatar>
                        </TooltipTrigger>
                        <TooltipContent>{o.name}</TooltipContent>
                      </Tooltip>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(p.target_date)}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(p.updated_at)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
