import { MARKDOWN_HEADERS, infoMarkdown } from "../markdown";

export function GET() {
  return new Response(infoMarkdown("about"), { headers: MARKDOWN_HEADERS("/about") });
}
