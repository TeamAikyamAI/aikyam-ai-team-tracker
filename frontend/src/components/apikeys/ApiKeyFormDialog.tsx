import * as React from "react";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { useProjects } from "@/hooks/useProjects";
import {
  useApiProviders, useCreateApiKey, useCreateApiProvider, useUpdateApiKey,
} from "@/hooks/useApiKeys";
import { useCan } from "@/hooks/usePermissions";
import { apiErrorMessage } from "@/lib/api";
import type { ApiKeyEntry } from "@/types";

const NO_PROJECT = "__label__";
/** A key can be planned before anyone has settled which vendor it comes from. */
const NO_PROVIDER = "__undecided__";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry?: ApiKeyEntry;
}

export function ApiKeyFormDialog({ open, onOpenChange, entry }: Props) {
  const editing = Boolean(entry);
  const { data: projects } = useProjects();
  const { data: providers } = useApiProviders();
  const createKey = useCreateApiKey();
  const updateKey = useUpdateApiKey();
  const createProvider = useCreateApiProvider();
  const canAdmin = useCan()("admin_panel");

  const [projectChoice, setProjectChoice] = React.useState<string>(NO_PROJECT);
  const [projectLabel, setProjectLabel] = React.useState("");
  const [providerId, setProviderId] = React.useState<string>("");
  const [purpose, setPurpose] = React.useState("");
  const [expiresOn, setExpiresOn] = React.useState<string | null>(null);
  const [accountEmail, setAccountEmail] = React.useState("");
  const [status, setStatus] = React.useState("active");
  const [notes, setNotes] = React.useState("");
  const [newProvider, setNewProvider] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setProjectChoice(entry?.project_id ? String(entry.project_id) : NO_PROJECT);
    setProjectLabel(entry?.project_label ?? "");
    setProviderId(entry?.provider_id ? String(entry.provider_id) : entry ? NO_PROVIDER : "");
    setPurpose(entry?.purpose ?? "");
    setExpiresOn(entry?.expires_on ?? null);
    setAccountEmail(entry?.account_email ?? "");
    setStatus(entry?.status ?? "active");
    setNotes(entry?.notes ?? "");
    setNewProvider("");
  }, [open, entry]);

  const linked = projectChoice !== NO_PROJECT;
  const undecided = providerId === NO_PROVIDER;
  // Only a pending key may have no provider; an active one came from somewhere.
  const providerOk = undecided ? status === "pending" : Boolean(providerId);
  const canSave = providerOk && (linked || projectLabel.trim().length > 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSave) return;
    const payload = {
      project_id: linked ? Number(projectChoice) : null,
      project_label: linked ? null : projectLabel.trim(),
      provider_id: undecided ? null : Number(providerId),
      purpose: purpose.trim() || null,
      expires_on: expiresOn,
      account_email: accountEmail.trim() || null,
      status,
      notes: notes.trim() || null,
    };
    try {
      if (entry) await updateKey.mutateAsync({ id: entry.id, payload });
      else await createKey.mutateAsync(payload);
      toast.success(entry ? "Entry updated" : "Key added to the register");
      onOpenChange(false);
    } catch (err) {
      toast.error("Couldn't save it", { description: apiErrorMessage(err) });
    }
  }

  const busy = createKey.isPending || updateKey.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit register entry" : "Add a key to the register"}</DialogTitle>
          <DialogDescription>
            Record what the key is for and when it lapses. Never paste the key itself — there is no
            field for it, and it must not live in a web page.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Project</Label>
            <Select value={projectChoice} onValueChange={setProjectChoice}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_PROJECT}>Not a tracker project — type a name</SelectItem>
                {(projects ?? []).map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!linked && (
              <Input
                value={projectLabel}
                onChange={(e) => setProjectLabel(e.target.value)}
                placeholder="e.g. Bulk email, FD_Rate"
                aria-label="Name of the work this key belongs to"
              />
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Provider</Label>
            <Select value={providerId} onValueChange={setProviderId}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {(providers ?? []).filter((p) => p.is_active || String(p.id) === providerId).map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                ))}
                <SelectItem value={NO_PROVIDER}>Not decided yet</SelectItem>
              </SelectContent>
            </Select>
            {undecided && status !== "pending" && (
              <p className="text-xs text-destructive">
                Set the status to Pending — a key already in use came from somewhere.
              </p>
            )}
            {canAdmin && (
              <div className="flex items-center gap-1.5 pt-1">
                <Input
                  value={newProvider}
                  onChange={(e) => setNewProvider(e.target.value)}
                  placeholder="New provider…"
                  className="h-8 text-xs"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  aria-label="Add provider"
                  disabled={!newProvider.trim() || createProvider.isPending}
                  onClick={async () => {
                    try {
                      const made = await createProvider.mutateAsync(newProvider.trim());
                      setProviderId(String(made.id));
                      setNewProvider("");
                      toast.success(`${made.name} added`);
                    } catch (err) {
                      toast.error("Couldn't add it", { description: apiErrorMessage(err) });
                    }
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="key-purpose">Purpose</Label>
            <Textarea
              id="key-purpose"
              rows={2}
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="e.g. For the STT, For the AI agent fallback"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Expiry date</Label>
              <DatePicker value={expiresOn} onChange={setExpiresOn} />
              <p className="text-xs text-muted-foreground">Leave empty if it never expires.</p>
            </div>
            <div className="space-y-1.5">
              <Label>Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="pending">Pending — not issued yet</SelectItem>
                  <SelectItem value="revoked">Revoked — no longer in use</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="key-email">Account it sits on</Label>
            <Input
              id="key-email"
              value={accountEmail}
              onChange={(e) => setAccountEmail(e.target.value)}
              placeholder="Whoever has to renew it will need this"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="key-notes">Notes</Label>
            <Textarea id="key-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>

          <DialogFooter>
            <Button type="submit" disabled={!canSave || busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? "Save changes" : "Add to register"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
