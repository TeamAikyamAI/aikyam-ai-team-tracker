import { cn } from "@/lib/utils";
import { useLogoMeta, logoSrc } from "@/hooks/useBranding";

/**
 * Renders the branding logo from the stored asset.
 *
 * Always an <img> pointing at the API, never an inlined <svg>: an uploaded SVG
 * is a document that could carry script, so it stays in its own sandboxed
 * request (the API serves it with a restrictive CSP and nosniff) rather than
 * being parsed into this page's DOM.
 */
export function Logo({ className, alt = "Aikyam" }: { className?: string; alt?: string }) {
  const { data } = useLogoMeta();
  return (
    <img
      src={logoSrc(data)}
      alt={alt}
      className={cn("object-contain", className)}
      draggable={false}
    />
  );
}
