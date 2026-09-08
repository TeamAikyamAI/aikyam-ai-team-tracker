import { Navigate, Outlet } from "react-router-dom";
import { useMyFeatures } from "@/hooks/usePermissions";
import type { FeatureKey } from "@/types";

/**
 * Route guard driven by the Admin access grid rather than a hardcoded role.
 *
 * This is only the polite half - it keeps someone from landing on a screen
 * that would fail anyway. Every endpoint behind these screens checks the same
 * grid on the server, so bypassing this changes nothing.
 */
export function FeatureRoute({ features }: { features: FeatureKey[] }) {
  const { data, isLoading } = useMyFeatures();

  // Wait rather than redirect: bouncing on first paint would throw people off
  // a bookmarked page every time they open the app.
  if (isLoading || !data) return null;

  if (!features.some((f) => data.features.includes(f))) {
    const fallback = data.features.includes("dashboard") ? "/" : "/queue";
    return <Navigate to={fallback} replace />;
  }
  return <Outlet />;
}
