import * as React from "react";
import { Loader2, Pencil } from "lucide-react";
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
import { useStatuses } from "@/hooks/useStatuses";
import { useVerticals } from "@/hooks/useVerticals";
import { useUsers } from "@/hooks/useUsers";
import { useUpdateProject } from "@/hooks/useProjects";
import { apiErrorMessage } from "@/lib/api";
import type { Project } from "@/types";

export function EditProjectDialog({ project }: { project: Project }) {
  const [open, setOpen] = React.useState(false);
  const { data: statuses } = useStatuses();
  const { data: verticals } = useVerticals();
  const { data: users } = useUsers();
  const updateProject = useUpdateProject();

  const [name, setName] = React.useState(project.name);
  const [description, setDescription] = React.useState(project.description ?? "");
  const [statusId, setStatusId] = React.useState(String(project.status_id));
  const [verticalId, setVerticalId] = React.useState(String(project.vertical_id));
  const [assignedBy, setAssignedBy] = React.useState(project.assigned_by ?? "");
  const [assignedOn, setAssignedOn] = React.useState<string | null>(project.assigned_on);
  const [remarks, setRemarks] = React.useState(project.remarks ?? "");
  const [ownerIds, setOwnerIds] = React.useState<number[]>(project.owner_ids ?? []);
  const [targetDate, setTargetDate] = React.useState<string | null>(project.target_date);
  const [actualCompletionDate, setActualCompletionDate] = React.useState<string | null>(
    project.actual_completion_date
  );

  React.useEffect(() => {
    if (open) {
      setName(project.name);
      setDescription(project.description ?? "");
      setStatusId(String(project.status_id));
      setVerticalId(String(project.vertical_id));
      setAssignedBy(project.assigned_by ?? "");
      setAssignedOn(project.assigned_on);
      setRemarks(project.remarks ?? "");
      setOwnerIds(project.owner_ids ?? []);
      setTargetDate(project.target_date);
      setActualCompletionDate(project.actual_completion_date);
    }
  }, [open, project]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateProject.mutateAsync({
        id: project.id,
        payload: {
          name: name.trim(),
          description: description.trim() || undefined,
          status_id: Number(statusId),
          vertical_id: Number(verticalId),
          owner_ids: ownerIds,
          assigned_by: assignedBy.trim() || null,
          assigned_on: assignedOn,
          remarks: remarks.trim() || null,
          target_date: targetDate,
          actual_completion_date: actualCompletionDate,
        },
      });
      toast.success("Project updated");
      setOpen(false);
    } catch (err) {
      toast.error("Couldn't update project", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit project</DialogTitle>
          <DialogDescription>Update the vertical, status, ownership, assignment details or dates.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="edit-name">Name</Label>
            <Input id="edit-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-desc">Description</Label>
            <Textarea id="edit-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Vertical</Label>
              <Select value={verticalId} onValueChange={setVerticalId}>
                <SelectTrigger>
                  <SelectValue />
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
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(statuses ?? [])
                    .filter((s) => s.is_active !== false || s.id === project.status_id)
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
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit-assigned-by">Assigned by</Label>
              <Input id="edit-assigned-by" value={assignedBy} onChange={(e) => setAssignedBy(e.target.value)} maxLength={120} placeholder="Who asked for it" />
            </div>
            <div className="space-y-1.5">
              <Label>Date of assignment</Label>
              <DatePicker value={assignedOn} onChange={setAssignedOn} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Owners</Label>
            <MultiUserSelect users={users ?? []} value={ownerIds} onChange={setOwnerIds} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Target date</Label>
              <DatePicker value={targetDate} onChange={setTargetDate} />
            </div>
            <div className="space-y-1.5">
              <Label>Actual completion</Label>
              <DatePicker value={actualCompletionDate} onChange={setActualCompletionDate} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-remarks">Remarks</Label>
            <Textarea id="edit-remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={2} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={updateProject.isPending || !name.trim()}>
              {updateProject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
