import {
  DISCLAIMER,
  REPO,
  SITE_DESCRIPTION,
  SITE_NAME,
  SITE_TITLE,
  SITE_URL,
  faqs,
  hero,
  status,
  storySteps,
  whyItMatters,
} from "./site";

// The home page as Markdown, for AI agents. Served at /index.md and at /
// when a request's Accept header prefers text/markdown (see proxy.ts).
// YAML frontmatter follows the fields Vercel uses for its own Markdown pages.
export function homeMarkdown() {
  return `---
title: ${JSON.stringify(SITE_TITLE)}
url: /
canonical_url: ${SITE_URL}
summary: ${JSON.stringify(SITE_DESCRIPTION)}
related:
  - ${REPO}
  - ${SITE_URL}/llms.txt
---

# ${hero.title}

${hero.eyebrow}.

${hero.body}

## How it works

${storySteps.map((step, k) => `${k + 1}. **${step.title}** ${step.body}`).join("\n")}

## ${whyItMatters.title}

${whyItMatters.body}

${whyItMatters.reasons
  .map((reason) => `- **${reason.title}${reason.later ? " (coming later)" : ""}.** ${reason.body}`)
  .join("\n")}

## ${status.title}

${status.body} Follow along on GitHub: ${REPO}

## Questions and answers

${faqs.map((faq) => `### ${faq.question}\n\n${faq.answer}`).join("\n\n")}

---

${SITE_NAME}. ${DISCLAIMER}
`;
}

export const MARKDOWN_HEADERS = {
  "Content-Type": "text/markdown; charset=utf-8",
  Vary: "Accept",
  // Points search engines at the HTML page, so the two don't compete.
  Link: `<${SITE_URL}>; rel="canonical"`,
};
