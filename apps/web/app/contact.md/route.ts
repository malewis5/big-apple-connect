import { MARKDOWN_HEADERS, infoMarkdown } from "../markdown";

export function GET() {
  return new Response(infoMarkdown("contact"), { headers: MARKDOWN_HEADERS("/contact") });
}
