import * as React from "react";
import { Check, ChevronsUpDown, Plus, X } from "lucide-react";
import { cn, initials } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { UserBrief } from "@/types";

/**
 * Picks the people a requestor wants kept in the loop.
 *
 * Two ways in, because not everyone who needs a copy has a login: pick a
 * colleague by name from the directory, or type a company address for a head
 * who never signs in. Names come from the directory, which deliberately does
 * not expose anyone's address — so a picked person travels as their id and the
 * server resolves it.
 */
export interface RecipientValue {
  userIds: number[];
  emails: string[];
}

export const emptyRecipients: RecipientValue = { userIds: [], emails: [] };

/** What the form posts: ids and addresses in one JSON list. */
export function toFormValue(value: RecipientValue): string {
  const all = [...value.userIds.map(String), ...value.emails];
  return all.length ? JSON.stringify(all) : "";
}

interface Props {
  users: UserBrief[];
  value: RecipientValue;
  onChange: (next: RecipientValue) => void;
  domain?: string;
  label: string;
  excludeUserId?: number;
}

export function RecipientPicker({ users, value, onChange, domain, label, excludeUserId }: Props) {
  const [open, setOpen] = React.useState(false);
  const [typed, setTyped] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const pickable = users.filter((u) => u.id !== excludeUserId);
  const picked = pickable.filter((u) => value.userIds.includes(u.id));

  function toggleUser(id: number) {
    onChange(
      value.userIds.includes(id)
        ? { ...value, userIds: value.userIds.filter((v) => v !== id) }
        : { ...value, userIds: [...value.userIds, id] }
    );
  }

  function addTyped() {
    const address = typed.trim().toLowerCase();
    if (!address) return;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(address)) {
      setError("That does not look like an email address.");
      return;
    }
    if (domain && !address.endsWith("@" + domain)) {
      setError(`Only @${domain} addresses can be added here.`);
      return;
    }
    if (value.emails.includes(address)) {
      setError("Already added.");
      return;
    }
    onChange({ ...value, emails: [...value.emails, address] });
    setTyped("");
    setError(null);
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button type="button" variant="outline" size="sm" className="justify-between">
              Pick from the team
              <ChevronsUpDown className="ml-1 h-3.5 w-3.5 opacity-60" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-0" align="start">
            <Command>
              <CommandInput placeholder="Search by name…" />
              <CommandList>
                <CommandEmpty>Nobody by that name.</CommandEmpty>
                <CommandGroup>
                  {pickable.map((u) => (
                    <CommandItem key={u.id} value={u.name} onSelect={() => toggleUser(u.id)}>
                      <Avatar className="mr-2 h-6 w-6">
                        <AvatarFallback className="text-[10px]">{initials(u.name)}</AvatarFallback>
                      </Avatar>
                      <span className="truncate">{u.name}</span>
                      <Check
                        className={cn(
                          "ml-auto h-4 w-4",
                          value.userIds.includes(u.id) ? "opacity-100" : "opacity-0"
                        )}
                      />
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        <div className="flex min-w-[16rem] flex-1 items-center gap-1.5">
          <Input
            value={typed}
            onChange={(e) => {
              setTyped(e.target.value);
              setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addTyped();
              }
            }}
            placeholder={domain ? `or type name@${domain}` : "or type an email address"}
            aria-label={`Add an email address to ${label}`}
          />
          <Button type="button" variant="outline" size="icon" onClick={addTyped} aria-label={`Add to ${label}`}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {(picked.length > 0 || value.emails.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {picked.map((u) => (
            <Badge key={`u${u.id}`} variant="secondary" className="gap-1 pr-1">
              {u.name}
              <button
                type="button"
                onClick={() => toggleUser(u.id)}
                aria-label={`Remove ${u.name} from ${label}`}
                className="rounded-full p-0.5 hover:bg-background/60"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {value.emails.map((email) => (
            <Badge key={email} variant="secondary" className="gap-1 pr-1">
              {email}
              <button
                type="button"
                onClick={() => onChange({ ...value, emails: value.emails.filter((e) => e !== email) })}
                aria-label={`Remove ${email} from ${label}`}
                className="rounded-full p-0.5 hover:bg-background/60"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
