import * as React from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Send, Sparkles, User as UserIcon } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAskTracker } from "@/hooks/useAsk";
import { useVerticals } from "@/hooks/useVerticals";
import { useAuth } from "@/context/AuthContext";
import { apiErrorMessage } from "@/lib/api";
import { initials, cn } from "@/lib/utils";
import { toast } from "sonner";

interface ChatEntry {
  id: string;
  question: string;
  answer: string | null;
  loading: boolean;
  error?: string;
  unconfigured?: boolean;
}

function buildSuggestions(verticalName?: string): string[] {
  // The vertical-specific example comes from the verticals actually configured,
  // so it never names one this install doesn't have.
  return [
    "Which projects are overdue?",
    verticalName
      ? `How many projects does the ${verticalName} vertical have?`
      : "Which vertical has the most projects?",
    "Summarize this week's progress across all projects",
    "What service requests are still awaiting review?",
  ];
}

function looksUnconfigured(answer: string): boolean {
  const s = answer.toLowerCase();
  return s.includes("not configured") || s.includes("not been configured") || s.includes("no ai") || s.includes("api key");
}

export default function AskTrackerPage() {
  const { user } = useAuth();
  const { data: verticals } = useVerticals();
  const suggestions = React.useMemo(() => buildSuggestions(verticals?.[0]?.name), [verticals]);
  const [searchParams, setSearchParams] = useSearchParams();
  const ask = useAskTracker();
  const [input, setInput] = React.useState("");
  const [entries, setEntries] = React.useState<ChatEntry[]>([]);
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const ranInitial = React.useRef(false);

  const submitQuestion = React.useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      const id = crypto.randomUUID();
      setEntries((prev) => [...prev, { id, question: trimmed, answer: null, loading: true }]);
      setInput("");
      try {
        const result = await ask.mutateAsync({ question: trimmed });
        setEntries((prev) =>
          prev.map((e) =>
            e.id === id
              ? { ...e, answer: result.answer, loading: false, unconfigured: looksUnconfigured(result.answer) }
              : e
          )
        );
      } catch (err) {
        setEntries((prev) =>
          prev.map((e) => (e.id === id ? { ...e, loading: false, error: apiErrorMessage(err) } : e))
        );
        toast.error("Couldn't get an answer", { description: apiErrorMessage(err) });
      }
    },
    [ask]
  );

  React.useEffect(() => {
    const q = searchParams.get("q");
    if (q && !ranInitial.current) {
      ranInitial.current = true;
      submitQuestion(q);
      searchParams.delete("q");
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submitQuestion(input);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <PageHeader title="Ask the Tracker" description="Ask natural-language questions about your team's projects." />

      <Card className="flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto scrollbar-thin p-5">
          {entries.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Sparkles className="h-6 w-6" />
              </div>
              <p className="text-sm font-medium text-foreground">Ask anything about your projects</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Try one of these, or type your own question below.
              </p>
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => submitQuestion(s)}
                    className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-left text-xs text-foreground transition-colors hover:bg-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-6">
            <AnimatePresence initial={false}>
              {entries.map((entry) => (
                <motion.div
                  key={entry.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-3"
                >
                  <div className="flex items-start gap-3">
                    <Avatar className="h-7 w-7 shrink-0">
                      <AvatarFallback className="bg-secondary text-[10px]">{initials(user?.name)}</AvatarFallback>
                    </Avatar>
                    <div className="rounded-2xl rounded-tl-sm bg-secondary px-3.5 py-2 text-sm text-secondary-foreground">
                      {entry.question}
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Avatar className="h-7 w-7 shrink-0 bg-primary/10">
                      <AvatarFallback className="bg-transparent text-primary">
                        <Sparkles className="h-3.5 w-3.5" />
                      </AvatarFallback>
                    </Avatar>
                    <div
                      className={cn(
                        "max-w-[85%] rounded-2xl rounded-tl-sm border px-3.5 py-2.5 text-sm",
                        entry.error
                          ? "border-destructive/30 bg-destructive/5 text-destructive"
                          : entry.unconfigured
                          ? "border-warning/30 bg-warning/5 text-foreground"
                          : "border-border bg-card text-foreground"
                      )}
                    >
                      {entry.loading ? (
                        <span className="flex items-center gap-2 text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Thinking…
                        </span>
                      ) : entry.error ? (
                        entry.error
                      ) : (
                        <span className="whitespace-pre-wrap">{entry.answer}</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <div ref={bottomRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-border p-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about project status, owners, deadlines…"
            rows={1}
            className="min-h-[40px] resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitQuestion(input);
              }
            }}
          />
          <Button type="submit" size="icon" disabled={!input.trim() || ask.isPending}>
            {ask.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </Card>
    </div>
  );
}
