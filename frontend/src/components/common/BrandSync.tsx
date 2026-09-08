import * as React from "react";
import { useLogoMeta, logoSrc } from "@/hooks/useBranding";
import { usePublicSettings } from "@/hooks/useSettings";

/**
 * Keeps the browser tab in step with the stored branding: the tab icon comes
 * from the same asset the sidebar and login page use (version-stamped, so a new
 * upload replaces it immediately), and the tab title follows the configured
 * application name.
 */
export function BrandSync() {
  const { data: logo } = useLogoMeta();
  const { settings } = usePublicSettings();

  React.useEffect(() => {
    if (!logo) return;
    let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.type = logo.content_type;
    link.href = logoSrc(logo);
  }, [logo]);

  React.useEffect(() => {
    if (settings.app_name) document.title = settings.app_name;
  }, [settings.app_name]);

  return null;
}
