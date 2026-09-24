import * as React from "react";
import { Download, KeyRound, Pencil, Plus, Trash2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { ApiKeyFormDialog } from "@/components/apikeys/ApiKeyFormDialog";
import { useApiKeys, useDeleteApiKey } from "@/hooks/useApiKeys";
import { apiErrorMessage, downloadFile } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ApiKeyEntry } from "@/types";

/** One phrase for each expiry state, used in the badge and nowhere else. */
function ExpiryBadge({ row }: { row: ApiKeyEntry }) {
  if (row.status === "revoked") return <Badge variant="outline">Revoked</Badge>;
  if (row.expiry_state === "none") return <span className="text-xs text-muted-foreground">No expiry date</span>;
  if (row.expiry_state === "expired") {
    const days = Math.abs(row.days_left ?? 0);
    return (
      <Badge className="bg-destructive/15 text-destructive hover:bg-destructive/15">
        Expired {days} day{days === 1 ? "" : "s"} ago
      </Badge>
    );
  }
  if (row.expiry_state === "soon") {
    return (
      <Badge className="bg-warning/15 text-warning hover:bg-warning/15">
        {row.days_left} day{row.days_left === 1 ? "" : "s"} left
      </Badge>
    );
  }
  return <span className="text-xs text-muted-foreground">{row.days_left} days left</span>;
}

export default function ApiKeysPage() {
  const { data: rows, isLoading } = useApiKeys();
  const deleteKey = useDeleteApiKey();
  const [search, setSearch] = React.useState("");
  const [editing, setEditing] = React.useState<ApiKeyEntry | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [confirming, setConfirming] = React.useState<ApiKeyEntry | null>(null);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    const all = rows ?? [];
    if (!q) return all;
    return all.filter((r) =>
      [r.project_name, r.provider_name, r.purpose, r.account_email]
        .some((v) => (v ?? "").toLowerCase().includes(q))
    );
  }, [rows, search]);

  const needsAttention = (rows ?? []).filter(
    (r) => r.expiry_state === "soon" || r.expiry_state === "expired"
  ).length;

  return (
    <div>
      <PageHeader
        title="API Key Register"
        description="Which provider's key each project uses, what it is for, and when it lapses."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await downloadFile("/api-keys/export.xlsx");
                } catch (err) {
                  toast.error("Couldn't export", { description: apiErrorMessage(err) });
                }
              }}
            >
              <Download className="h-4 w-4" />
              Export Excel
            </Button>
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" />
              Add key
            </Button>
          </div>
        }
      />

      <div className="mb-4 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        This is a register, not a vault. It records that a key exists and when it runs out — the key
        itself is never stored here.
      </div>

      {needsAttention > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm">
          <TriangleAlert className="h-4 w-4 shrink-0 text-warning" />
          <span>
            <strong>{needsAttention}</strong> key{needsAttention === 1 ? "" : "s"} expired or expiring
            within 30 days. These are listed in Monday's rollup too.
          </span>
        </div>
      )}

      <div className="mb-4">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search project, provider, purpose or account…"
          className="max-w-sm"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<KeyRound className="h-6 w-6" />}
          title={rows?.length ? "Nothing matches that search" : "No keys recorded yet"}
          description={
            rows?.length
              ? "Try a different word."
              : "Add the first one so the team knows what exists and what is about to lapse."
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Project</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Purpose</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">
                        {row.project_name}
                        {row.status === "pending" && (
                          <Badge variant="outline" className="ml-2">Pending</Badge>
                        )}
                      </TableCell>
                      <TableCell>{row.provider_name}</TableCell>
                      <TableCell className="max-w-[22rem] text-sm text-muted-foreground">
                        {row.purpose || "-"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm">
                            {row.expires_on ? formatDate(row.expires_on) : "-"}
                          </span>
                          <ExpiryBadge row={row} />
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {row.account_email || "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Edit the ${row.provider_name} key for ${row.project_name}`}
                            onClick={() => setEditing(row)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Delete the ${row.provider_name} key for ${row.project_name}`}
                            className="text-destructive"
                            onClick={() => setConfirming(row)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <ApiKeyFormDialog open={creating} onOpenChange={setCreating} />
      <ApiKeyFormDialog
        open={editing !== null}
        onOpenChange={(v) => !v && setEditing(null)}
        entry={editing ?? undefined}
      />

      <ConfirmDialog
        open={confirming !== null}
        onOpenChange={(v) => !v && setConfirming(null)}
        destructive
        title="Remove this entry?"
        description={
          confirming
            ? `The ${confirming.provider_name} key for ${confirming.project_name} stops being tracked. This does not touch the key itself at the provider.`
            : undefined
        }
        confirmLabel="Remove"
        loading={deleteKey.isPending}
        onConfirm={async () => {
          if (!confirming) return;
          try {
            await deleteKey.mutateAsync(confirming.id);
            toast.success("Entry removed");
            setConfirming(null);
          } catch (err) {
            toast.error("Couldn't remove it", { description: apiErrorMessage(err) });
          }
        }}
      />
    </div>
  );
}
