import * as React from "react";
import { Link } from "react-router-dom";
import { Download, FileStack, Inbox } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { downloadFile } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useRequests } from "@/hooks/useRequests";
import { useVerticals } from "@/hooks/useVerticals";
import { useCan } from "@/hooks/usePermissions";

const NEXT_STEP: Record<string, string> = {
  submitted: "With the AI team. They'll pick it up from the queue.",
  under_review: "The AI team is looking at it now.",
  approved: "Approved - it's on the board and in the queue.",
  rejected: "Not taken up. See the note below.",
  on_hold: "Paused for now. See the note below.",
};

export default function MyRequestsPage() {
  const { user } = useAuth();
  const { data: requests, isLoading } = useRequests();
  const { data: verticals } = useVerticals();
  const can = useCan();

  // Admins and members see every request through Requests Review; this page is
  // "what I asked for", so it stays scoped to the signed-in person either way.
  const mine = React.useMemo(
    () => (requests ?? []).filter((r) => r.requestor_id === user?.id),
    [requests, user]
  );

  const verticalName = (id: number) => verticals?.find((v) => v.id === id)?.name ?? "-";

  return (
    <div>
      <PageHeader
        title="My Requests"
        description="Everything you've submitted, and where each one has got to."
        actions={
          // Only offered to roles that may actually file one. Without this the
          // button survives revoking Apply for Service in the grid and lands
          // the person on a route that bounces them straight back.
          can("apply") ? (
            <Button asChild size="sm">
              <Link to="/apply">
                <FileStack className="mr-1.5 h-4 w-4" />
                New request
              </Link>
            </Button>
          ) : undefined
        }
      />

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      )}

      {!isLoading && mine.length === 0 && (
        <EmptyState
          icon={<Inbox className="h-6 w-6" />}
          title="You haven't submitted a request yet"
          description="Check the project queue to see what the team is already working on, then submit a request with a BRD signed by your vertical head."
        />
      )}

      <div className="space-y-3">
        {mine.map((r) => (
          <Card key={r.id}>
            <CardContent className="p-4">
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="font-medium leading-tight">{r.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {verticalName(r.vertical_id)} · submitted{" "}
                    {new Date(r.created_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <RequestStatusBadge status={r.status} />
              </div>

              {r.description && (
                <p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">{r.description}</p>
              )}

              <p className="mt-3 text-xs text-muted-foreground">{NEXT_STEP[r.status]}</p>

              {r.review_notes && (
                <p className="mt-2 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm">
                  <span className="font-medium">Note from the team: </span>
                  {r.review_notes}
                </p>
              )}

              {r.brd_filename && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 h-8 px-2 text-xs"
                  onClick={() =>
                    downloadFile(`/requests/${r.id}/brd`).catch(() => toast.error("Couldn't download the BRD"))
                  }
                >
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  {r.brd_filename}
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
