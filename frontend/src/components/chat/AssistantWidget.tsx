import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Send, X, Loader2, Sparkles, MessageSquarePlus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";
import { usePublicSettings } from "@/hooks/useSettings";
import { useCan } from "@/hooks/usePermissions";
import { useAskAssistant, fetchChatHistory } from "@/hooks/useChatbot";
import { apiErrorMessage } from "@/lib/api";

interface Turn {
  role: "user" | "assistant";
  content: string;
}

const SESSION_KEY = "aikyam_assistant_session";

/** A friendly robot face - the button people click to open the assistant. */
function RobotFace({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <circle cx="24" cy="7" r="2.6" fill="currentColor" />
      <rect x="23" y="9" width="2" height="4" rx="1" fill="currentColor" />
      <rect x="8" y="13" width="32" height="26" rx="9" fill="currentColor" />
      <circle cx="18" cy="24" r="3.2" className="fill-primary" />
      <circle cx="30" cy="24" r="3.2" className="fill-primary" />
      <circle cx="19.1" cy="22.9" r="1.1" fill="white" />
      <circle cx="31.1" cy="22.9" r="1.1" fill="white" />
      <path
        d="M17.5 30.5c1.9 2.4 4.1 3.6 6.5 3.6s4.6-1.2 6.5-3.6"
        className="stroke-primary"
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      />
      <rect x="4.5" y="21" width="3.5" height="8" rx="1.75" fill="currentColor" />
      <rect x="40" y="21" width="3.5" height="8" rx="1.75" fill="currentColor" />
    </svg>
  );
}

export function AssistantWidget() {
  const { user } = useAuth();
  const { settings } = usePublicSettings();
  const can = useCan();
  const ask = useAskAssistant();

  const [open, setOpen] = React.useState(false);
  const [bubbleDismissed, setBubbleDismissed] = React.useState(false);
  const [input, setInput] = React.useState("");
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Restore the conversation so a page refresh doesn't lose the thread.
  React.useEffect(() => {
    if (!open || sessionId !== null) return;
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(SESSION_KEY);
    } catch {
      stored = null;
    }
    if (!stored) return;
    setSessionId(stored);
    fetchChatHistory(stored)
      .then((msgs) => setTurns(msgs.map((m) => ({ role: m.role, content: m.content }))))
      .catch(() => {
        /* a stale session id is not worth bothering the user about */
      });
  }, [open, sessionId]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, ask.isPending]);

  const suggestions = React.useMemo(
    () =>
      (settings.chatbot_suggestions ?? "")
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, 6),
    [settings.chatbot_suggestions]
  );

  // The permission grid describes "Ask the Tracker" as the assistant page AND
  // this widget, so revoking it has to remove both. Until this check the page
  // disappeared and the bubble kept working, which made the grid a half-truth.
  if (!user || !settings.chatbot_enabled || !can("ask")) return null;

  async function send() {
    const question = input.trim();
    if (!question || ask.isPending) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", content: question }]);
    try {
      const res = await ask.mutateAsync({ question, sessionId });
      if (!sessionId) {
        setSessionId(res.session_id);
        try {
          localStorage.setItem(SESSION_KEY, res.session_id);
        } catch {
          /* private mode - the chat still works, it just won't survive a refresh */
        }
      }
      setTurns((t) => [...t, { role: "assistant", content: res.answer }]);
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `Sorry - ${apiErrorMessage(err, "something went wrong.")}` },
      ]);
    }
  }

  return (
    <>
      <div className="fixed bottom-5 right-5 z-50 flex items-end gap-2.5 print:hidden">
        <AnimatePresence>
          {!open && !bubbleDismissed && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.95 }}
              transition={{ delay: 0.6, duration: 0.25 }}
              className="relative mb-2 max-w-[210px] rounded-2xl rounded-br-sm border border-border bg-popover px-3.5 py-2.5 text-xs leading-relaxed text-popover-foreground shadow-popover"
            >
              {settings.chatbot_greeting}
              <button
                onClick={() => setBubbleDismissed(true)}
                aria-label="Dismiss"
                className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-background text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          onClick={() => setOpen((o) => !o)}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          aria-label={open ? "Close the assistant" : `Chat with ${settings.chatbot_name}`}
          aria-expanded={open}
          className="brand-gradient flex h-14 w-14 items-center justify-center rounded-full text-white shadow-glow transition-shadow hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <AnimatePresence mode="wait" initial={false}>
            {open ? (
              <motion.span key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}>
                <X className="h-6 w-6" />
              </motion.span>
            ) : (
              <motion.span
                key="bot"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="text-primary-foreground"
              >
                <RobotFace className="h-9 w-9" />
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed bottom-24 right-5 z-50 flex h-[min(560px,calc(100vh-8rem))] w-[min(380px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-border bg-popover shadow-popover print:hidden"
          >
            <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
              <div className="brand-gradient flex h-9 w-9 items-center justify-center rounded-full text-white">
                <RobotFace className="h-6 w-6" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{settings.chatbot_name}</p>
                <p className="truncate text-xs text-muted-foreground">Ask me about {settings.app_name}</p>
              </div>
              {turns.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => {
                    try {
                      localStorage.removeItem(SESSION_KEY);
                    } catch {
                      /* ignore */
                    }
                    setTurns([]);
                    setSessionId(null);
                    setInput("");
                  }}
                  aria-label="Start a new chat"
                  title="New chat"
                >
                  <MessageSquarePlus className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon-sm" onClick={() => setOpen(false)} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4 scrollbar-thin">
              {turns.length === 0 && (
                <div className="space-y-3">
                  <div className="rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2.5 text-sm text-foreground">
                    {settings.chatbot_greeting}
                  </div>
                  <div className="space-y-1.5">
                    {suggestions.map((s) => (
                      <button
                        key={s}
                        onClick={() => setInput(s)}
                        className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                      >
                        <Sparkles className="h-3.5 w-3.5 shrink-0" />
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {turns.map((t, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn("flex", t.role === "user" ? "justify-end" : "justify-start")}
                >
                  <div
                    className={cn(
                      "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm",
                      t.role === "user"
                        ? "rounded-br-sm bg-primary text-primary-foreground"
                        : "rounded-tl-sm bg-muted text-foreground"
                    )}
                  >
                    {t.content}
                  </div>
                </motion.div>
              ))}

              {ask.isPending && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2.5 text-sm text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Thinking…
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-border p-3">
              <div className="flex items-end gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                  placeholder="Ask about projects, status, the queue…"
                  rows={1}
                  className="max-h-28 min-h-[38px] resize-none text-sm"
                />
                <Button size="icon" onClick={() => void send()} disabled={!input.trim() || ask.isPending} aria-label="Send">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <p className="mt-1.5 flex items-center gap-1 text-[11px] text-muted-foreground">
                <Bot className="h-3 w-3" />
                Reads live tracker data. It can answer, not change anything.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
