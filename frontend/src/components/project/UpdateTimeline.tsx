import * as React from "react";
import { motion } from "framer-motion";
import { AlertOctagon, ClipboardList, TrendingUp } from "lucide-react";
import type { ProjectUpdate, UserBrief } from "@/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/common/EmptyState";
import { formatDateTime, initials, timeAgo } from "@/lib/utils";

interface UpdateTimelineProps {
  updates: ProjectUpdate[];
  userById: Map<number, UserBrief>;
}

const SECTIONS: Array<{ key: keyof ProjectUpdate; label: string; icon: React.ReactNode; dot: string }> = [
  { key: "plan", label: "Plan", icon: <ClipboardList className="h-3.5 w-3.5" />, dot: "bg-sky-500" },
  { key: "progress", label: "Progress", icon: <TrendingUp className="h-3.5 w-3.5" />, dot: "bg-success" },
  { key: "problem", label: "Problem", icon: <AlertOctagon className="h-3.5 w-3.5" />, dot: "bg-destructive" },
];

export function UpdateTimeline({ updates, userById }: UpdateTimelineProps) {
  if (updates.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-6 w-6" />}
        title="No updates logged yet"
        description="Add the first Plan / Progress / Problem update below to start this project's history."
      />
    );
  }

  return (
    <ol className="relative space-y-6 border-l border-border pl-6">
      {updates.map((u, i) => {
        const author = userById.get(u.author_id);
        return (
          <motion.li
            key={u.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, delay: Math.min(i * 0.04, 0.3) }}
            className="relative"
          >
            <span className="absolute -left-[29px] top-1 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background bg-primary" />
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Avatar className="h-6 w-6">
                <AvatarFallback className="text-[10px]">{initials(author?.name)}</AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium text-foreground">{author?.name ?? "Unknown"}</span>
              <span className="text-xs text-muted-foreground" title={formatDateTime(u.created_at)}>
                {timeAgo(u.created_at)}
              </span>
            </div>
            <Card className="divide-y divide-border overflow-hidden">
              {SECTIONS.map((s) => {
                const value = u[s.key] as string | null;
                if (!value) return null;
                return (
                  <div key={String(s.key)} className="p-4">
                    <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                      {s.icon}
                      {s.label}
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-foreground/90">{value}</p>
                  </div>
                );
              })}
              {!u.plan && !u.progress && !u.problem && u.raw_bullets && (
                <div className="p-4">
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">{u.raw_bullets}</p>
                </div>
              )}
            </Card>
          </motion.li>
        );
      })}
    </ol>
  );
}
