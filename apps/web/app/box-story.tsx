"use client";

import { useEffect, useRef } from "react";
import { FRAMES, FramePlayer, POSTER_SRC, POSTER_SRCSET } from "./frame-player";
import { storySteps } from "./site";

// The box's motion, from design/box/build_box.py, runs over 180 frames,
// pre-rendered by scripts/build-frames.mjs.
const FADE = 8; // frames over which a caption fades in or out

type Step = { from: number; to: number; title: string; body: string };

// Frame ranges follow the animation: the Pi settles (1-26), the case
// closes (34-78), the cables plug in (92-138), the light turns on (140-150).
// The captions live in site.ts, shared with the Markdown version of the page.
const FRAME_RANGES = [
  [-FADE, 30],
  [34, 86],
  [90, 138],
  [140, Infinity],
];
const steps: Step[] = storySteps.map((step, k) => ({ from: FRAME_RANGES[k][0], to: FRAME_RANGES[k][1], ...step }));

// Where each step begins, for the progress bars. The last entry is the end.
const STARTS = [0, 34, 90, 140, FRAMES - 1];

// When the story stands still. It normally pins to the screen and plays as
// you scroll, which needs room: on a short screen (a phone on its side, or a
// page zoomed far in) the words would be cut off. So there, and for people
// who ask their device for less motion, it becomes an ordinary part of the
// page: the finished box, then every step, all readable at once. The height
// is in em, so it also applies to people who set a larger text size.
const STILL_QUERY = "(max-height: 32.5em), (prefers-reduced-motion: reduce)";
// The same rules apply without JavaScript, when nothing can play the story.
// They are !important to win over the layout classes and over the styles
// the scroll code sets on each caption.
const STILL_CSS = `
#story { height: auto !important; }
#story [data-pin] { position: static !important; height: auto !important; overflow: visible !important; }
#story [data-layout] { display: flex !important; flex-direction: column !important; align-items: stretch !important; gap: 2rem !important; height: auto !important; padding-block: 4rem !important; }
#story [data-stage] { order: 0 !important; flex: none !important; width: 100% !important; height: min(100vw - 3rem, 22rem) !important; }
#story [data-picture] { max-width: none !important; }
#story [data-text] { order: 1 !important; }
#story [data-captions] { grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)) !important; gap: 2.5rem !important; }
#story [data-caption] { grid-area: auto !important; align-self: start !important; opacity: 1 !important; transform: none !important; }
#story [data-bars] { display: none !important; }
`;

function clamp(value: number) {
  return Math.min(1, Math.max(0, value));
}

type Layout = { ranges: number[][]; starts: number[]; fade: number; frames: number };
const LAYOUT: Layout = {
  ranges: steps.map((step) => [step.from, Math.min(step.to, 1e9)]),
  starts: STARTS,
  fade: FADE,
  frames: FRAMES,
};

// Show the captions and fill the progress bars for a frame. It also runs as
// an inline script before React loads (see Prepaint), so it must not use
// anything from outside itself.
function paintText(frame: number, captions: ArrayLike<HTMLElement | null>, bars: ArrayLike<HTMLElement | null>, layout: Layout) {
  const unit = (value: number) => Math.min(1, Math.max(0, value));
  for (let k = 0; k < captions.length; k++) {
    const caption = captions[k];
    if (!caption) continue;
    const [from, to] = layout.ranges[k];
    const v = Math.min(unit((frame - from) / layout.fade), unit((to - frame) / layout.fade));
    caption.style.opacity = String(v);
    caption.style.transform = `translate3d(0, ${(1 - v) * 24}px, 0)`;
  }
  for (let k = 0; k < bars.length; k++) {
    const bar = bars[k];
    const { starts } = layout;
    if (bar) bar.style.transform = `scaleX(${unit((frame - starts[k]) / (starts[k + 1] - starts[k]))})`;
  }
}

declare global {
  interface Window {
    storyPrepaint?: () => void;
  }
}

