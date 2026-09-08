import * as React from "react";
import { Lock, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { usePermissionMatrix, useUpdatePermissions } from "@/hooks/usePermissions";
import type { PermissionFeature } from "@/types";

export function PermissionsTab() {
  const { data, isLoading } = usePermissionMatrix();
  const save = useUpdatePermissions();

  // Pending edits, keyed "feature:role" - the grid stays responsive while the
  // person ticks several boxes, and one Save sends them together.
  const [edits, setEdits] = React.useState<Record<string, boolean>>({});
  const dirty = Object.keys(edits).length > 0;

  const valueOf = (f: PermissionFeature, role: string) =>
    edits[`${f.key}:${role}`] ?? f.roles[role]!.allowed;

  const toggle = (f: PermissionFeature, role: string, next: boolean) => {
    const key = `${f.key}:${role}`;
    setEdits((prev) => {
      const copy = { ...prev };
      if (f.roles[role]!.allowed === next) delete copy[key];
      else copy[key] = next;
      return copy;
    });
  };

  const onSave = () => {
    const changes: Record<string, Record<string, boolean>> = {};
    for (const [key, allowed] of Object.entries(edits)) {
      const [feature, role] = key.split(":");
      (changes[feature!] ??= {})[role!] = allowed;
    }
    save.mutate(changes, {
      onSuccess: () => {
        setEdits({});
        toast.success("Access updated");
      },
      onError: (err: any) =>
        toast.error(err?.response?.data?.detail ?? "Couldn't save those changes"),
    });
  };

  if (isLoading || !data) return <Skeleton className="mt-4 h-96 rounded-xl" />;

  const groups = Array.from(new Set(data.features.map((f) => f.group)));

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          Who can see what
        </CardTitle>
        <CardDescription>
          Tick a box to give that role a feature. This is enforced on the server, not just in the
          menu, so a role without a feature is refused even if someone types the address directly.
          Changes apply the next time each person's browser refreshes.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 pr-4 text-left font-medium text-muted-foreground">Feature</th>
                {data.roles.map((r) => (
                  <th key={r.key} className="w-28 pb-2 text-center font-medium text-muted-foreground">
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <React.Fragment key={group}>
                  <tr>
                    <td
                      colSpan={data.roles.length + 1}
                      className="pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                    >
                      {group}
                    </td>
                  </tr>
                  {data.features
                    .filter((f) => f.group === group)
                    .map((f) => (
                      <tr key={f.key} className="border-t border-border/60">
                        <td className="py-2.5 pr-4 align-top">
                          <p className="font-medium leading-tight">{f.label}</p>
                          {f.help && (
                            <p className="mt-0.5 max-w-lg text-xs leading-snug text-muted-foreground">
                              {f.help}
                            </p>
                          )}
                        </td>
                        {data.roles.map((r) => {
                          const cell = f.roles[r.key]!;
                          const checked = valueOf(f, r.key);
                          const changed = edits[`${f.key}:${r.key}`] !== undefined;
                          const box = (
                            <div className="flex justify-center">
                              <Checkbox
                                checked={checked}
                                disabled={cell.locked}
                                aria-label={`${f.label} for ${r.label}`}
                                onCheckedChange={(v) => toggle(f, r.key, v === true)}
                                className={changed ? "ring-2 ring-primary ring-offset-1" : undefined}
                              />
                            </div>
                          );
                          return (
                            <td key={r.key} className="py-2.5 align-top">
                              {cell.locked ? (
                                <Tooltip delayDuration={200}>
                                  <TooltipTrigger asChild>
                                    <div className="flex items-center justify-center gap-1 text-muted-foreground">
                                      <Lock className="h-3 w-3" />
                                      {box}
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    Always on - this is what stops an admin locking themselves out.
                                  </TooltipContent>
                                </Tooltip>
                              ) : (
                                box
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <Button onClick={onSave} disabled={!dirty || save.isPending}>
            {save.isPending ? "Saving..." : "Save changes"}
          </Button>
          {dirty && (
            <Button variant="ghost" onClick={() => setEdits({})} disabled={save.isPending}>
              Cancel
            </Button>
          )}
          {dirty && (
            <span className="text-xs text-muted-foreground">
              {Object.keys(edits).length} unsaved change{Object.keys(edits).length === 1 ? "" : "s"}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
