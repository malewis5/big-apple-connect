import Image from "next/image";
import BoxStory from "./box-story";
import { SiteFooter } from "./info-page";
import { GitHubIcon } from "./site-header";
import {
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

// The maker's own public profiles. They tell search engines and AI answer
// engines which Matt Lewis this is. Each one is a profile he links to from
// his GitHub page or his own website. Only list a profile that really exists.
const AUTHOR_PROFILES = [
  "https://github.com/malewis5",
  "https://www.linkedin.com/in/malewis5",
  "https://twitter.com/mttlws",
  "https://www.mattech.fyi",
];

// Structured data for search engines and AI answer engines. Every entry
// describes something the page shows, in the same words, as Google requires.
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      url: SITE_URL,
      name: SITE_NAME,
      description: SITE_DESCRIPTION,
      inLanguage: "en-US",
      publisher: { "@id": `${SITE_URL}/#author` },
    },
    {
      "@type": "WebPage",
      "@id": `${SITE_URL}/#webpage`,
      url: SITE_URL,
      name: SITE_TITLE,
      headline: hero.title,
      description: hero.body,
      inLanguage: "en-US",
      isPartOf: { "@id": `${SITE_URL}/#website` },
      about: { "@id": `${SITE_URL}/#software` },
      author: { "@id": `${SITE_URL}/#author` },
      hasPart: [
        { "@id": `${SITE_URL}/#how-it-works` },
        { "@id": `${SITE_URL}/#why-it-matters` },
        { "@id": `${SITE_URL}/#faq` },
      ],
    },
    {
      "@type": "Person",
      "@id": `${SITE_URL}/#author`,
      name: "Matt Lewis",
      description: `Maker and maintainer of the ${SITE_NAME}. It is an independent, open-source project that measures home internet for NYCHA residents.`,
      url: "https://github.com/malewis5",
      sameAs: AUTHOR_PROFILES,
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE_URL}/#software`,
      name: SITE_NAME,
      description:
        "Open-source program that measures home internet speed, latency and reliability around the clock and saves the results as evidence.",
      applicationCategory: "UtilitiesApplication",
      operatingSystem: "macOS, Linux, Raspberry Pi OS",
      isAccessibleForFree: true,
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      license: `${REPO}/blob/main/LICENSE`,
      codeRepository: REPO,
      downloadUrl: `${REPO}/releases/latest`,
      author: { "@id": `${SITE_URL}/#author` },
      url: SITE_URL,
      sameAs: [REPO],
      audience: {
        "@type": "Audience",
        audienceType: "NYCHA residents and New York City public housing households",
      },
    },
    // The four steps of the scrolling story.
    {
      "@type": "HowTo",
      "@id": `${SITE_URL}/#how-it-works`,
      name: `How the ${SITE_NAME} works`,
      description: hero.body,
      step: storySteps.map((step, k) => ({
        "@type": "HowToStep",
        position: k + 1,
        name: step.title,
        text: step.body,
      })),
    },
    // The three cards under "Why it matters".
    {
      "@type": "ItemList",
      "@id": `${SITE_URL}/#why-it-matters`,
      name: whyItMatters.title,
      description: whyItMatters.body,
      itemListElement: whyItMatters.reasons.map((reason, k) => ({
        "@type": "ListItem",
        position: k + 1,
        name: reason.title,
        description: reason.body,
      })),
    },
    {
      "@type": "FAQPage",
      "@id": `${SITE_URL}/#faq`,
      mainEntity: faqs.map((faq) => ({
        "@type": "Question",
        name: faq.question,
        acceptedAnswer: { "@type": "Answer", text: faq.answer },
      })),
    },
  ],
};

export default function Home() {
  return (
    <div className="flex-1 bg-white text-zinc-900">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <main id="main" tabIndex={-1} className="outline-none">
        <section className="flex min-h-[calc(100svh-5rem)] flex-col items-center justify-center px-6 pb-20 text-center">
          <p className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
            {hero.eyebrow}
          </p>
          <h1 className="mt-6 max-w-4xl text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
            {hero.title}
          </h1>
          <p className="mt-6 max-w-2xl text-xl leading-relaxed text-pretty text-zinc-500 sm:text-2xl">{hero.body}</p>
          <div className="mt-16 flex flex-col items-center gap-2 text-sm text-zinc-500" aria-hidden="true">
            Scroll to see how it works
            <svg viewBox="0 0 20 20" className="size-5 motion-safe:animate-bounce" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M5 8l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </section>

        <BoxStory />

        <section className="bg-gradient-to-b from-white to-zinc-50 px-6 py-32">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-4xl font-semibold tracking-tight sm:text-6xl">{whyItMatters.title}</h2>
            <p className="mt-4 max-w-2xl text-xl leading-relaxed text-zinc-500">{whyItMatters.body}</p>
            <div className="mt-16 grid gap-6 md:grid-cols-3">
              {whyItMatters.reasons.map((reason) => (
                <div
                  key={reason.title}
                  className="rounded-3xl bg-white p-8 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_16px_40px_-20px_rgb(0_0_0/0.18)] ring-1 ring-zinc-900/5"
                >
                  <Image src={reason.icon} alt="" width={480} height={480} className="-mt-4 -ml-4 size-48" />
                  <h3 className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xl font-semibold">
                    {reason.title}
                    {reason.later && (
                      <span className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium whitespace-nowrap text-zinc-600">
                        Coming later
                      </span>
                    )}
                  </h3>
                  <p className="mt-3 text-lg leading-relaxed text-zinc-500">{reason.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-zinc-50 px-6 pb-32">
          <div className="mx-auto max-w-3xl rounded-3xl bg-white px-8 py-14 text-center shadow-[0_1px_2px_rgb(0_0_0/0.04),0_16px_40px_-20px_rgb(0_0_0/0.18)] ring-1 ring-zinc-900/5 sm:px-16">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">{status.title}</h2>
            <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-zinc-500">{status.body}</p>
            <a
              href={REPO}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-zinc-700"
            >
              <GitHubIcon className="size-4" />
              Follow along on GitHub
            </a>
          </div>
        </section>

        <section id="faq" className="bg-zinc-50 px-6 pb-32">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Questions and answers</h2>
            <div className="mt-10 divide-y divide-zinc-900/10 border-y border-zinc-900/10">
              {faqs.map((faq) => (
                <details key={faq.question} className="group py-6">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-lg font-semibold [&::-webkit-details-marker]:hidden">
                    <h3>{faq.question}</h3>
                    <svg
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                      className="size-5 shrink-0 text-zinc-500 transition group-open:rotate-180 motion-reduce:transition-none"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <path d="M5 8l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </summary>
                  <p className="mt-3 text-lg leading-relaxed text-zinc-500">{faq.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <SiteFooter className="bg-zinc-50" />
    </div>
  );
}
