<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Writing the site's words

The words people read are in `app/site.ts`. When you write or change them:

- Don't name a thing and then describe it after a comma: "Big Apple Connect,
  the city's program" or "Netrics, the open-source software used in...". The
  other order is out too: "its maker, Matt Lewis". Use the name alone, or say
  what it is in a sentence of its own: "It follows Netrics. Netrics is the
  software used in...".
