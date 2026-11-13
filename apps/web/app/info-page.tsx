import type { Metadata } from "next";
import Link from "next/link";
import { DISCLAIMER, SITE_NAME, SITE_URL, infoPages, type InfoPage } from "./site";

export function infoPage(slug: string): InfoPage {
  const page = infoPages.find((p) => p.slug === slug);
  if (!page) throw new Error(`No page named ${slug} in site.ts`);
  return page;
}

export function infoMetadata(slug: string): Metadata {
  const page = infoPage(slug);
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: `/${slug}`, types: { "text/markdown": `/${slug}.md` } },
    openGraph: { url: `/${slug}`, title: `${page.title} | ${SITE_NAME}`, description: page.description },
  };
}

// Links to the About, Contact and Privacy pages, shown at the foot of every page.
export function SiteFooter() {
  return (
    <footer className="bg-zinc-50 px-6 pb-16 text-center text-sm leading-relaxed text-zinc-600">
      <nav aria-label="About this site" className="flex flex-wrap justify-center gap-x-6 gap-y-2">
        {infoPages.map((page) => (
          <Link key={page.slug} href={`/${page.slug}`} className="font-medium underline-offset-4 hover:text-zinc-900 hover:underline">
            {page.title}
          </Link>
        ))}
      </nav>
      <p className="mx-auto mt-4 max-w-2xl">{DISCLAIMER}</p>
    </footer>
  );
}

// The layout shared by the About, Contact and Privacy pages.
export default function InfoPageView({ slug }: { slug: string }) {
  const page = infoPage(slug);
  // Tells search engines and AI answer engines what kind of page this is, and
  // where it sits in the site. The breadcrumb entry matches the trail of
  // links shown above the page title, and lets Google show that trail in
  // search results in place of the bare web address.
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": slug === "about" ? "AboutPage" : slug === "contact" ? "ContactPage" : "WebPage",
        "@id": `${SITE_URL}/${slug}#page`,
        url: `${SITE_URL}/${slug}`,
        name: `${page.title} | ${SITE_NAME}`,
        description: page.description,
        inLanguage: "en-US",
        isPartOf: { "@id": `${SITE_URL}/#website` },
        about: { "@id": `${SITE_URL}/#software` },
        breadcrumb: { "@id": `${SITE_URL}/${slug}#breadcrumb` },
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${SITE_URL}/${slug}#breadcrumb`,
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
          { "@type": "ListItem", position: 2, name: page.title, item: `${SITE_URL}/${slug}` },
        ],
      },
    ],
  };

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 text-zinc-900">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-3xl flex-1 px-6 pt-12 pb-24 outline-none">
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-2 text-sm text-zinc-600">
            <li>
              <Link href="/" className="font-medium underline-offset-4 hover:text-zinc-900 hover:underline">
                Home
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li aria-current="page">{page.title}</li>
          </ol>
        </nav>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight sm:text-6xl">{page.title}</h1>
        <p className="mt-6 text-xl leading-relaxed text-pretty text-zinc-500">{page.description}</p>
        {page.sections.map((section) => (
          <section key={section.title} className="mt-14">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{section.title}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="mt-4 text-lg leading-relaxed text-zinc-600">
                {paragraph}
              </p>
            ))}
            {section.links && (
              <ul className="mt-5 space-y-2 text-lg">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <a href={link.href} className="font-medium text-emerald-700 underline underline-offset-4 hover:text-emerald-900">
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </main>

      <SiteFooter />
    </div>
  );
}
