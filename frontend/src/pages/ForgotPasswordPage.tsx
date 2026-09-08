import * as React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, Mail, MailCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/common/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { usePublicSettings } from "@/hooks/useSettings";
import { api, apiErrorMessage } from "@/lib/api";

export default function ForgotPasswordPage() {
  const { settings } = usePublicSettings();
  const [email, setEmail] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [sent, setSent] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim() });
      setSent(true);
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
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Forgot your password?</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Enter your e-mail and we will send you a reset link.</p>
        </div>
        <Card className="brand-glow">
          <CardContent className="p-6">
            {sent ? (
              <div className="flex flex-col items-center text-center" role="status">
                <MailCheck className="mb-3 h-8 w-8 text-primary" />
                <p className="text-sm text-foreground">If that address has an account, a reset link is on its way.</p>
                <p className="mt-1.5 text-xs text-muted-foreground">Check your inbox (and spam folder). The link works for a limited time.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="email" type="email" autoComplete="email" placeholder={`you@${settings.email_domain}`} value={email} onChange={(e) => setEmail(e.target.value)} className="pl-9" required autoFocus />
                  </div>
                </div>
                {error && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" size="lg" disabled={loading || !email.trim()}>
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Send reset link
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
