import * as React from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  file: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
  className?: string;
  error?: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileDropzone({ file, onChange, accept = ".pdf,.doc,.docx", className, error }: FileDropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) onChange(files[0]);
  };

  if (file) {
    return (
      <div
        className={cn(
          "flex items-center justify-between gap-3 rounded-lg border border-border bg-accent/40 px-4 py-3",
          className
        )}
      >
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-success/15 text-success">
            <FileText className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
            <p className="text-xs text-muted-foreground">{formatBytes(file.size)} &middot; attached</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            onChange(null);
            if (inputRef.current) inputRef.current.value = "";
          }}
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          aria-label="Remove file"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
        dragOver ? "border-primary bg-accent/50" : "border-border hover:border-primary/50 hover:bg-accent/20",
        error && "border-destructive/60 bg-destructive/5",
        className
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <UploadCloud className={cn("h-7 w-7", error ? "text-destructive" : "text-muted-foreground")} />
      <div>
        <p className="text-sm font-medium text-foreground">
          Click to upload <span className="font-normal text-muted-foreground">or drag and drop</span>
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">PDF or Word document, signed by the vertical head</p>
      </div>
    </label>
  );
}
