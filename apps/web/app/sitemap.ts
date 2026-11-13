import type { MetadataRoute } from "next";
import { HOME_UPDATED, SITE_URL, infoPages } from "./site";

// Each page with the day its words last changed (kept by hand in site.ts).
// Search engines use that date to decide what to read again. They ignore the
// older "priority" and "change frequency" fields, so those are left out.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, lastModified: HOME_UPDATED },
    ...infoPages.map((page) => ({ url: `${SITE_URL}/${page.slug}`, lastModified: page.updated })),
  ];
}
