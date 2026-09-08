import * as React from "react";
import { Check, ChevronsUpDown, User as UserIcon, X } from "lucide-react";
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
import type { User } from "@/types";

interface UserComboboxProps {
  users: User[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  excludeId?: number;
  disabled?: boolean;
  clearable?: boolean;
}

export function UserCombobox({
  users,
  value,
  onChange,
  placeholder = "Select a person…",
  excludeId,
  disabled,
  clearable = true,
}: UserComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const options = React.useMemo(
    () => users.filter((u) => u.id !== excludeId && u.is_active !== false),
    [users, excludeId]
  );
  const selected = users.find((u) => u.id === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          <span className="flex min-w-0 items-center gap-2 truncate">
            <UserIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            {selected ? (
              <span className="truncate">
                {selected.name} <span className="text-muted-foreground">· {selected.email}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </span>
          <span className="flex items-center gap-1">
            {clearable && selected && (
              <span
                role="button"
                tabIndex={-1}
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(null);
                }}
                className="rounded-sm p-0.5 hover:bg-accent"
              >
                <X className="h-3.5 w-3.5" />
              </span>
            )}
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search people by name or email…" />
          <CommandList>
            <CommandEmpty>No matching person.</CommandEmpty>
            <CommandGroup>
              {options.map((u) => (
                <CommandItem
                  key={u.id}
                  value={`${u.name} ${u.email}`}
                  onSelect={() => {
                    onChange(u.id);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("h-4 w-4", value === u.id ? "opacity-100" : "opacity-0")} />
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
  );
}
