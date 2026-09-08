import * as React from "react";
import { Loader2, Lock, Save, RotateCcw, MailCheck, CalendarClock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminSettings, useUpdateSettings, useTestEmail, useDigestPreview } from "@/hooks/useSettings";
import { apiErrorMessage } from "@/lib/api";
import type { SettingItem } from "@/types";

type Draft = Record<string, string | number | boolean>;

export function SettingsTab() {
  const { data: items, isLoading } = useAdminSettings();
  const save = useUpdateSettings();
  const testEmail = useTestEmail();
  const digestPreview = useDigestPreview();
  const [draft, setDraft] = React.useState<Draft>({});
  // The SMTP error is the whole point of the test button and it is usually
  // longer than a toast will show, so the last result also stays on the page.
  const [emailResult, setEmailResult] = React.useState<{ ok: boolean; text: string } | null>(null);

  // Only the fields the admin actually touched get sent, so blank secrets are
  // never mistaken for "clear this password".
  const dirtyKeys = Object.keys(draft);

  function valueOf(item: SettingItem): string | number | boolean {
    if (item.key in draft) return draft[item.key];
    if (item.type === "secret") return "";
    if (item.type === "bool") return Boolean(item.value);
    return (item.value ?? "") as string | number;
  }

  function setValue(key: string, value: string | number | boolean) {
    // Belt and braces: the inputs are disabled, but a stray change must never
    // put an .env-backed key into the payload - the API rejects those.
    if (items?.find((i) => i.key === key)?.env_only) return;
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function handleSave() {
    if (!dirtyKeys.length) return;
    try {
      await save.mutateAsync(draft);
      setDraft({});
      toast.success("Settings saved", {
        description: dirtyKeys.some((k) => k.startsWith("digest_"))
          ? "The weekly digest schedule was updated and is already live."
          : "Changes are live — no restart needed.",
      });
    } catch (err) {
      toast.error("Couldn't save settings", { description: apiErrorMessage(err) });
    }
  }

  if (isLoading || !items) {
    return (
      <div className="max-w-3xl space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  const groups = Array.from(new Set(items.map((i) => i.group)));

  return (
    <div className="max-w-3xl">
      <p className="mb-4 text-sm text-muted-foreground">
        Everything here is stored in the database and applies as soon as you save — no redeploy, no editing
        files on the server.
      </p>

      <div className="space-y-4">
        {groups.map((group) => (
          <Card key={group}>
            <CardContent className="p-5">
              <h3 className="mb-4 text-sm font-semibold text-foreground">{group}</h3>
              <div className="space-y-4">
                {items
                  .filter((i) => i.group === group)
                  .map((item) => (
                    <div key={item.key} className="grid gap-1.5 sm:grid-cols-[minmax(0,240px)_1fr] sm:items-start sm:gap-4">
                      <Label htmlFor={item.key} className="pt-2 text-sm">
                        {item.label}
                      </Label>
                      <div className="min-w-0">
                        {item.type === "bool" ? (
                          <Switch
                            id={item.key}
                            checked={Boolean(valueOf(item))}
                            onCheckedChange={(v) => setValue(item.key, v)}
                          />
                        ) : item.type === "select" ? (
                          <Select value={String(valueOf(item))} onValueChange={(v) => setValue(item.key, v)}>
                            <SelectTrigger id={item.key}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {item.options.map((o) => (
                                <SelectItem key={o} value={o} className="capitalize">
                                  {o}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : item.type === "text" ? (
                          <Textarea
                            id={item.key}
                            rows={4}
                            value={String(valueOf(item))}
                            onChange={(e) => setValue(item.key, e.target.value)}
                          />
                        ) : (
                          <Input
                            id={item.key}
                            type={item.type === "secret" ? "password" : item.type === "int" ? "number" : "text"}
                            min={item.min ?? undefined}
                            max={item.max ?? undefined}
                            readOnly={item.env_only}
                            disabled={item.env_only}
                            // Browsers happily autofill a saved password into any
                            // password box, which is how a mask once got saved over
                            // a working credential.
                            autoComplete={item.type === "secret" ? "new-password" : "off"}
                            value={
                              item.env_only && item.type === "secret"
                                ? (item.is_set ? "•••••••• (from .env)" : "not set in .env")
                                : String(valueOf(item))
                            }
                            placeholder={item.type === "secret" && item.is_set && !item.env_only ? "•••••••• (saved)" : undefined}
                            className={item.env_only ? "bg-muted text-muted-foreground" : undefined}
                            onChange={(e) =>
                              setValue(item.key, item.type === "int" ? Number(e.target.value) : e.target.value)
                            }
                          />
                        )}
                        {item.help && <p className="mt-1 text-xs text-muted-foreground">{item.help}</p>}
                        {item.env_only && (
                          <p className="mt-1 flex items-start gap-1.5 text-xs text-warning">
                            <Lock className="mt-0.5 h-3 w-3 shrink-0" />
                            <span>
                              Set in <code>backend/.env</code>, not here. Edit that file and restart
                              the backend to change it.
                            </span>
                          </p>
                        )}
                        {item.type === "secret" && item.is_set && !item.env_only && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            A value is saved. Leave blank to keep it, or type a new one to replace it.
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
              </div>

              {group === "Weekly digest" && (
                <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={digestPreview.isPending}
                    onClick={async () => {
                      if (dirtyKeys.length > 0) {
                        toast.warning("Save first", {
                          description:
                            "The preview uses the saved settings. Click 'Save changes' at the bottom, then try again.",
                        });
                        return;
                      }
                      try {
                        const res = await digestPreview.mutateAsync();
                        toast.success(res.emails_sent ? "Preview sent" : "Nothing to send", {
                          description: res.detail,
                        });
                      } catch (err) {
                        toast.error("Couldn't send the preview", { description: apiErrorMessage(err) });
                      }
                    }}
                  >
                    {digestPreview.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CalendarClock className="h-4 w-4" />
                    )}
                    Send me this week's digest
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {dirtyKeys.length > 0
                      ? "Save your changes first."
                      : "Exactly what Monday will send, delivered to you instead of your manager."}
                  </span>
                </div>
              )}

              {group === "Email" && (
                <div className="mt-5 border-t border-border pt-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      // Deliberately clickable even with unsaved edits: a dead
                      // button with a line of grey text next to it reads as a
                      // broken screen. Clicking says what to do instead.
                      disabled={testEmail.isPending}
                      onClick={async () => {
                        if (dirtyKeys.length > 0) {
                          toast.warning("Save first", {
                            description:
                              "The test uses the saved settings. Click 'Save changes' at the bottom, then send the test.",
                          });
                          return;
                        }
                        setEmailResult(null);
                        try {
                          const res = await testEmail.mutateAsync();
                          setEmailResult({ ok: true, text: res.detail });
                          toast.success("It works", { description: res.detail });
                        } catch (err) {
                          const text = apiErrorMessage(err);
                          setEmailResult({ ok: false, text });
                          toast.error("Test email failed", { description: text });
                        }
                      }}
                    >
                      {testEmail.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <MailCheck className="h-4 w-4" />
                      )}
                      Send test email
                    </Button>
                    <span className="text-xs text-muted-foreground">
                      {dirtyKeys.length > 0
                        ? "Save your changes first, then test."
                        : "Sends a real email to your own address using the saved settings."}
                    </span>
                  </div>
                  {emailResult && (
                    <p
                      className={`mt-3 break-words rounded-lg border p-3 text-xs ${
                        emailResult.ok
                          ? "border-success/40 bg-success/10 text-foreground"
                          : "border-destructive/40 bg-destructive/10 text-foreground"
                      }`}
                    >
                      {emailResult.text}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="sticky bottom-4 mt-5 flex items-center gap-2 rounded-xl border border-border bg-background/90 p-3 shadow-soft backdrop-blur">
        <Button onClick={handleSave} disabled={!dirtyKeys.length || save.isPending}>
          {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save changes
        </Button>
        {dirtyKeys.length > 0 && (
          <>
            <Button variant="ghost" onClick={() => setDraft({})} disabled={save.isPending}>
              <RotateCcw className="h-4 w-4" />
              Discard
            </Button>
            <span className="text-xs text-muted-foreground">
              {dirtyKeys.length} unsaved change{dirtyKeys.length > 1 ? "s" : ""}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
