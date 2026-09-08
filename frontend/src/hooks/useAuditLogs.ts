import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLog, AuditLogFilters } from "@/types";

export function auditLogsKey(filters: AuditLogFilters) {
  return ["audit-logs", filters] as const;
}

export function useAuditLogs(filters: AuditLogFilters) {
  return useQuery({
    queryKey: auditLogsKey(filters),
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (filters.user_id) params.user_id = filters.user_id;
      if (filters.action) params.action = filters.action;
      if (filters.entity_type) params.entity_type = filters.entity_type;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      params.limit = filters.limit ?? 50;
      params.offset = filters.offset ?? 0;
      return (await api.get<AuditLog[]>("/audit-logs", { params })).data;
    },
  });
}
