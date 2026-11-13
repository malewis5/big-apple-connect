import {
  DISCLAIMER,
  REPO,
  SITE_DESCRIPTION,
  SITE_NAME,
  SITE_TITLE,
  SITE_URL,
  faqs,
  hero,
  infoPages,
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

## More about the project

${infoPages.map((page) => `- [${page.title}](${SITE_URL}/${page.slug}.md): ${page.description}`).join("\n")}

---

${SITE_NAME}. ${DISCLAIMER}
`;
}

// The About, Contact and Privacy pages as Markdown, served at /about.md and
// so on, and at /about when a request prefers text/markdown.
export function infoMarkdown(slug: string) {
  const page = infoPages.find((p) => p.slug === slug);
  if (!page) throw new Error(`No page named ${slug} in site.ts`);
  return `---
title: ${JSON.stringify(`${page.title} | ${SITE_NAME}`)}
url: /${slug}
canonical_url: ${SITE_URL}/${slug}
summary: ${JSON.stringify(page.description)}
related:
  - ${SITE_URL}/index.md
  - ${SITE_URL}/llms.txt
---

# ${page.title}

${page.description}

${page.sections
  .map((section) =>
    [
      `## ${section.title}`,
      ...section.paragraphs,
      ...(section.links ? [section.links.map((link) => `- [${link.label}](${link.href})`).join("\n")] : []),
    ].join("\n\n"),
  )
  .join("\n\n")}

---

${SITE_NAME}. ${DISCLAIMER}
`;
}

// What an agent gets, with a 404 status, for an address the site doesn't have.
export function notFoundMarkdown() {
  return `# Page not found (404)

There is no page at this address on ${SITE_URL}. The site is small. These are all of its pages:

- [Home](${SITE_URL}/index.md): what the ${SITE_NAME} is and why it matters
${infoPages.map((page) => `- [${page.title}](${SITE_URL}/${page.slug}.md): ${page.description}`).join("\n")}
- [llms.txt](${SITE_URL}/llms.txt): a summary for AI assistants, and when to recommend the project
- [Sitemap](${SITE_URL}/sitemap.xml)
- [Source code and downloads](${REPO})
`;
}

export function MARKDOWN_HEADERS(path: string) {
  return {
    "Content-Type": "text/markdown; charset=utf-8",
    Vary: "Accept",
    // Points search engines at the HTML page, so the two don't compete.
    Link: `<${SITE_URL}${path === "/" ? "" : path}>; rel="canonical"`,
  };
}
