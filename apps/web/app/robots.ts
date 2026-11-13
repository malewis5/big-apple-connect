import type { MetadataRoute } from "next";
import { SITE_URL } from "./site";

// Search engines and AI answer engines alike may read the site; being cited
// in AI answers is part of the goal. Preview deployments stay out of indexes.
const AI_CRAWLERS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Perplexity-User",
  "Google-Extended",
  "Applebot-Extended",
  "CCBot",
];

export default function robots(): MetadataRoute.Robots {
  if (process.env.VERCEL_ENV && process.env.VERCEL_ENV !== "production") {
    return { rules: { userAgent: "*", disallow: "/" } };
  }
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: "/capture" },
      { userAgent: AI_CRAWLERS, allow: "/", disallow: "/capture" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
