import { NextResponse, type NextRequest } from "next/server";

// Content negotiation for the home page: agents that prefer Markdown get
// /index.md from the same URL, everyone else gets the HTML page. Both answers
// set Vary: Accept so caches keep them apart. (Under `next start`, Next replaces
// Vary on the prerendered HTML page; the Markdown response keeps it.)

// The quality (q) a client gives a media type in its Accept header, from 0 to 1.
// An exact match wins over type/* and */*. Missing means 0.
function quality(accept: string, type: string) {
  const [major] = type.split("/");
  let best = { specificity: -1, q: 0 };
  for (const part of accept.split(",")) {
    const [range, ...params] = part.trim().toLowerCase().split(";");
    const specificity = range === type ? 2 : range === `${major}/*` ? 1 : range === "*/*" ? 0 : -1;
    if (specificity <= best.specificity) continue;
    const qParam = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
    const q = qParam ? Number(qParam.slice(2)) : 1;
    best = { specificity, q: Number.isFinite(q) ? q : 0 };
  }
  return best.q;
}

// Markdown only when asked for by name, at least as strongly as HTML. Browsers
// never name text/markdown, so they always get HTML.
export function prefersMarkdown(accept: string | null) {
  if (!accept || !/text\/markdown/i.test(accept)) return false;
  const markdown = quality(accept, "text/markdown");
  return markdown > 0 && markdown >= quality(accept, "text/html");
}

export function proxy(request: NextRequest) {
  if (prefersMarkdown(request.headers.get("accept"))) {
    const response = NextResponse.rewrite(new URL("/index.md", request.url));
    response.headers.set("Vary", "Accept");
    return response;
  }
  const response = NextResponse.next();
  response.headers.set("Vary", "Accept");
  // Advertise the Markdown version to clients that read headers, not HTML.
  response.headers.set("Link", '</index.md>; rel="alternate"; type="text/markdown"');
  return response;
}

export const config = {
  matcher: "/",
};
