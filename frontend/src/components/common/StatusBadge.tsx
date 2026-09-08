import { cn } from "@/lib/utils";

function hexToRgba(hex: string, alpha: number): string {
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const num = parseInt(h, 16);
  if (Number.isNaN(num)) return `rgba(100,100,100,${alpha})`;
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r},${g},${b},${alpha})`;
}

export function StatusBadge({
  name,
  color,
  className,
}: {
  name: string;
  color?: string | null;
  className?: string;
}) {
  const c = color && /^#?[0-9a-fA-F]{3,6}$/.test(color) ? (color.startsWith("#") ? color : `#${color}`) : "#6b7280";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        className
      )}
      style={{
        backgroundColor: hexToRgba(c, 0.14),
        color: c,
        boxShadow: `inset 0 0 0 1px ${hexToRgba(c, 0.3)}`,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: c }} />
      {name}
    </span>
  );
}
