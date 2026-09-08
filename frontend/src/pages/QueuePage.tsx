import * as React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { FileText, LayoutGrid, PlusCircle, Search } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useProjectQueue } from "@/hooks/useProjects";
import { useCan } from "@/hooks/usePermissions";

export default function QueuePage() {
  const { data, isLoading, isError } = useProjectQueue();
  const [search, setSearch] = React.useState("");
  // Both calls to action below lead to Apply for Service, so both disappear
  // for a role that may not file one - otherwise the button bounces.
  const canApply = useCan()("apply");

  const filtered = React.useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return data;
    return data.filter(
      (p) => p.name.toLowerCase().includes(q) || p.vertical_name.toLowerCase().includes(q)
    );
  }, [data, search]);

  return (
    <div>
      <PageHeader
        title="Project Queue"
        description="Browse everything currently in motion across the AI &amp; Automation team before filing a new request."
        actions={
          canApply ? (
            <Button asChild>
              <Link to="/apply">
                <PlusCircle className="h-4 w-4" />
                Apply for Service
              </Link>
            </Button>
          ) : undefined
        }
      />

      <div className="mb-5 flex items-center gap-2">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search projects or verticals…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        {data && (
          <span className="text-xs text-muted-foreground">
            {filtered.length} of {data.length} projects
          </span>
        )}
      </div>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="space-y-3 p-5">
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-6 w-24 rounded-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={<FileText className="h-6 w-6" />}
          title="Couldn't load the project queue"
          description="Check that the backend is running and reachable, then refresh the page."
        />
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          icon={<LayoutGrid className="h-6 w-6" />}
          title={data && data.length > 0 ? "No projects match your search" : "No projects in the queue yet"}
          description={
            data && data.length > 0
              ? "Try a different search term."
              : "Once projects are created, they'll show up here for everyone to browse."
          }
        />
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
            >
              <Card className="h-full transition-shadow hover:shadow-popover">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-semibold leading-snug text-foreground">{p.name}</h3>
                  </div>
                  <p className="text-xs text-muted-foreground">{p.vertical_name}</p>
                  <div className="mt-auto pt-1">
                    <StatusBadge name={p.status_name} color={p.status_color} />
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {canApply && (
        <div className="mt-10 rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center">
          <p className="text-sm font-medium text-foreground">Don't see what you need?</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
            File a service request with a BRD signed by your vertical head, and the AI &amp; Automation team will
            review it.
          </p>
          <Button asChild className="mt-4">
            <Link to="/apply">
              <PlusCircle className="h-4 w-4" />
              Apply for Service
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
