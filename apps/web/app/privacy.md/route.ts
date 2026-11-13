import { MARKDOWN_HEADERS, infoMarkdown } from "../markdown";

export function GET() {
  return new Response(infoMarkdown("privacy"), { headers: MARKDOWN_HEADERS("/privacy") });
}
