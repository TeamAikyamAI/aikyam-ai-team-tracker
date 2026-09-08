import * as React from "react";
import { toast } from "sonner";
import { Loader2, Save, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useCreateUpdate, useQuickFill } from "@/hooks/useUpdates";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export function AddUpdateForm({ projectId }: { projectId: number }) {
  const [rawBullets, setRawBullets] = React.useState("");
  const [plan, setPlan] = React.useState("");
  const [progress, setProgress] = React.useState("");
  const [problem, setProblem] = React.useState("");
  const [draftApplied, setDraftApplied] = React.useState(false);

  const quickFill = useQuickFill();
  const createUpdate = useCreateUpdate();

  async function handleQuickFill() {
    if (!rawBullets.trim()) {
      toast.error("Type a few rough bullet notes first.");
      return;
    }
    try {
      const result = await quickFill.mutateAsync({ bullets: rawBullets.trim() });
      setPlan(result.plan ?? "");
      setProgress(result.progress ?? "");
      setProblem(result.problem ?? "");
      setDraftApplied(true);
      toast.success("Draft generated — review and edit before saving", {
        description: "Nothing has been saved yet.",
      });
    } catch (err) {
      toast.error("Quick-fill failed", { description: apiErrorMessage(err) });
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!plan.trim() && !progress.trim() && !problem.trim() && !rawBullets.trim()) {
      toast.error("Add at least one field before saving.");
      return;
    }
    try {
      await createUpdate.mutateAsync({
        project_id: projectId,
        plan: plan.trim() || undefined,
        progress: progress.trim() || undefined,
        problem: problem.trim() || undefined,
        raw_bullets: rawBullets.trim() || undefined,
      });
      toast.success("Update saved to the project log");
      setRawBullets("");
      setPlan("");
      setProgress("");
      setProblem("");
      setDraftApplied(false);
    } catch (err) {
      toast.error("Couldn't save update", { description: apiErrorMessage(err) });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add an update</CardTitle>
        <CardDescription>
          Jot rough notes and let AI Quick-Fill draft Plan / Progress / Problem — then review and save.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="raw-bullets">Rough notes</Label>
            <Textarea
              id="raw-bullets"
              placeholder={"e.g.\n- finished data pipeline\n- vendor API still flaky\n- next: build retry logic"}
              value={rawBullets}
              onChange={(e) => setRawBullets(e.target.value)}
              rows={3}
            />
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleQuickFill}
                disabled={quickFill.isPending}
              >
                {quickFill.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                )}
                AI Quick-Fill
              </Button>
            </div>
          </div>

          <Separator />

          <div
            className={cn(
              "space-y-4 rounded-lg transition-colors",
              draftApplied && "-m-3 border border-primary/25 bg-primary/[0.03] p-3"
            )}
          >
            {draftApplied && (
              <p className="flex items-center gap-1.5 text-xs font-medium text-primary">
                <Sparkles className="h-3.5 w-3.5" />
                AI draft applied below — review and edit before saving, nothing is saved yet.
              </p>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="plan">Plan</Label>
              <Textarea id="plan" value={plan} onChange={(e) => setPlan(e.target.value)} rows={2} placeholder="What's planned next…" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="progress">Progress</Label>
              <Textarea
                id="progress"
                value={progress}
                onChange={(e) => setProgress(e.target.value)}
                rows={2}
                placeholder="What's been done since the last update…"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="problem">Problem</Label>
              <Textarea
                id="problem"
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
                rows={2}
                placeholder="Any blockers or risks…"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={createUpdate.isPending}>
              {createUpdate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save update
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
