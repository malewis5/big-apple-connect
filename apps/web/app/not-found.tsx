import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "./info-page";
import { GitHubIcon } from "./site-header";
import { REPO, infoPages, notFound } from "./site";

// The layout tells search engines to index every page and points the
// canonical at the home page. Neither fits a missing page, so override both.
export const metadata: Metadata = {
  title: "Page not found",
  alternates: { canonical: null },
  robots: { index: false, follow: true },
};

// Shown for any address the site doesn't have. The shared header comes from
// layout.tsx. Agents asking for Markdown get /not-found.md instead (proxy.ts).
export default function NotFound() {
  return (
    <div className="flex flex-1 flex-col bg-white text-zinc-900">
      <main
        id="main"
        tabIndex={-1}
        className="flex flex-1 flex-col items-center justify-center px-6 pt-12 pb-24 text-center outline-none"
      >
        <p className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">{notFound.eyebrow}</p>
        <h1 className="mt-6 max-w-3xl text-5xl font-semibold tracking-tight text-balance sm:text-7xl">{notFound.title}</h1>
        <p className="mt-6 max-w-xl text-xl leading-relaxed text-pretty text-zinc-500">{notFound.body}</p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-zinc-700"
          >
            Go to the home page
          </Link>
          <a
            href={REPO}
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-zinc-700 ring-1 ring-zinc-900/10 transition hover:bg-zinc-50 hover:text-zinc-900"
          >
            <GitHubIcon className="size-4" />
            View on GitHub
          </a>
        </div>
        <nav aria-label="Pages on this site" className="mt-14 w-full max-w-md">
          <ul className="divide-y divide-zinc-900/10 border-y border-zinc-900/10 text-left">
            {infoPages.map((page) => (
              <li key={page.slug}>
                <Link
                  href={`/${page.slug}`}
                  className="group flex items-center justify-between gap-6 py-4 text-lg font-semibold"
                >
                  {page.title}
                  <span
                    aria-hidden="true"
                    className="text-zinc-400 transition group-hover:translate-x-1 group-hover:text-zinc-900 motion-reduce:transition-none"
                  >
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </main>

      <SiteFooter />
    </div>
  );
}
