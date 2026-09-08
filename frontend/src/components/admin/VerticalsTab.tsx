import * as React from "react";
import { Building2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { VerticalFormDialog } from "@/components/admin/VerticalFormDialog";
import { usePublicSettings } from "@/hooks/useSettings";
import { useVerticals } from "@/hooks/useVerticals";
import type { Vertical } from "@/types";

export function VerticalsTab() {
  const { data: verticals, isLoading } = useVerticals();
  const { settings } = usePublicSettings();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Vertical | null>(null);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Business verticals across {settings.org_name}.</p>
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setDialogOpen(true);
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          Add vertical
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && (!verticals || verticals.length === 0) && (
        <EmptyState icon={<Building2 className="h-6 w-6" />} title="No verticals yet" description="Add your first business vertical." />
      )}

      {!isLoading && verticals && verticals.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Head</TableHead>
                <TableHead>Head email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {verticals.map((v) => (
                <TableRow key={v.id}>
                  <TableCell className="font-medium text-foreground">{v.name}</TableCell>
                  <TableCell className="text-muted-foreground">{v.head_name}</TableCell>
                  <TableCell className="text-muted-foreground">{v.head_email}</TableCell>
                  <TableCell>
                    <Badge variant={v.is_active ? "success" : "secondary"}>{v.is_active ? "Active" : "Inactive"}</Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setEditing(v);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <VerticalFormDialog open={dialogOpen} onOpenChange={setDialogOpen} vertical={editing} />
    </div>
  );
}
