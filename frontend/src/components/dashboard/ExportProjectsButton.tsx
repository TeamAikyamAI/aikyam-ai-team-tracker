import * as React from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { downloadFile, apiErrorMessage } from "@/lib/api";

/** Downloads every project as an Excel workbook - one sheet per status,
 *  the same layout as the team's original Weekly_Update.xlsx. */
export function ExportProjectsButton() {
  const [busy, setBusy] = React.useState(false);

  async function run() {
    setBusy(true);
    try {
      await downloadFile("/projects/export.xlsx", "Weekly_Update.xlsx");
      toast.success("Excel export downloaded");
    } catch (err) {
      toast.error("Couldn't export", { description: apiErrorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="outline" onClick={() => void run()} disabled={busy} aria-label="Export projects to Excel">
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
      Export Excel
    </Button>
  );
}
