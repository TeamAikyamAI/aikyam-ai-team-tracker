import * as React from "react";
import { Plus, Users as UsersIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { RoleBadge } from "@/components/common/RoleBadge";
import { UserFormDialog } from "@/components/admin/UserFormDialog";
import { useUsers } from "@/hooks/useUsers";
import { useVerticals } from "@/hooks/useVerticals";
import { initials } from "@/lib/utils";
import type { User } from "@/types";

export function UsersTab() {
  const { data: users, isLoading } = useUsers();
  const { data: verticals } = useVerticals();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<User | null>(null);

  const userById = React.useMemo(() => new Map((users ?? []).map((u) => [u.id, u])), [users]);
  const verticalById = React.useMemo(() => new Map((verticals ?? []).map((v) => [v.id, v])), [verticals]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{users?.length ?? 0} users across the team.</p>
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setDialogOpen(true);
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          Add user
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && (!users || users.length === 0) && (
        <EmptyState icon={<UsersIcon className="h-6 w-6" />} title="No users yet" description="Add the first team member to get started." />
      )}

      {!isLoading && users && users.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Reports to</TableHead>
                <TableHead>Vertical</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => {
                const manager = u.reports_to_id ? userById.get(u.reports_to_id) : null;
                const vertical = u.vertical_id ? verticalById.get(u.vertical_id) : null;
                return (
                  <TableRow key={u.id}>
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="bg-primary/10 text-xs text-primary">{initials(u.name)}</AvatarFallback>
                        </Avatar>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{u.name}</p>
                          <p className="truncate text-xs text-muted-foreground">{u.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <RoleBadge role={u.role} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {manager ? manager.name : u.external_manager_email || "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{vertical?.name ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "success" : "secondary"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditing(u);
                          setDialogOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <UserFormDialog open={dialogOpen} onOpenChange={setDialogOpen} user={editing} />
    </div>
  );
}
