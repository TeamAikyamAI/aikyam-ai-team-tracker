import * as React from "react";
import {
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ListTodo,
  Plus,
  RotateCcw,
  Trash2,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { useCan } from "@/hooks/usePermissions";
import { useAddTask, useDay, useDeleteTask, useTeamDay, useUpdateTask } from "@/hooks/useDaily";
import type { DailyTask } from "@/types";

/** Local YYYY-MM-DD - never toISOString(), which would shift the day in IST. */
function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function shiftDay(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y!, m! - 1, d!);
  dt.setDate(dt.getDate() + days);
  return isoDay(dt);
}

function prettyDay(iso: string, today: string): string {
  if (iso === today) return "Today";
  if (iso === shiftDay(today, -1)) return "Yesterday";
  if (iso === shiftDay(today, 1)) return "Tomorrow";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y!, m! - 1, d!).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

function TaskRow({
  task,
  done,
  readOnly,
  onToggle,
  onDelete,
}: {
  task: DailyTask;
  done: boolean;
  readOnly: boolean;
  onToggle: (completed: boolean) => void;
  onDelete: () => void;
}) {
  return (
    <li className="group flex items-start gap-3 rounded-md px-2 py-2 transition-colors hover:bg-muted/60">
      <Checkbox
        checked={done}
        disabled={readOnly}
        aria-label={done ? `Mark "${task.title}" as not done` : `Mark "${task.title}" as done`}
        onCheckedChange={(v) => onToggle(v === true)}
        className="mt-0.5"
      />
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm leading-snug", done && "text-muted-foreground line-through")}>
          {task.title}
        </p>
        {!done && task.carried_days > 0 && (
          <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-warning/10 px-2 py-0.5 text-[11px] font-medium text-warning">
            <RotateCcw className="h-3 w-3" />
            carried {task.carried_days} {task.carried_days === 1 ? "day" : "days"}
          </span>
        )}
      </div>
      {!readOnly && (
        <button
          onClick={onDelete}
          aria-label={`Delete "${task.title}"`}
          className="rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </li>
  );
}

export default function MyDayPage() {
  const { user } = useAuth();
  const can = useCan();
  const today = isoDay(new Date());

  const [date, setDate] = React.useState(today);
  const [whose, setWhose] = React.useState<string>("me");
  const [draft, setDraft] = React.useState("");

  const viewingUserId = whose === "me" ? undefined : Number(whose);
  const { data: day, isLoading } = useDay(date, viewingUserId);
  const { data: team } = useTeamDay(date, can("team_day"));

  const addTask = useAddTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const readOnly = !!day && !day.is_own;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const title = draft.trim();
    if (!title) return;
    addTask.mutate(
      { title, task_date: date },
      {
        onSuccess: () => setDraft(""),
        onError: () => toast.error("Couldn't add that task"),
      }
    );
  };

  return (
    <div>
      <PageHeader
        title="My Day"
        description="Your own list for the day. Anything you don't tick moves to the next day by itself."
        actions={
          <div className="flex items-center gap-2">
            {can("team_day") && team && team.rows.length > 1 && (
              <Select value={whose} onValueChange={setWhose}>
                <SelectTrigger className="h-9 w-44 text-xs">
                  <Users className="mr-1 h-3.5 w-3.5 shrink-0" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="me">My list</SelectItem>
                  {team.rows
                    .filter((r) => r.user_id !== user?.id)
                    .map((r) => (
                      <SelectItem key={r.user_id} value={String(r.user_id)}>
                        {r.user_name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            )}
            <div className="flex items-center rounded-md border border-input bg-card">
              <Button variant="ghost" size="icon-sm" aria-label="Previous day" onClick={() => setDate(shiftDay(date, -1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <button
                onClick={() => setDate(today)}
                className="min-w-[6.5rem] px-2 text-xs font-medium tabular-nums"
                title="Jump to today"
              >
                {prettyDay(date, today)}
              </button>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Next day"
                disabled={date >= today}
                onClick={() => setDate(shiftDay(date, 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        }
      />

      <div className="mb-6 grid grid-cols-3 gap-4">
        <StatCard label="Done" value={day?.summary.done ?? 0} icon={<CheckCircle2 className="h-5 w-5" />} loading={isLoading} accent="success" index={0} />
        <StatCard label="Still pending" value={day?.summary.pending ?? 0} icon={<ListTodo className="h-5 w-5" />} loading={isLoading} accent="primary" index={1} />
        <StatCard label="Carried over" value={day?.summary.carried ?? 0} icon={<RotateCcw className="h-5 w-5" />} loading={isLoading} accent="warning" index={2} />
      </div>

      {readOnly && (
        <p className="mb-4 rounded-md border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          You're looking at {day?.user_name}'s day. Read only, on purpose: a daily list is only
          honest if the person who owns it is the only one who can tick it.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <ListTodo className="h-4 w-4 text-muted-foreground" />
              To do
              {day && <span className="ml-auto text-sm font-normal tabular-nums text-muted-foreground">{day.open.length}</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!readOnly && (
              <form onSubmit={submit} className="mb-3 flex gap-2">
                <Input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="What needs doing?"
                  aria-label="New task"
                  maxLength={500}
                />
                <Button type="submit" size="icon" aria-label="Add task" disabled={!draft.trim() || addTask.isPending}>
                  <Plus className="h-4 w-4" />
                </Button>
              </form>
            )}

            {isLoading && <Skeleton className="h-24 rounded-md" />}

            {!isLoading && day && day.open.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                {date === today ? "Nothing on the list yet." : "Nothing was pending on this day."}
              </p>
            )}

            {!isLoading && day && day.open.length > 0 && (
              <ul className="-mx-2">
                {day.open.map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    done={false}
                    readOnly={readOnly}
                    onToggle={(completed) => updateTask.mutate({ id: t.id, completed })}
                    onDelete={() => deleteTask.mutate(t.id)}
                  />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-success" />
              Done {date === today ? "today" : "that day"}
              {day && <span className="ml-auto text-sm font-normal tabular-nums text-muted-foreground">{day.done.length}</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading && <Skeleton className="h-24 rounded-md" />}
            {!isLoading && day && day.done.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">Nothing ticked off yet.</p>
            )}
            {!isLoading && day && day.done.length > 0 && (
              <ul className="-mx-2">
                {day.done.map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    done
                    readOnly={readOnly}
                    onToggle={(completed) => updateTask.mutate({ id: t.id, completed })}
                    onDelete={() => deleteTask.mutate(t.id)}
                  />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {can("team_day") && team && team.rows.length > 0 && (
        <Card className="mt-4">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-muted-foreground" />
              The team on {prettyDay(date, today).toLowerCase()}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-border">
              {team.rows.map((r) => (
                <li key={r.user_id} className="flex items-center gap-3 py-2 text-sm">
                  <button
                    className="truncate text-left font-medium hover:underline"
                    onClick={() => setWhose(r.user_id === user?.id ? "me" : String(r.user_id))}
                  >
                    {r.user_name}
                  </button>
                  <span className="ml-auto flex items-center gap-4 text-xs tabular-nums text-muted-foreground">
                    <span className="text-success">{r.summary.done} done</span>
                    <span>{r.summary.pending} pending</span>
                    {r.summary.carried > 0 && <span className="text-warning">{r.summary.carried} carried</span>}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {!isLoading && !day && (
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="Couldn't load your day"
          description="Check that the backend is running, then refresh."
        />
      )}
    </div>
  );
}
