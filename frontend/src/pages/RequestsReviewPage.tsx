import * as React from "react";
import { FileStack, ListFilter } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { RequestDetailDialog } from "@/components/requests/RequestDetailDialog";
import { useRequests } from "@/hooks/useRequests";
import { useUsers } from "@/hooks/useUsers";
import { useVerticals } from "@/hooks/useVerticals";
import { formatDateTime } from "@/lib/utils";
import type { RequestStatus, ServiceRequest } from "@/types";

const ALL = "__all__";

export default function RequestsReviewPage() {
  const { data: requests, isLoading, isError } = useRequests();
  const { data: users } = useUsers();
  const { data: verticals } = useVerticals();

  const [statusFilter, setStatusFilter] = React.useState<string>(ALL);
  const [verticalFilter, setVerticalFilter] = React.useState<string>(ALL);
  const [active, setActive] = React.useState<ServiceRequest | null>(null);

  const userById = React.useMemo(() => new Map((users ?? []).map((u) => [u.id, u])), [users]);
  const verticalById = React.useMemo(() => new Map((verticals ?? []).map((v) => [v.id, v])), [verticals]);

  const filtered = React.useMemo(() => {
    if (!requests) return [];
    return requests
      .filter((r) => statusFilter === ALL || r.status === statusFilter)
      .filter((r) => verticalFilter === ALL || String(r.vertical_id) === verticalFilter)
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  }, [requests, statusFilter, verticalFilter]);

  const pendingCount = requests?.filter((r) => r.status === "submitted" || r.status === "under_review").length ?? 0;

  return (
    <div>
      <PageHeader
        title="Requests Review"
        description={pendingCount > 0 ? `${pendingCount} request${pendingCount > 1 ? "s" : ""} awaiting your review.` : "Service requests filed by the business."}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <ListFilter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {(["submitted", "under_review", "approved", "rejected", "on_hold"] as RequestStatus[]).map((s) => (
              <SelectItem key={s} value={s}>
                {s.replace("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={verticalFilter} onValueChange={setVerticalFilter}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Vertical" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All verticals</SelectItem>
            {(verticals ?? []).map((v) => (
              <SelectItem key={v.id} value={String(v.id)}>
                {v.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={<FileStack className="h-6 w-6" />}
          title="Couldn't load requests"
          description="Check that the backend is running and reachable, then refresh the page."
        />
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          icon={<FileStack className="h-6 w-6" />}
          title="No requests to show"
          description="New service requests filed by the business will appear here for review."
        />
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Requestor</TableHead>
                <TableHead>Vertical</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Submitted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((r) => (
                <TableRow key={r.id} className="cursor-pointer" onClick={() => setActive(r)}>
                  <TableCell className="max-w-[280px] truncate font-medium text-foreground">{r.title}</TableCell>
                  <TableCell className="text-muted-foreground">{userById.get(r.requestor_id)?.name ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{verticalById.get(r.vertical_id)?.name ?? "—"}</TableCell>
                  <TableCell>
                    <RequestStatusBadge status={r.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(r.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <RequestDetailDialog
        request={active}
        onOpenChange={(open) => !open && setActive(null)}
        requestor={active ? userById.get(active.requestor_id) : undefined}
        vertical={active ? verticalById.get(active.vertical_id) : undefined}
        reviewer={active?.reviewed_by_id ? userById.get(active.reviewed_by_id) : undefined}
      />
    </div>
  );
}
