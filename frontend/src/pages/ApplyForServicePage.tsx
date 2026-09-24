import * as React from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Loader2, Send, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { FileDropzone } from "@/components/common/FileDropzone";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useVerticals } from "@/hooks/useVerticals";
import { useCreateRequest } from "@/hooks/useRequests";
import { useUserDirectory } from "@/hooks/useUsers";
import { usePublicSettings } from "@/hooks/useSettings";
import { useAuth } from "@/context/AuthContext";
import {
  RecipientPicker,
  emptyRecipients,
  toFormValue,
  type RecipientValue,
} from "@/components/requests/RecipientPicker";
import { apiErrorMessage } from "@/lib/api";

export default function ApplyForServicePage() {
  const navigate = useNavigate();
  const { data: verticals, isLoading: verticalsLoading } = useVerticals();
  const { data: directory } = useUserDirectory();
  const { settings } = usePublicSettings();
  const { user } = useAuth();
  const createRequest = useCreateRequest();

  const [verticalId, setVerticalId] = React.useState<string>("");
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [fileTouched, setFileTouched] = React.useState(false);
  const [submitted, setSubmitted] = React.useState(false);
  const [extraTo, setExtraTo] = React.useState<RecipientValue>(emptyRecipients);
  const [extraCc, setExtraCc] = React.useState<RecipientValue>(emptyRecipients);

  const canSubmit = Boolean(verticalId) && title.trim().length > 0 && Boolean(file);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFileTouched(true);
    if (!file) {
      toast.error("Please attach the signed BRD before submitting.");
      return;
    }
    if (!verticalId || !title.trim()) return;

    const form = new FormData();
    form.append("vertical_id", verticalId);
    form.append("title", title.trim());
    if (description.trim()) form.append("description", description.trim());
    const to = toFormValue(extraTo);
    const cc = toFormValue(extraCc);
    if (to) form.append("extra_to", to);
    if (cc) form.append("extra_cc", cc);
    form.append("brd_file", file);

    try {
      await createRequest.mutateAsync(form);
      toast.success("Service request submitted", {
        description: "The AI & Automation team will review your BRD shortly.",
      });
      setSubmitted(true);
    } catch (err) {
      toast.error("Couldn't submit your request", { description: apiErrorMessage(err) });
    }
  }

  if (submitted) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-success/15 text-success"
        >
          <CheckCircle2 className="h-7 w-7" />
        </motion.div>
        <h2 className="text-lg font-semibold text-foreground">Request submitted</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your service request and BRD have been sent for review. You can track its status from the queue once
          it's approved.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={() => navigate("/queue")}>
            View project queue
          </Button>
          <Button
            onClick={() => {
              setSubmitted(false);
              setVerticalId("");
              setTitle("");
              setDescription("");
              setFile(null);
              setFileTouched(false);
            }}
          >
            Submit another request
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Apply for Service"
        description="File a new automation or AI request with your vertical head's signed BRD."
      />

      <div className="mb-5 flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <p className="text-sm text-foreground">
          A <strong>BRD (Business Requirement Document) signed by your vertical head</strong> is mandatory for
          every request. Submissions without a signed BRD attached cannot be processed.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <Label>Vertical</Label>
              {verticalsLoading ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <Select value={verticalId} onValueChange={setVerticalId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your business vertical" />
                  </SelectTrigger>
                  <SelectContent>
                    {(verticals ?? [])
                      .filter((v) => v.is_active !== false)
                      .map((v) => (
                        <SelectItem key={v.id} value={String(v.id)}>
                          {v.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="title">Request title</Label>
              <Input
                id="title"
                placeholder="e.g. Automate daily reconciliation report"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Briefly describe the problem, current process, and desired outcome…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={5}
              />
            </div>

            <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-4">
              <div>
                <p className="text-sm font-medium text-foreground">Who else should be kept in the loop?</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Optional. The AI team and your vertical head are always included — this is for anyone
                  else on your side. Whoever you pick stays on every email about this request: when it
                  is submitted, when it is decided, and when it is delivered.
                </p>
              </div>

              <div className="space-y-1.5">
                <Label>Also address to</Label>
                <RecipientPicker
                  users={directory ?? []}
                  value={extraTo}
                  onChange={setExtraTo}
                  domain={settings.email_domain}
                  label="the To line"
                  excludeUserId={user?.id}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Copy in</Label>
                <RecipientPicker
                  users={directory ?? []}
                  value={extraCc}
                  onChange={setExtraCc}
                  domain={settings.email_domain}
                  label="the Cc line"
                  excludeUserId={user?.id}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>
                Signed BRD <span className="text-destructive">*</span>
              </Label>
              <FileDropzone
                file={file}
                onChange={(f) => {
                  setFile(f);
                  setFileTouched(true);
                }}
                error={fileTouched && !file}
              />
              {fileTouched && !file && (
                <p className="flex items-center gap-1.5 text-xs text-destructive">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  A signed BRD file is required — submission is disabled until one is attached.
                </p>
              )}
            </div>

            <Button type="submit" size="lg" className="w-full" disabled={!canSubmit || createRequest.isPending}>
              {createRequest.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit request
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
