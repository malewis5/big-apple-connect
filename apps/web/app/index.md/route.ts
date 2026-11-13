import { MARKDOWN_HEADERS, homeMarkdown } from "../markdown";

export function GET() {
  return new Response(homeMarkdown(), { headers: MARKDOWN_HEADERS("/") });
}
