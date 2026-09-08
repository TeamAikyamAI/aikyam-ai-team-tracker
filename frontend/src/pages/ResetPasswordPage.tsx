import * as React from "react";
import { motion } from "framer-motion";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, KeyRound, Loader2, Lock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/common/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { usePublicSettings } from "@/hooks/useSettings";
import { api, apiErrorMessage } from "@/lib/api";

export default function ResetPasswordPage() {
  const { settings } = usePublicSettings();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const mismatch = confirm.length > 0 && confirm !== password;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (mismatch) return;
    setError(null);
    setLoading(true);
    try {
      const r = await api.post<{ detail: string }>("/auth/reset-password", { token, password });
      toast.success(r.data.detail);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_15%_10%,hsl(var(--brand-violet)/0.16),transparent_50%),radial-gradient(ellipse_at_85%_90%,hsl(var(--brand-sky)/0.18),transparent_45%),radial-gradient(circle_at_70%_20%,hsl(var(--brand-coral)/0.10),transparent_35%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.35] [background-image:linear-gradient(hsl(var(--border))_1px,transparent_1px),linear-gradient(90deg,hsl(var(--border))_1px,transparent_1px)] [background-size:32px_32px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]"
      />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo className="mb-4 h-14 w-14" alt={settings.app_name} />
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Choose a new password</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{settings.app_name}</p>
        </div>
        <Card className="brand-glow">
          <CardContent className="p-6">
            {!token ? (
              <div className="text-center">
                <p className="text-sm text-foreground">This link is missing its token.</p>
                <p className="mt-1.5 text-xs text-muted-foreground">Open the link from the e-mail again, or request a new one.</p>
                <Button asChild variant="outline" className="mt-4">
                  <Link to="/forgot-password">Request a new link</Link>
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="password">New password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className="pl-9" required autoFocus />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="confirm">Confirm password</Label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className="pl-9" required aria-invalid={mismatch || undefined} />
                  </div>
                  {mismatch && <p className="text-xs text-destructive">Passwords do not match.</p>}
                </div>
                {error && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" size="lg" disabled={loading || !password || mismatch}>
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Set new password
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
        <p className="mt-6 text-center text-sm">
          <Link to="/login" className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
