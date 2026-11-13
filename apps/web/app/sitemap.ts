import type { MetadataRoute } from "next";
import { HOME_UPDATED, SITE_NAME, SITE_URL, demoVideo, infoPages } from "./site";

// Each page with the day its words last changed (kept by hand in site.ts).
// Search engines use that date to decide what to read again. They ignore the
// older "priority" and "change frequency" fields, so those are left out.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      lastModified: HOME_UPDATED,
      // The demo video on the home page. Next writes these into the XML as
      // they are, so they must not contain & or <.
      videos: [
        {
          title: `${SITE_NAME}: ${demoVideo.title}`,
          description: demoVideo.body,
          thumbnail_loc: `${SITE_URL}${demoVideo.files.thumbnail}`,
          content_loc: `${SITE_URL}${demoVideo.files.mp4}`,
          duration: demoVideo.seconds,
          publication_date: demoVideo.uploaded,
          family_friendly: "yes",
        },
      ],
    },
    ...infoPages.map((page) => ({ url: `${SITE_URL}/${page.slug}`, lastModified: page.updated })),
  ];
}
