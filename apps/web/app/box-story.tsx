"use client";

import { useEffect, useRef } from "react";
import { FRAMES, FramePlayer, POSTER_SRC, POSTER_SRCSET } from "./frame-player";

// The box's motion, from design/box/build_box.py, runs over 180 frames,
// pre-rendered by scripts/build-frames.mjs.
const FADE = 8; // frames over which a caption fades in or out

type Step = { from: number; to: number; title: string; body: string };

// Frame ranges follow the animation: the Pi settles (1-26), the case
// closes (34-78), the cables plug in (92-138), the light turns on (140-150).
const steps: Step[] = [
  {
    from: -FADE,
    to: 30,
    title: "It starts with a tiny computer.",
    body: "A Raspberry Pi is a whole computer the size of a credit card. It costs about $35.",
  },
  {
    from: 34,
    to: 86,
    title: "We give it a simple home.",
    body: "A plain white case keeps it safe. It's small enough to sit right next to your router.",
  },
  {
    from: 90,
    to: 138,
    title: "Plug it into your router.",
    body: "One cable connects the box to your router. Plug the other into the wall for power, like a phone charger.",
  },
  {
    from: 140,
    to: Infinity,
    title: "Then it quietly keeps watch.",
    body: "Every five minutes it checks your connection. Every hour it runs a full speed test. Every result is saved, so you have proof.",
  },
];

// Where each step begins, for the progress bars. The last entry is the end.
const STARTS = [0, 34, 90, 140, FRAMES - 1];

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
      player.load(frame.current); // on screen already, so don't wait for the page to finish loading
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
    const load = () => player.load(frame.current);
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
    return () => {
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
    <section id="story" ref={section} className="relative h-[600vh]" aria-label="How the box comes together">
      <div ref={pinned} data-pin className="sticky top-0 flex h-svh items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-4 px-6 lg:grid-cols-[1fr_1.25fr] lg:gap-12">
          <div className="order-2 lg:order-1">
          <div className="relative h-48 lg:h-72">
            {steps.map((step, k) => (
              <div
                key={step.title}
                ref={(el) => {
                  captions.current[k] = el;
                }}
                data-caption
                // Prepaint sets its style before React loads.
                suppressHydrationWarning
                className="absolute inset-x-0 bottom-0 opacity-0 will-change-transform"
              >
                <p className="text-sm font-medium uppercase tracking-widest text-emerald-600">
                  Step {k + 1}
                </p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-900 sm:text-5xl">
                  {step.title}
                </h2>
                <p className="mt-4 max-w-md text-lg leading-relaxed text-zinc-500 sm:text-xl">{step.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex gap-2" aria-hidden="true">
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
          <div
            role="img"
            aria-label="A small Raspberry Pi computer is closed inside a white box. An internet cable and a power cable plug in, and a green light turns on."
            className="relative order-1 mx-auto aspect-square w-full max-w-[min(100%,60svh)] lg:order-2 lg:max-w-[min(100%,80svh)]"
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
    </section>
    <Prepaint />
    </>
  );
}
