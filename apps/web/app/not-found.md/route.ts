import { notFoundMarkdown } from "../markdown";

// The "page not found" answer for AI agents that ask for Markdown. proxy.ts
// sends them here for any address the site doesn't have, so they get a short
// explanation and links to follow, not an HTML error page.
export function GET() {
  return new Response(notFoundMarkdown(), {
    status: 404,
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      Vary: "Accept",
      "X-Robots-Tag": "noindex",
    },
  });
}
