import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DailyTask, DayView, TeamDayView } from "@/types";

export const dayKey = (date: string, userId?: number) => ["daily", date, userId ?? "me"] as const;
export const teamDayKey = (date: string) => ["daily", "team", date] as const;

export function useDay(date: string, userId?: number) {
  return useQuery({
    queryKey: dayKey(date, userId),
    queryFn: async () =>
      (await api.get<DayView>("/daily-tasks", { params: { date, user_id: userId } })).data,
  });
}

export function useTeamDay(date: string, enabled = true) {
  return useQuery({
    queryKey: teamDayKey(date),
    enabled,
    queryFn: async () => (await api.get<TeamDayView>("/daily-tasks/team", { params: { date } })).data,
  });
}

/** Anything that changes a task invalidates every day view - a tick moves an
 *  item between days, so refreshing only the current one would go stale. */
function useDailyMutation<TArgs>(fn: (args: TArgs) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["daily"] }),
  });
}

export function useAddTask() {
  return useDailyMutation(async ({ title, task_date }: { title: string; task_date?: string }) =>
    (await api.post<DailyTask>("/daily-tasks", { title, task_date })).data
  );
}

export function useUpdateTask() {
  return useDailyMutation(
    async ({ id, ...body }: { id: number; title?: string; completed?: boolean; task_date?: string }) =>
      (await api.patch<DailyTask>(`/daily-tasks/${id}`, body)).data
  );
}

export function useDeleteTask() {
  return useDailyMutation(async (id: number) => (await api.delete(`/daily-tasks/${id}`)).data);
}
