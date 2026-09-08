import * as React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches any render-time crash below it and shows a readable message instead
 * of a blank white page, which tells you nothing about what actually broke.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Keep the full detail in the console for debugging.
    console.error("Unhandled UI error:", error, info);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h1 className="text-lg font-semibold text-foreground">Something broke on this page</h1>
        <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
          The rest of the app is fine — only this screen failed to render. The technical detail is below
          and in your browser console.
        </p>
        <pre className="mt-4 max-w-xl overflow-x-auto rounded-lg border border-border bg-muted/40 p-3 text-left text-xs text-muted-foreground">
          {error.message}
        </pre>
        <div className="mt-5 flex gap-2">
          <Button onClick={() => window.location.reload()}>
            <RotateCcw className="h-4 w-4" />
            Reload page
          </Button>
          <Button variant="outline" onClick={() => this.setState({ error: null })}>
            Try again
          </Button>
        </div>
      </div>
    );
  }
}
