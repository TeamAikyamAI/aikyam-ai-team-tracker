import * as React from "react";
import { ChevronLeft, ChevronRight, ListFilter, ShieldCheck, X } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { useUsers } from "@/hooks/useUsers";
import { formatDateTime } from "@/lib/utils";

const ALL = "__all__";
const PAGE_SIZE = 25;

export default function AuditTrailPage() {
  const { data: users } = useUsers();
  const [userId, setUserId] = React.useState(ALL);
  const [action, setAction] = React.useState("");
  const [entityType, setEntityType] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState<string | null>(null);
  const [dateTo, setDateTo] = React.useState<string | null>(null);
  const [offset, setOffset] = React.useState(0);
  const [sortAsc, setSortAsc] = React.useState(false);

  const { data: logs, isLoading, isError, isFetching } = useAuditLogs({
    user_id: userId !== ALL ? Number(userId) : undefined,
    action: action.trim() || undefined,
    entity_type: entityType.trim() || undefined,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const sorted = React.useMemo(() => {
    const arr = [...(logs ?? [])];
    arr.sort((a, b) => (sortAsc ? a.created_at.localeCompare(b.created_at) : b.created_at.localeCompare(a.created_at)));
    return arr;
  }, [logs, sortAsc]);

  const hasFilters = userId !== ALL || action || entityType || dateFrom || dateTo;

  function clearFilters() {
    setUserId(ALL);
    setAction("");
    setEntityType("");
    setDateFrom(null);
    setDateTo(null);
    setOffset(0);
  }

  return (
    <div>
      <PageHeader title="Audit Trail" description="Full visibility into activity across every user, with date and time detail." />

      <div className="mb-4 flex flex-wrap items-end gap-2">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <ListFilter className="h-4 w-4" />
        </div>
        <Select
          value={userId}
          onValueChange={(v) => {
            setUserId(v);
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="User" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All users</SelectItem>
            {(users ?? []).map((u) => (
              <SelectItem key={u.id} value={String(u.id)}>
                {u.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Action (e.g. create)"
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setOffset(0);
          }}
          className="h-8 w-40 text-xs"
        />
        <Input
          placeholder="Entity type (e.g. project)"
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setOffset(0);
          }}
          className="h-8 w-44 text-xs"
        />
        <DatePicker value={dateFrom} onChange={(v) => { setDateFrom(v); setOffset(0); }} placeholder="From date" className="h-8 w-36 text-xs" />
        <DatePicker value={dateTo} onChange={(v) => { setDateTo(v); setOffset(0); }} placeholder="To date" className="h-8 w-36 text-xs" />
        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8">
            <X className="h-3.5 w-3.5" />
            Clear
          </Button>
        )}
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState icon={<ShieldCheck className="h-6 w-6" />} title="Couldn't load audit logs" description="Check that the backend is running and reachable." />
      )}

      {!isLoading && !isError && sorted.length === 0 && (
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title={hasFilters ? "No activity matches these filters" : "No activity recorded yet"}
          description={hasFilters ? "Try widening your filters." : "Actions taken across the tracker will show up here."}
        />
      )}

      {!isLoading && !isError && sorted.length > 0 && (
        <>
          <div className="rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Details</TableHead>
                  <TableHead>
                    <button onClick={() => setSortAsc((v) => !v)} className="hover:text-foreground">
                      Timestamp {sortAsc ? "↑" : "↓"}
                    </button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium text-foreground">{log.user_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {log.entity_type}
                      {log.entity_id != null && <span className="text-xs"> #{log.entity_id}</span>}
                    </TableCell>
                    <TableCell className="max-w-[320px] truncate text-muted-foreground">{log.details ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Showing {offset + 1}–{offset + sorted.length}
              {isFetching && " · refreshing…"}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={sorted.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
