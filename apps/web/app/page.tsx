import Image from "next/image";
import BoxStory from "./box-story";

const REPO = "https://github.com/malewis5/big-apple-connect-box";

const reasons = [
  {
    icon: "/icons/record.webp",
    title: "It keeps a record",
    body: "A speed test on your phone shows one moment. The box checks all day and all night, so slow evenings and outages get written down too.",
  },
  {
    icon: "/icons/compare.webp",
    title: "Results you can compare",
    body: "It measures the same way as a University of Chicago study of home internet, so results from different homes and cities line up.",
  },
  {
    icon: "/icons/home.webp",
    title: "Advice for your home",
    body: "Later, we want to turn the results into personalized recommendations to improve your home's internet.",
    later: true,
  },
];

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="currentColor">
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
    </svg>
  );
}

export default function Home() {
  return (
    <div className="flex-1 bg-white text-zinc-900">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
        <a href="#" className="flex items-center gap-2.5 text-sm font-semibold tracking-tight">
          <span className="size-2.5 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgb(16_185_129/0.15)]" />
          Big Apple Connect Box
        </a>
        <a
          href={REPO}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-zinc-700 ring-1 ring-zinc-900/10 transition hover:bg-zinc-50 hover:text-zinc-900"
        >
          <GitHubIcon className="size-4" />
          View on GitHub
        </a>
      </header>

      <main>
        <section className="flex min-h-[calc(100svh-5rem)] flex-col items-center justify-center px-6 pb-20 text-center">
          <p className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
            For homes in New York City public housing
          </p>
          <h1 className="mt-6 max-w-4xl text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
            Is your internet as good as promised?
          </h1>
          <p className="mt-6 max-w-2xl text-xl leading-relaxed text-pretty text-zinc-500 sm:text-2xl">
            New York City promises NYCHA residents free, fast and reliable internet. We&apos;re building a small box
            that checks that promise from inside the home, day and night.
          </p>
          <div className="mt-16 flex flex-col items-center gap-2 text-sm text-zinc-400" aria-hidden="true">
            Scroll to see how it works
            <svg viewBox="0 0 20 20" className="size-5 motion-safe:animate-bounce" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M5 8l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </section>

        <BoxStory />

        <section className="bg-gradient-to-b from-white to-zinc-50 px-6 py-32">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-4xl font-semibold tracking-tight sm:text-6xl">Why it matters</h2>
            <p className="mt-4 max-w-2xl text-xl leading-relaxed text-zinc-500">
              Internet providers tell you how fast your connection should be. The box shows how fast it really is.
            </p>
            <div className="mt-16 grid gap-6 md:grid-cols-3">
              {reasons.map((reason) => (
                <div
                  key={reason.title}
                  className="rounded-3xl bg-white p-8 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_16px_40px_-20px_rgb(0_0_0/0.18)] ring-1 ring-zinc-900/5"
                >
                  <Image src={reason.icon} alt="" width={480} height={480} className="-mt-4 -ml-4 size-48" />
                  <h3 className="flex items-center gap-2 text-xl font-semibold">
                    {reason.title}
                    {reason.later && (
                      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-500">
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
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Where things stand</h2>
            <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-zinc-500">
              The measuring software already runs on Mac and Linux, and we&apos;re still improving it. The box is next.
              Everything is free and open source, so anyone can see exactly how it works.
            </p>
            <a
              href={REPO}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-zinc-700"
            >
              <GitHubIcon className="size-4" />
              Follow along on GitHub
            </a>
          </div>
        </section>
      </main>

      <footer className="bg-zinc-50 px-6 pb-16 text-center text-sm leading-relaxed text-zinc-400">
        <p className="mx-auto max-w-2xl">
          An independent, personal project. It is not affiliated with, endorsed by or run by the City of New York,
          NYCHA, or any internet provider.
        </p>
      </footer>
    </div>
  );
}
