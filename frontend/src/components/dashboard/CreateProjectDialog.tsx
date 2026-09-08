import * as React from "react";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { MultiUserSelect } from "@/components/common/MultiUserSelect";
import { useVerticals } from "@/hooks/useVerticals";
import { useStatuses } from "@/hooks/useStatuses";
import { useUsers } from "@/hooks/useUsers";
import { useCreateProject } from "@/hooks/useProjects";
import { apiErrorMessage } from "@/lib/api";

export function CreateProjectDialog() {
  const [open, setOpen] = React.useState(false);
  const { data: verticals } = useVerticals();
  const { data: statuses } = useStatuses();
  const { data: users } = useUsers();
  const createProject = useCreateProject();

  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [verticalId, setVerticalId] = React.useState("");
  const [statusId, setStatusId] = React.useState("");
  const [ownerIds, setOwnerIds] = React.useState<number[]>([]);
  const [targetDate, setTargetDate] = React.useState<string | null>(null);
  const [assignedBy, setAssignedBy] = React.useState("");
  const [assignedOn, setAssignedOn] = React.useState<string | null>(null);
  const [remarks, setRemarks] = React.useState("");

  function reset() {
    setAssignedBy("");
    setAssignedOn(null);
    setRemarks("");
    setName("");
    setDescription("");
    setVerticalId("");
    setStatusId("");
    setOwnerIds([]);
    setTargetDate(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !verticalId || !statusId) return;
    try {
      await createProject.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        vertical_id: Number(verticalId),
        status_id: Number(statusId),
        owner_ids: ownerIds,
        target_date: targetDate ?? undefined,
        assigned_by: assignedBy.trim() || undefined,
        assigned_on: assignedOn ?? undefined,
        remarks: remarks.trim() || undefined,
      });
      toast.success("Project created");
      setOpen(false);
      reset();
    } catch (err) {
      toast.error("Couldn't create project", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" />
          New Project
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create a new project</DialogTitle>
          <DialogDescription>It will immediately appear in the queue and on the dashboard board.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="proj-name">Name</Label>
            <Input id="proj-name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="proj-desc">Description</Label>
            <Textarea id="proj-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Vertical</Label>
              <Select value={verticalId} onValueChange={setVerticalId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select" />
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
            <div className="space-y-1.5">
              <Label>Status</Label>
              <Select value={statusId} onValueChange={setStatusId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  {(statuses ?? [])
                    .filter((s) => s.is_active !== false)
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {s.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Owners</Label>
            <MultiUserSelect users={users ?? []} value={ownerIds} onChange={setOwnerIds} />
            <p className="text-xs text-muted-foreground">Leave empty to default to yourself.</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="proj-assigned-by">Assigned by</Label>
              <Input
                id="proj-assigned-by"
                value={assignedBy}
                onChange={(e) => setAssignedBy(e.target.value)}
                placeholder="Who asked for it"
                maxLength={120}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Date of assignment</Label>
              <DatePicker value={assignedOn} onChange={setAssignedOn} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Target date</Label>
            <DatePicker value={targetDate} onChange={setTargetDate} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="proj-remarks">Remarks</Label>
            <Textarea id="proj-remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={2} placeholder="Anything worth noting" />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createProject.isPending || !name.trim() || !verticalId || !statusId}>
              {createProject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Create project
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