// The page is prerendered with every caption hidden. Reloaded halfway down,
// that would paint the wrong captions until React loads, then snap. This
// runs during parsing, before the first paint, and keeps the captions in step
// with the scroll (browsers may restore it late) until React takes over.
// Like paintText, it must not use anything from outside itself.
function prepaint(layout: Layout, paint: typeof paintText) {
  const section = document.getElementById("story");
  const pin = section?.querySelector<HTMLElement>("[data-pin]");
  if (!section || !pin) return;
  const captions = section.querySelectorAll<HTMLElement>("[data-caption]");
  const bars = section.querySelectorAll<HTMLElement>("[data-bar]");
  const update = () => {
    const top = section.getBoundingClientRect().top + window.scrollY;
    const scrollable = Math.max(1, section.offsetHeight - pin.offsetHeight);
    const progress = Math.min(1, Math.max(0, (window.scrollY - top) / scrollable));
    paint(progress * (layout.frames - 1), captions, bars, layout);
  };
  update();
  window.addEventListener("scroll", update, { passive: true });
  window.storyPrepaint = update;
}

function Prepaint() {
  return (
    <script
      dangerouslySetInnerHTML={{ __html: `(${prepaint})(${JSON.stringify(LAYOUT)}, ${paintText})` }}
    />
  );
}

// How quickly the story catches up with the scroll position, per second.
// Easing smooths out mouse-wheel steps and the uneven scroll updates some
// phones send, without feeling detached from the finger.
const EASE = 12;
// A bigger jump than this in one step comes from the browser restoring the
// scroll position on reload, or a link; go straight there instead of
// playing the animation to catch up.
const JUMP = 24;

