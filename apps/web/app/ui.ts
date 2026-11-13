// Shared layout for the home page's sections, so each one lines up with the
// header and the next: the same width, the same left edge, the same heading
// size and the same space between sections. The hero is the one exception,
// centered as the cover; every section after it reads from the left edge.

// The page's column: the header's width and padding, so text starts where
// the site name does.
export const CONTAINER = "mx-auto w-full max-w-6xl px-6";

// Space above and below a section.
export const SECTION_Y = "py-24 sm:py-32";

// A section's heading and the paragraph under it.
export const SECTION_TITLE = "text-4xl font-semibold tracking-tight text-balance sm:text-5xl";
export const SECTION_LEAD = "mt-4 max-w-2xl text-xl leading-relaxed text-pretty text-zinc-600";

// White cards on the page: the "Why it matters" reasons, the video and the
// project's status.
export const CARD =
  "rounded-3xl bg-white shadow-[0_1px_2px_rgb(0_0_0/0.04),0_16px_40px_-20px_rgb(0_0_0/0.18)] ring-1 ring-zinc-900/5";
