import * as React from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { UserCombobox } from "@/components/common/UserCombobox";
import { useCreateUser, useUpdateUser, useUsers } from "@/hooks/useUsers";
import { useVerticals } from "@/hooks/useVerticals";
import { apiErrorMessage } from "@/lib/api";
import type { Role, User } from "@/types";

interface UserFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null;
}

const ROLES: Role[] = ["admin", "member", "requestor"];

export function UserFormDialog({ open, onOpenChange, user }: UserFormDialogProps) {
  const isEdit = Boolean(user);
  const { data: allUsers } = useUsers();
  const { data: verticals } = useVerticals();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [role, setRole] = React.useState<Role>("member");
  const [reportsToId, setReportsToId] = React.useState<number | null>(null);
  const [verticalId, setVerticalId] = React.useState<number | null>(null);
  const [externalManagerEmail, setExternalManagerEmail] = React.useState("");
  const [isActive, setIsActive] = React.useState(true);

  React.useEffect(() => {
    if (open) {
      setName(user?.name ?? "");
      setEmail(user?.email ?? "");
      setPassword("");
      setRole(user?.role ?? "member");
      setReportsToId(user?.reports_to_id ?? null);
      setVerticalId(user?.vertical_id ?? null);
      setExternalManagerEmail(user?.external_manager_email ?? "");
      setIsActive(user?.is_active ?? true);
    }
  }, [open, user]);

  const saving = createUser.isPending || updateUser.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (isEdit && user) {
        await updateUser.mutateAsync({
          id: user.id,
          payload: {
            name: name.trim(),
            email: email.trim(),
            role,
            reports_to_id: reportsToId,
            vertical_id: role === "requestor" ? verticalId : null,
            external_manager_email: reportsToId ? null : externalManagerEmail.trim() || null,
            is_active: isActive,
            ...(password.trim() ? { password: password.trim() } : {}),
          },
        });
        toast.success("User updated");
      } else {
        await createUser.mutateAsync({
          name: name.trim(),
          email: email.trim(),
          password: password.trim(),
          role,
          reports_to_id: reportsToId,
          vertical_id: role === "requestor" ? verticalId : null,
          external_manager_email: reportsToId ? null : externalManagerEmail.trim() || null,
        });
        toast.success("User created");
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(isEdit ? "Couldn't update user" : "Couldn't create user", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit user" : "Add a new user"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update this person's details, role, or reporting chain." : "Create a login for a new team member or requestor."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="u-name">Full name</Label>
              <Input id="u-name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="u-email">Email</Label>
              <Input id="u-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="u-password">{isEdit ? "New password (leave blank to keep current)" : "Password"}</Label>
            <Input
              id="u-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required={!isEdit}
              placeholder={isEdit ? "••••••••" : undefined}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select value={role} onValueChange={(v) => setRole(v as Role)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r} value={r} className="capitalize">
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Reports to</Label>
            <UserCombobox
              users={allUsers ?? []}
              value={reportsToId}
              onChange={setReportsToId}
              excludeId={user?.id}
              placeholder="Select their manager in the system…"
            />
            <p className="text-xs text-muted-foreground">
              Builds the reporting / org chart. Leave empty for the top of a chain.
            </p>
          </div>

          {!reportsToId && (
            <div className="space-y-1.5">
              <Label htmlFor="u-ext-manager">External manager email</Label>
              <Input
                id="u-ext-manager"
                type="email"
                value={externalManagerEmail}
                onChange={(e) => setExternalManagerEmail(e.target.value)}
                placeholder="For someone outside the system (e.g. your own boss)"
              />
            </div>
          )}

          {role === "requestor" && (
            <div className="space-y-1.5">
              <Label>Vertical</Label>
              <Select
                value={verticalId != null ? String(verticalId) : ""}
                onValueChange={(v) => setVerticalId(v ? Number(v) : null)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select vertical" />
                </SelectTrigger>
                <SelectContent>
                  {(verticals ?? []).map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      {v.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {isEdit && (
            <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
              <div>
                <Label htmlFor="u-active">Active</Label>
                <p className="text-xs text-muted-foreground">Inactive users cannot sign in.</p>
              </div>
              <Switch id="u-active" checked={isActive} onCheckedChange={setIsActive} />
            </div>
          )}

          <DialogFooter>
            <Button type="submit" disabled={saving || !name.trim() || !email.trim()}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? "Save changes" : "Create user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
