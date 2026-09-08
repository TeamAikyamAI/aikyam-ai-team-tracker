import * as React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { CalendarDays } from "lucide-react";
import type { Project, Status, UserBrief, Vertical } from "@/types";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { EmptyState } from "@/components/common/EmptyState";
import { formatDate, initials } from "@/lib/utils";
import { LayoutGrid } from "lucide-react";

interface KanbanBoardProps {
  projects: Project[];
  statuses: Status[];
  verticals: Vertical[];
  users: UserBrief[];
}

export function KanbanBoard({ projects, statuses, verticals, users }: KanbanBoardProps) {
  const verticalById = React.useMemo(() => new Map(verticals.map((v) => [v.id, v])), [verticals]);
  const userById = React.useMemo(() => new Map(users.map((u) => [u.id, u])), [users]);

  const sortedStatuses = React.useMemo(
    () => [...statuses].filter((s) => s.is_active !== false).sort((a, b) => a.sort_order - b.sort_order),
    [statuses]
  );

  if (sortedStatuses.length === 0) {
    return (
      <EmptyState
        icon={<LayoutGrid className="h-6 w-6" />}
        title="No statuses configured"
        description="Ask an admin to set up project statuses from the Admin Panel."
      />
    );
  }

  return (
    // Every column is the same fixed-height box whatever it holds: the cards
    // scroll inside it, so a status with twenty projects no longer stretches
    // the board (and every other column with it) down the page.
    <div className="flex gap-4 overflow-x-auto pb-3 scrollbar-thin">
      {sortedStatuses.map((status) => {
        const items = projects.filter((p) => p.status_id === status.id);
        return (
          <div
            key={status.id}
            className="flex h-[60vh] max-h-[38rem] min-h-[18rem] w-72 shrink-0 flex-col lg:w-auto lg:min-w-[13.5rem] lg:flex-1"
          >
            {/* Outside the scroll area, so it stays put while cards move under it. */}
            <div className="mb-3 flex shrink-0 items-center justify-between px-1">
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: status.color || "#888" }}
                />
                <span className="truncate text-sm font-semibold text-foreground">{status.name}</span>
              </div>
              <span className="ml-2 shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-medium tabular-nums text-muted-foreground">
                {items.length}
              </span>
            </div>
            <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto rounded-xl border border-border/60 bg-muted/40 p-2.5 scrollbar-thin">
              {items.length === 0 && (
                <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-border/70 py-8 text-xs text-muted-foreground">
                  No projects
                </div>
              )}
              {items.map((p, i) => {
                const vertical = verticalById.get(p.vertical_id);
                const owners = (p.owner_ids ?? []).map((id) => userById.get(id)).filter(Boolean) as UserBrief[];
                return (
                  <motion.div
                    key={p.id}
                    layout
                    // Without this the flex column squashes the cards to fit
                    // instead of letting the box scroll.
                    className="shrink-0"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: Math.min(i * 0.02, 0.2) }}
                  >
                    <Link to={`/projects/${p.id}`} className="block rounded-xl">
                      <Card
                        className="surface-hover cursor-pointer border-l-[3px] p-3.5"
                        style={{ borderLeftColor: status.color || undefined }}
                      >
                        <p className="text-sm font-medium leading-snug text-foreground line-clamp-2">{p.name}</p>
                        {vertical && (
                          // Wraps to a second line rather than cutting the name
                          // in half - vertical names are long.
                          <p className="mt-1.5 text-xs leading-snug text-muted-foreground">{vertical.name}</p>
                        )}
                        <div className="mt-3 flex items-center justify-between">
                          <div className="flex -space-x-1.5">
                            {owners.slice(0, 3).map((o) => (
                              <Tooltip key={o.id}>
                                <TooltipTrigger asChild>
                                  <Avatar className="h-6 w-6 border-2 border-card">
                                    <AvatarFallback className="text-[9px]">{initials(o.name)}</AvatarFallback>
                                  </Avatar>
                                </TooltipTrigger>
                                <TooltipContent>{o.name}</TooltipContent>
                              </Tooltip>
                            ))}
                            {owners.length > 3 && (
                              <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-card bg-muted text-[9px] font-medium text-muted-foreground">
                                +{owners.length - 3}
                              </div>
                            )}
                          </div>
                          {p.target_date && (
                            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                              <CalendarDays className="h-3 w-3" />
                              {formatDate(p.target_date, { day: "2-digit", month: "short" })}
                            </span>
                          )}
                        </div>
                      </Card>
                    </Link>
                  </motion.div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
