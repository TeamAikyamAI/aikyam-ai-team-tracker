import * as React from "react";
import { toast } from "sonner";
import { CheckCircle2, Download, FileText, Loader2, PauseCircle, XCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { Separator } from "@/components/ui/separator";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { useStatuses } from "@/hooks/useStatuses";
import { useReviewRequest } from "@/hooks/useRequests";
import { downloadFile, apiErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { ServiceRequest, User, Vertical } from "@/types";

interface RequestDetailDialogProps {
  request: ServiceRequest | null;
  onOpenChange: (open: boolean) => void;
  requestor?: User;
  vertical?: Vertical;
  reviewer?: User;
}

type Decision = "approved" | "rejected" | "on_hold" | null;

export function RequestDetailDialog({ request, onOpenChange, requestor, vertical, reviewer }: RequestDetailDialogProps) {
  const { data: statuses } = useStatuses();
  const reviewRequest = useReviewRequest();

  const [decision, setDecision] = React.useState<Decision>(null);
  const [notes, setNotes] = React.useState("");
  const [seedStatusId, setSeedStatusId] = React.useState("");
  const [targetDate, setTargetDate] = React.useState<string | null>(null);
  const [downloading, setDownloading] = React.useState(false);

  React.useEffect(() => {
    setDecision(null);
    setNotes("");
    setSeedStatusId("");
    setTargetDate(null);
  }, [request?.id]);

  if (!request) return null;

  const isPending = request.status === "submitted" || request.status === "under_review";

  async function openBrd() {
    if (!request) return;
    setDownloading(true);
    try {
      await downloadFile(`/requests/${request.id}/brd`, request.brd_filename ?? "brd");
    } catch (err) {
      toast.error("Couldn't download the BRD", { description: apiErrorMessage(err) });
    } finally {
      setDownloading(false);
    }
  }

  async function submitDecision() {
    if (!decision || !request) return;
    if (decision === "approved" && !seedStatusId) {
      toast.error("Choose the starting status for the new project.");
      return;
    }
    try {
      await reviewRequest.mutateAsync({
        id: request.id,
        payload: {
          decision,
          review_notes: notes.trim() || undefined,
          status_id: decision === "approved" ? Number(seedStatusId) : undefined,
          target_date: decision === "approved" && targetDate ? targetDate : undefined,
        },
      });
      toast.success(
        decision === "approved"
          ? "Request approved — a new project has been created"
          : decision === "rejected"
          ? "Request rejected"
          : "Request put on hold"
      );
      onOpenChange(false);
    } catch (err) {
      toast.error("Couldn't submit review", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Dialog open={Boolean(request)} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle className="truncate">{request.title}</DialogTitle>
            <RequestStatusBadge status={request.status} />
          </div>
          <DialogDescription>
            Submitted {formatDateTime(request.created_at)} by {requestor?.name ?? "Unknown"} · {vertical?.name ?? "—"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {request.description && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
              <p className="whitespace-pre-wrap text-sm text-foreground/90">{request.description}</p>
            </div>
          )}

          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Signed BRD
            </p>
            {request.brd_filename ? (
              <button
                type="button"
                onClick={() => void openBrd()}
                disabled={downloading}
                className="flex w-full items-center gap-2 rounded-lg border border-border bg-accent/30 px-3 py-2.5 text-left text-sm font-medium text-foreground transition-colors hover:bg-accent/60 disabled:opacity-60"
              >
                <FileText className="h-4 w-4 shrink-0 text-primary" />
                <span className="truncate">{request.brd_filename}</span>
                {downloading ? (
                  <Loader2 className="ml-auto h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
                ) : (
                  <Download className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
              </button>
            ) : (
              <p className="text-sm text-muted-foreground">No file on record.</p>
            )}
          </div>

          {!isPending && (
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2.5 text-sm">
              <p className="text-muted-foreground">
                Reviewed by <span className="font-medium text-foreground">{reviewer?.name ?? "—"}</span> on{" "}
                {formatDateTime(request.reviewed_at)}
              </p>
              {request.review_notes && <p className="mt-1 text-foreground/90">&ldquo;{request.review_notes}&rdquo;</p>}
            </div>
          )}

          {isPending && (
            <>
              <Separator />
              <div className="space-y-3">
                <Label>Decision</Label>
                <div className="grid grid-cols-3 gap-2">
                  <Button
                    type="button"
                    variant={decision === "approved" ? "success" : "outline"}
                    size="sm"
                    onClick={() => setDecision("approved")}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Approve
                  </Button>
                  <Button
                    type="button"
                    variant={decision === "on_hold" ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => setDecision("on_hold")}
                  >
                    <PauseCircle className="h-3.5 w-3.5" />
                    On hold
                  </Button>
                  <Button
                    type="button"
                    variant={decision === "rejected" ? "destructive" : "outline"}
                    size="sm"
                    onClick={() => setDecision("rejected")}
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    Reject
                  </Button>
                </div>

                {decision === "approved" && (
                  <div className="space-y-3 rounded-lg border border-success/30 bg-success/5 p-3">
                    <p className="text-xs text-foreground">
                      Approving will immediately <strong>create a new project</strong> in the queue, linked back to
                      this request.
                    </p>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Starting status for new project</Label>
                      <Select value={seedStatusId} onValueChange={setSeedStatusId}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Select a status" />
                        </SelectTrigger>
                        <SelectContent>
                          {(statuses ?? [])
                            .sort((a, b) => a.sort_order - b.sort_order)
                            .map((s) => (
                              <SelectItem key={s.id} value={String(s.id)}>
                                {s.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Target date (optional)</Label>
                      <DatePicker value={targetDate} onChange={setTargetDate} className="h-8 text-xs" />
                    </div>
                  </div>
                )}

                <div className="space-y-1.5">
                  <Label className="text-xs">Review notes (optional)</Label>
                  <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Any context for the requestor…" />
                </div>
              </div>
            </>
          )}
        </div>

        {isPending && (
          <DialogFooter>
            <Button
              onClick={submitDecision}
              disabled={!decision || reviewRequest.isPending}
              variant={decision === "rejected" ? "destructive" : decision === "approved" ? "success" : "default"}
            >
              {reviewRequest.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Confirm {decision ? decision.replace("_", " ") : "decision"}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