export default function BoxStory() {
  const section = useRef<HTMLElement>(null);
  const pinned = useRef<HTMLDivElement>(null);
  const captions = useRef<(HTMLDivElement | null)[]>([]);
  const bars = useRef<(HTMLSpanElement | null)[]>([]);
  const canvas = useRef<HTMLCanvasElement>(null);
  const frame = useRef(0); // the frame on screen, easing toward the scroll position

  useEffect(() => {
    const el = section.current;
    const pin = pinned.current;
    const screen = canvas.current;
    if (!el || !pin || !screen) return;
    let top = 0;
    let scrollable = 1;
    let raf = 0;
    let last = 0;
    let dirty = true;
    const still = window.matchMedia(STILL_QUERY);
    const player = new FramePlayer(screen, () => {
      dirty = true; // a frame finished decoding; redraw with it
    });

    // Layout is read only when it changes, never per frame. The pinned box is
    // sized in svh, so mobile toolbars showing and hiding don't move the story.
    function measure() {
      top = el!.getBoundingClientRect().top + window.scrollY;
      scrollable = Math.max(1, el!.offsetHeight - pin!.offsetHeight);
      dirty = true;
    }

    function goal() {
      if (still.matches) return FRAMES - 1; // standing still: show the finished box
      return clamp((window.scrollY - top) / scrollable) * (FRAMES - 1);
    }

    function paint(f: number) {
      paintText(f, captions.current, bars.current, LAYOUT);
      player.draw(f);
      if (player.hasDrawn) screen!.style.opacity = "1";
    }

    // One loop drives the captions, the progress bars and the 3D scene, so
    // they all move together in the same frame as the scroll.
    function tick(now: number) {
      raf = requestAnimationFrame(tick);
      const target = goal();
      const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
      last = now;
      let f = frame.current + (target - frame.current) * (1 - Math.exp(-dt * EASE));
      if (Math.abs(target - frame.current) > JUMP) {
        f = target;
        player.prioritize(f);
      } else if (Math.abs(target - f) < 0.005) f = target;
      if (f === frame.current && !dirty) return;
      dirty = false;
      frame.current = f;
      paint(f);
    }

    function start() {
      if (raf) return;
      measure();
      frame.current = goal(); // arrive in place, don't animate from a stale spot
      player.load(frame.current, still.matches); // on screen already, so don't wait for the page to finish loading
      last = 0;
      raf = requestAnimationFrame(tick);
    }

    function stop() {
      cancelAnimationFrame(raf);
      raf = 0;
    }

    // Take over from the inline script.
    if (window.storyPrepaint) window.removeEventListener("scroll", window.storyPrepaint);
    measure();
    frame.current = goal();
    paint(frame.current);

    // Download frames once the rest of the page has loaded, so they never
    // compete with the first screen.
    const load = () => player.load(frame.current, still.matches);
    if (document.readyState === "complete") load();
    else window.addEventListener("load", load, { once: true });

    // Only run while the story is on screen.
    const visible = new IntersectionObserver(([entry]) => (entry.isIntersecting ? start() : stop()), {
      rootMargin: "50% 0px",
    });
    visible.observe(el);
    const resized = new ResizeObserver(measure);
    resized.observe(el);
    resized.observe(document.body);
    window.addEventListener("resize", measure);
    // Turning a phone, zooming, or changing the motion setting can start or
    // stop the story. Once it plays, it needs every frame.
    const stillChanged = () => {
      measure();
      if (!still.matches) player.load(goal());
    };
    still.addEventListener("change", stillChanged);
    return () => {
      still.removeEventListener("change", stillChanged);
      stop();
      player.dispose();
      window.removeEventListener("load", load);
      visible.disconnect();
      resized.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  return (
    <>
    {/* React moves this to the <head>. */}
    <style href="story-still" precedence="default">{`@media ${STILL_QUERY} {${STILL_CSS}}`}</style>
    <noscript>
      <style>{STILL_CSS}</style>
    </noscript>
    <section id="story" ref={section} className="relative h-[600vh]" aria-label="How the box comes together">
      <div ref={pinned} data-pin className="sticky top-0 h-svh overflow-hidden">
        {/* On a phone the picture sits above the words and gives up height
            when the words need it (large text, wide spacing), so they never
            overlap. On a wide screen they sit side by side. */}
        <div
          data-layout
          className="mx-auto flex h-full w-full max-w-6xl flex-col justify-center gap-4 px-6 py-6 lg:grid lg:grid-cols-[1fr_1.25fr] lg:items-center lg:gap-12 lg:py-0"
        >
          <div data-text className="order-2 shrink-0 lg:order-1">
          {/* Every caption shares one grid cell, so the cell is as tall as the
              longest and the words stay in the page's flow. */}
          <div data-captions className="grid">
            {steps.map((step, k) => (
              <div
                key={step.title}
                ref={(el) => {
                  captions.current[k] = el;
                }}
                data-caption
                // Prepaint sets its style before React loads.
                suppressHydrationWarning
                className="col-start-1 row-start-1 self-end opacity-0 will-change-transform"
              >
                <p className="text-sm font-medium uppercase tracking-widest text-emerald-800">
                  Step {k + 1}
                </p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-900 sm:text-5xl">
                  {step.title}
                </h2>
                <p className="mt-4 max-w-md text-lg leading-relaxed text-zinc-600 sm:text-xl">{step.body}</p>
              </div>
            ))}
          </div>
          <div data-bars className="mt-8 flex gap-2" aria-hidden="true">
            {steps.map((step, k) => (
              <span key={step.title} className="h-1 w-10 overflow-hidden rounded-full bg-zinc-200">
                <span
                  ref={(el) => {
                    bars.current[k] = el;
                  }}
                  data-bar
                  suppressHydrationWarning
                  className="block h-full origin-left rounded-full bg-emerald-500"
                  style={{ transform: "scaleX(0)" }}
                />
              </span>
            ))}
          </div>
          </div>
          {/* The space the picture may use. The picture is the largest square
              that fits in it (cqw and cqh are this box's width and height). */}
          <div
            data-stage
            className="order-1 flex min-h-0 shrink grow-0 basis-[min(60svh,calc(100vw-3rem))] items-center justify-center [container-type:size] lg:order-2 lg:h-full"
          >
          <div
            data-picture
            role="img"
            aria-label="A small Raspberry Pi computer is closed inside a white box. An internet cable and a power cable plug in, and a green light turns on."
            className="relative aspect-square w-[min(100cqw,100cqh)] lg:max-w-[80svh]"
          >
            <noscript>
              {/* eslint-disable-next-line @next/next/no-img-element -- frames are pre-sized; the optimizer adds nothing */}
              <img
                src={POSTER_SRC}
                srcSet={POSTER_SRCSET}
                sizes="(min-width: 1024px) min(80svh, 55vw), min(100vw - 3rem, 60svh)"
                alt=""
                className="absolute inset-0 size-full"
              />
            </noscript>
            {/* Fades in once it has the right frame, so a reload mid-story
                never flashes the wrong one. */}
            <canvas ref={canvas} className="absolute inset-0 size-full opacity-0 transition-opacity duration-300" />
          </div>
          </div>
        </div>
      </div>
    </section>
    <Prepaint />
    </>
  );
}
