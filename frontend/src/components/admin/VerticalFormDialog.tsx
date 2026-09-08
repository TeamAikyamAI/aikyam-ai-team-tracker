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
import { useCreateVertical, useUpdateVertical } from "@/hooks/useVerticals";
import { apiErrorMessage } from "@/lib/api";
import type { Vertical } from "@/types";

interface VerticalFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vertical?: Vertical | null;
}

export function VerticalFormDialog({ open, onOpenChange, vertical }: VerticalFormDialogProps) {
  const isEdit = Boolean(vertical);
  const createVertical = useCreateVertical();
  const updateVertical = useUpdateVertical();

  const [name, setName] = React.useState("");
  const [headName, setHeadName] = React.useState("");
  const [headEmail, setHeadEmail] = React.useState("");
  const [isActive, setIsActive] = React.useState(true);

  React.useEffect(() => {
    if (open) {
      setName(vertical?.name ?? "");
      setHeadName(vertical?.head_name ?? "");
      setHeadEmail(vertical?.head_email ?? "");
      setIsActive(vertical?.is_active ?? true);
    }
  }, [open, vertical]);

  const saving = createVertical.isPending || updateVertical.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (isEdit && vertical) {
        await updateVertical.mutateAsync({
          id: vertical.id,
          payload: { name: name.trim(), head_name: headName.trim(), head_email: headEmail.trim(), is_active: isActive },
        });
        toast.success("Vertical updated");
      } else {
        await createVertical.mutateAsync({ name: name.trim(), head_name: headName.trim(), head_email: headEmail.trim() });
        toast.success("Vertical created");
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(isEdit ? "Couldn't update vertical" : "Couldn't create vertical", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit vertical" : "Add a vertical"}</DialogTitle>
          <DialogDescription>Business verticals group projects and requests by function.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="v-name">Name</Label>
            <Input id="v-name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus placeholder="e.g. Broking & Clearing" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="v-head-name">Vertical head name</Label>
            <Input id="v-head-name" value={headName} onChange={(e) => setHeadName(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="v-head-email">Vertical head email</Label>
            <Input id="v-head-email" type="email" value={headEmail} onChange={(e) => setHeadEmail(e.target.value)} required />
          </div>
          {isEdit && (
            <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
              <Label htmlFor="v-active">Active</Label>
              <Switch id="v-active" checked={isActive} onCheckedChange={setIsActive} />
            </div>
          )}
          <DialogFooter>
            <Button type="submit" disabled={saving || !name.trim() || !headName.trim() || !headEmail.trim()}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? "Save changes" : "Create vertical"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
