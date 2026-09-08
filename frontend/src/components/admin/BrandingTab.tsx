import * as React from "react";
import { Loader2, Trash2, Upload, ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useLogoMeta, useUploadLogo, useDeleteLogo, logoSrc } from "@/hooks/useBranding";
import { apiErrorMessage } from "@/lib/api";

const MAX_BYTES = 512 * 1024;
const ACCEPTED = ["image/svg+xml", "image/png"];

function prettySize(bytes: number) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

export function BrandingTab() {
  const { data: meta, isLoading } = useLogoMeta();
  const upload = useUploadLogo();
  const remove = useDeleteLogo();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    // Check locally first so an obvious mistake doesn't need a round trip.
    if (!ACCEPTED.includes(file.type)) {
      toast.error("Unsupported file type", { description: "The logo must be an SVG or PNG." });
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error("File is too large", {
        description: `That file is ${prettySize(file.size)}. The limit is 512 KB.`,
      });
      return;
    }
    try {
      await upload.mutateAsync(file);
      toast.success("Logo updated", { description: "It's live in the sidebar, login page and browser tab." });
    } catch (err) {
      toast.error("Couldn't update the logo", { description: apiErrorMessage(err) });
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleRemove() {
    try {
      await remove.mutateAsync();
      toast.success("Custom logo removed", { description: "Reverted to the default Aikyam mark." });
    } catch (err) {
      toast.error("Couldn't remove the logo", { description: apiErrorMessage(err) });
    }
  }

  return (
    <div className="max-w-2xl">
      <p className="mb-4 text-sm text-muted-foreground">
        The logo is stored in the database, so changing it here updates the sidebar, the login page and the
        browser tab icon straight away — no redeploy.
      </p>

      <Card>
        <CardContent className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center">
          <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-xl border border-border bg-[repeating-conic-gradient(hsl(var(--muted))_0_25%,transparent_0_50%)] bg-[length:16px_16px] p-3">
            {isLoading ? (
              <Skeleton className="h-full w-full rounded-lg" />
            ) : (
              <img src={logoSrc(meta)} alt="Current logo" className="max-h-full max-w-full object-contain" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-24" />
              </div>
            ) : (
              <>
                <p className="truncate text-sm font-medium text-foreground">{meta?.filename}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {meta?.has_custom ? "Uploaded" : "Built-in default"} ·{" "}
                  {meta ? prettySize(meta.size_bytes) : "—"} · {meta?.content_type}
                </p>
              </>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              <input
                ref={inputRef}
                type="file"
                accept="image/svg+xml,image/png"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
              <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
                {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                {meta?.has_custom ? "Replace logo" : "Upload logo"}
              </Button>
              {meta?.has_custom && (
                <Button
                  variant="outline"
                  onClick={() => setConfirmOpen(true)}
                  disabled={remove.isPending}
                >
                  {remove.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  Remove
                </Button>
              )}
            </div>

            <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
              <ImageIcon className="h-3.5 w-3.5" />
              SVG or PNG, up to 512 KB. A square-ish mark works best.
            </p>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Remove the uploaded logo?"
        description="The app will go back to the default Aikyam mark. You can upload a new one at any time."
        confirmLabel="Remove"
        destructive
        loading={remove.isPending}
        onConfirm={handleRemove}
      />
    </div>
  );
}
