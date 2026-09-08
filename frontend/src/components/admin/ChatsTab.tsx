import * as React from "react";
import { MessageSquare } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useChatConversations, useChatConversation } from "@/hooks/useChatbot";

function when(iso: string) {
  return new Date(iso).toLocaleString();
}

export function ChatsTab() {
  const { data: conversations, isLoading } = useChatConversations();
  const [openSession, setOpenSession] = React.useState<string | null>(null);
  const { data: messages, isLoading: loadingThread } = useChatConversation(openSession);

  return (
    <div>
      <p className="mb-4 text-sm text-muted-foreground">
        Every conversation people have with the assistant, so you can see what's being asked.
      </p>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && (!conversations || conversations.length === 0) && (
        <EmptyState
          icon={<MessageSquare className="h-6 w-6" />}
          title="No conversations yet"
          description="Once people start chatting with the assistant, their questions show up here."
        />
      )}

      {!isLoading && conversations && conversations.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Person</TableHead>
                <TableHead>First question</TableHead>
                <TableHead>Messages</TableHead>
                <TableHead>Last activity</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {conversations.map((c) => (
                <TableRow key={c.session_id}>
                  <TableCell className="text-sm font-medium text-foreground">{c.user_name ?? "—"}</TableCell>
                  <TableCell className="max-w-sm truncate text-sm text-muted-foreground">{c.first_question}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{c.message_count}</TableCell>
                  <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{when(c.last_at)}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => setOpenSession(c.session_id)}>
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={Boolean(openSession)} onOpenChange={(o) => !o && setOpenSession(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Conversation</DialogTitle>
            <DialogDescription>The full exchange, oldest first.</DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1 scrollbar-thin">
            {loadingThread && <Skeleton className="h-24 w-full rounded-lg" />}
            {messages?.map((m) => (
              <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm",
                    m.role === "user"
                      ? "rounded-br-sm bg-primary text-primary-foreground"
                      : "rounded-tl-sm bg-muted text-foreground"
                  )}
                >
                  {m.content}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
