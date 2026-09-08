import * as React from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Project, Status, Vertical } from "@/types";

interface PipelineCardProps {
  projects: Project[];
  statuses: Status[];
  verticals: Vertical[];
  onPickStatus?: (statusId: number) => void;
}

/**
 * Where the work sits right now: one proportional bar across the pipeline
 * stages (colours come from Admin > Statuses) and the split by vertical.
 * Purely derived from the project list - nothing here is configured twice.
 */
export function PipelineCard({ projects, statuses, verticals, onPickStatus }: PipelineCardProps) {
  const stages = React.useMemo(
    () =>
      [...statuses]
        .filter((s) => s.is_active !== false)
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((s) => ({ ...s, count: projects.filter((p) => p.status_id === s.id).length })),
    [statuses, projects]
  );
  const total = projects.length;
  const byVertical = React.useMemo(() => {
    const rows = verticals
      .map((v) => ({ id: v.id, name: v.name, count: projects.filter((p) => p.vertical_id === v.id).length }))
      .filter((r) => r.count > 0)
      .sort((a, b) => b.count - a.count);
    const max = rows[0]?.count ?? 1;
    return rows.slice(0, 5).map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }));
  }, [verticals, projects]);

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle>Pipeline</CardTitle>
        <CardDescription>Where the {total} project{total === 1 ? "" : "s"} sit right now</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-5">
        <div>
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted" role="img" aria-label="Projects by stage">
            {stages.map((s, i) => (
              <motion.button
                key={s.id}
                type="button"
                initial={{ width: 0 }}
                animate={{ width: total ? `${(s.count / total) * 100}%` : "0%" }}
                transition={{ duration: 0.5, delay: i * 0.05, ease: "easeOut" }}
                style={{ backgroundColor: s.color || "#888" }}
                className="h-full min-w-0 transition-opacity hover:opacity-80 focus-visible:opacity-80"
                title={`${s.name}: ${s.count}`}
                aria-label={`${s.name}: ${s.count} project${s.count === 1 ? "" : "s"}`}
                onClick={() => onPickStatus?.(s.id)}
              />
            ))}
          </div>
          {/* Wrapping row rather than fixed columns: a status name is never
              worth truncating, and "In queue" did not fit a quarter-width cell. */}
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
            {stages.map((s) => (
              <li key={s.id} className="flex items-center gap-1.5 text-xs">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: s.color || "#888" }} />
                <span className="text-muted-foreground">{s.name}</span>
                <span className="font-semibold tabular-nums text-foreground">{s.count}</span>
              </li>
            ))}
          </ul>
        </div>

        {byVertical.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">By vertical</p>
            {/* Name on its own line above the bar. Vertical names run long
                ("Capital Market Solutions"), and a fixed-width column could
                only ever show them cut in half. */}
            <ul className="space-y-2.5">
              {byVertical.map((v, i) => (
                <li key={v.id} className="space-y-1 text-xs">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-foreground">{v.name}</span>
                    <span className="shrink-0 font-semibold tabular-nums text-foreground">{v.count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${v.pct}%` }}
                      transition={{ duration: 0.5, delay: 0.15 + i * 0.05, ease: "easeOut" }}
                      className="brand-gradient h-full rounded-full"
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
