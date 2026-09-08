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
import { Switch } from "@/components/ui/switch";
import { useCreateStatus, useUpdateStatus } from "@/hooks/useStatuses";
import { apiErrorMessage } from "@/lib/api";
import type { Status } from "@/types";

interface StatusFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  status?: Status | null;
  nextSortOrder: number;
}

const PRESET_COLORS = ["#6366f1", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b", "#ec4899"];

export function StatusFormDialog({ open, onOpenChange, status, nextSortOrder }: StatusFormDialogProps) {
  const isEdit = Boolean(status);
  const createStatus = useCreateStatus();
  const updateStatus = useUpdateStatus();

  const [name, setName] = React.useState("");
  const [color, setColor] = React.useState("#6366f1");
  const [sortOrder, setSortOrder] = React.useState(0);
  const [isTerminal, setIsTerminal] = React.useState(false);
  const [isActive, setIsActive] = React.useState(true);
  const colorInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setName(status?.name ?? "");
      setColor(status?.color ?? "#6366f1");
      setSortOrder(status?.sort_order ?? nextSortOrder);
      setIsTerminal(status?.is_terminal ?? false);
      setIsActive(status?.is_active ?? true);
    }
  }, [open, status, nextSortOrder]);

  const saving = createStatus.isPending || updateStatus.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (isEdit && status) {
        await updateStatus.mutateAsync({
          id: status.id,
          payload: { name: name.trim(), color, sort_order: sortOrder, is_terminal: isTerminal, is_active: isActive },
        });
        toast.success("Status updated");
      } else {
        await createStatus.mutateAsync({ name: name.trim(), color, sort_order: sortOrder, is_terminal: isTerminal });
        toast.success("Status created");
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(isEdit ? "Couldn't update status" : "Couldn't create status", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit status" : "Add a status"}</DialogTitle>
          <DialogDescription>Statuses power the kanban board columns and badge colors.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="s-name">Name</Label>
            <Input id="s-name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus placeholder="e.g. In Progress" />
          </div>

          <div className="space-y-1.5">
            <Label>Color</Label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => colorInputRef.current?.click()}
                className="h-9 w-9 shrink-0 rounded-md border border-input shadow-sm"
                style={{ backgroundColor: color }}
                aria-label="Pick color"
              />
              <input
                ref={colorInputRef}
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="sr-only"
              />
              <Input value={color} onChange={(e) => setColor(e.target.value)} className="font-mono" />
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className="h-6 w-6 rounded-full border border-border/50 transition-transform hover:scale-110"
                  style={{ backgroundColor: c }}
                  aria-label={c}
                />
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="s-sort">Sort order</Label>
            <Input
              id="s-sort"
              type="number"
              value={sortOrder}
              onChange={(e) => setSortOrder(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">Determines column order on the kanban board.</p>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
            <div>
              <Label htmlFor="s-terminal">Terminal status</Label>
              <p className="text-xs text-muted-foreground">Marks a project as finished (e.g. Completed, Cancelled).</p>
            </div>
            <Switch id="s-terminal" checked={isTerminal} onCheckedChange={setIsTerminal} />
          </div>

          {isEdit && (
            <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
              <Label htmlFor="s-active">Active</Label>
              <Switch id="s-active" checked={isActive} onCheckedChange={setIsActive} />
            </div>
          )}

          <DialogFooter>
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? "Save changes" : "Create status"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
