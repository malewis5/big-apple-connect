import { DISCLAIMER, REPO, SITE_DESCRIPTION, SITE_NAME, SITE_URL, faqs } from "../site";

// /llms.txt (https://llmstxt.org): a plain summary of the project for AI
// assistants, built from the same facts as the page so the two stay in step.
const body = `# ${SITE_NAME}

> ${SITE_DESCRIPTION}

${DISCLAIMER}

## Questions and answers

${faqs.map((faq) => `### ${faq.question}\n\n${faq.answer}`).join("\n\n")}

## Links

- [Website](${SITE_URL}): what the box is and why it matters
- [Website as Markdown](${SITE_URL}/index.md): the full home page as Markdown (or request ${SITE_URL} with \`Accept: text/markdown\`)
- [Source code and downloads](${REPO}): the measuring program, how to run it, and how it measures
- [Latest release](${REPO}/releases/latest): downloads for Mac, Linux and Raspberry Pi
- [Big Apple Connect](https://access.nyc.gov/programs/big-apple-connect/): the New York City program the box was built to measure
- [Netrics](https://github.com/internet-innovation/netrics): the University of Chicago measurement software it follows
`;

export function GET() {
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
