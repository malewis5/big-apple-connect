import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "./info-page";
import { RequestedPath } from "./requested-path";
import { infoPages, notFound } from "./site";

// The layout tells search engines to index every page and points the
// canonical at the home page. Neither fits a missing page, so override both.
export const metadata: Metadata = {
  title: "Page not found",
  alternates: { canonical: null },
  robots: { index: false, follow: true },
};

// A green dot with a slow, soft ring: "connected". Same as the dot in the header.
function LiveDot({ className }: { className: string }) {
  return (
    <span aria-hidden="true" className={`relative flex ${className}`}>
      <span className="absolute inline-flex size-full rounded-full bg-emerald-400 opacity-40 motion-safe:animate-ping motion-safe:[animation-duration:2.5s] motion-safe:[animation-iteration-count:2]" />
      <span className="relative inline-flex size-full rounded-full bg-emerald-500" />
    </span>
  );
}

function CheckIcon() {
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
      <svg viewBox="0 0 20 20" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
        <path d="m5 10.5 3.5 3.5L15 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function MissingIcon() {
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-zinc-500">
      <svg viewBox="0 0 20 20" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
        <path d="M6 10h8" strokeLinecap="round" />
      </svg>
    </span>
  );
}

// Shown for any address the site doesn't have. The shared header comes from
// layout.tsx. Agents asking for Markdown get /not-found.md instead (proxy.ts).
//
// The words sit beside a quick check from the box: your internet works, the
// site works, only this page is missing. On phones the check is a short,
// plain list under the button, with no card.
export default function NotFound() {
  const { check } = notFound;
  return (
    <div className="flex flex-1 flex-col bg-white text-zinc-900">
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto grid w-full max-w-6xl flex-1 content-start items-center px-6 pt-12 pb-16 outline-none sm:pt-20 lg:content-center lg:grid-cols-[1.1fr_1fr] lg:gap-20 lg:pt-10 lg:pb-24"
      >
        <div className="min-w-0">
          <p className="inline-flex rounded-full bg-zinc-100 px-3 py-1 text-sm font-medium text-zinc-600">{notFound.eyebrow}</p>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight text-balance break-words sm:text-6xl lg:mt-6 lg:text-7xl">{notFound.title}</h1>
          <p className="mt-4 max-w-lg text-lg leading-relaxed text-pretty text-zinc-600 lg:mt-6 lg:text-xl">
            {notFound.body}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-8 gap-y-5 lg:mt-10">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-zinc-700"
            >
              <span aria-hidden="true">←</span>
              Back to the home page
            </Link>
            {/* Wide screens only: the footer has the same links. */}
            <nav aria-label="Other pages" className="hidden gap-2 text-sm font-medium text-zinc-600 lg:flex">
              {infoPages.map((page) => (
                <Link key={page.slug} href={`/${page.slug}`} className="inline-flex min-h-11 items-center px-2 underline-offset-4 hover:text-zinc-900 hover:underline">
                  {page.title}
                </Link>
              ))}
            </nav>
          </div>
        </div>

        {/* The quick check. A plain list on phones, a card on wide screens. The words on the left say the same. */}
        <figure
          aria-hidden="true"
          className="mt-12 max-w-lg min-w-0 lg:mt-0 lg:max-w-none lg:rounded-3xl lg:bg-white lg:p-8 lg:shadow-[0_1px_2px_rgb(0_0_0/0.04),0_24px_60px_-24px_rgb(0_0_0/0.25)] lg:ring-1 lg:ring-zinc-900/5"
        >
          <div className="flex items-center justify-between text-sm font-medium">
            <span className="flex items-center gap-2.5 text-zinc-900">
              <LiveDot className="size-2.5" />
              {check.title}
            </span>
            <span className="text-zinc-600 motion-safe:animate-check-in motion-safe:[animation-delay:1.6s]">{check.done}</span>
          </div>

          <ul className="mt-4 divide-y lg:mt-6 divide-zinc-900/5 border-t border-zinc-900/5">
            {check.rows.map((row, k) => (
              <li
                key={row.label}
                className="flex items-center gap-4 py-3.5 motion-safe:animate-check-in lg:items-start lg:py-5"
                style={{ animationDelay: `${0.3 + k * 0.45}s` }}
              >
                {row.ok ? <CheckIcon /> : <MissingIcon />}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                    <span className="font-semibold lg:text-lg">{row.label}</span>
                    <span className={`text-sm font-medium ${row.ok ? "text-emerald-800" : "text-zinc-600"}`}>{row.value}</span>
                  </div>
                  <p className="mt-1 hidden truncate text-zinc-600 lg:block">{row.ok ? row.note : <RequestedPath />}</p>
                </div>
              </li>
            ))}
          </ul>
        </figure>
      </main>

      <SiteFooter />
    </div>
  );
}
