import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
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
import type { User } from "@/types";
import { initials } from "@/lib/utils";

interface MultiUserSelectProps {
  users: User[];
  value: number[];
  onChange: (ids: number[]) => void;
  placeholder?: string;
}

export function MultiUserSelect({ users, value, onChange, placeholder = "Select owners…" }: MultiUserSelectProps) {
  const [open, setOpen] = React.useState(false);
  const selected = users.filter((u) => value.includes(u.id));

  const toggle = (id: number) => {
    if (value.includes(id)) onChange(value.filter((v) => v !== id));
    else onChange([...value, id]);
  };

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between font-normal">
            <span className="text-muted-foreground">
              {selected.length === 0 ? placeholder : `${selected.length} owner${selected.length > 1 ? "s" : ""} selected`}
            </span>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search people…" />
            <CommandList>
              <CommandEmpty>No matching person.</CommandEmpty>
              <CommandGroup>
                {users
                  .filter((u) => u.is_active !== false)
                  .map((u) => (
                    <CommandItem key={u.id} value={`${u.name} ${u.email}`} onSelect={() => toggle(u.id)}>
                      <Check className={cn("h-4 w-4", value.includes(u.id) ? "opacity-100" : "opacity-0")} />
                      <span className="flex flex-col">
                        <span className="text-sm">{u.name}</span>
                        <span className="text-xs text-muted-foreground">{u.email}</span>
                      </span>
                    </CommandItem>
                  ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((u) => (
            <Badge key={u.id} variant="secondary" className="gap-1.5 py-1 pl-1 pr-2">
              <Avatar className="h-4 w-4">
                <AvatarFallback className="text-[9px]">{initials(u.name)}</AvatarFallback>
              </Avatar>
              {u.name}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
