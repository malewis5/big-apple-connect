"use client";

import dynamic from "next/dynamic";
import { Component, type ReactNode, useCallback, useEffect, useRef, useState } from "react";

// WebGL runs only in the browser, so the scene skips server rendering.
const BoxScene = dynamic(() => import("./box-scene"), { ssr: false });

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? null : this.props.children;
  }
}

// The model's motion, from design/box/build_box.py, runs over 180 frames.
const FRAMES = 180;
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

function visibility(frame: number, step: Step) {
  return Math.min(clamp((frame - step.from) / FADE), clamp((step.to - frame) / FADE));
}

export default function BoxStory() {
  const section = useRef<HTMLElement>(null);
  const captions = useRef<(HTMLDivElement | null)[]>([]);
  const bars = useRef<(HTMLSpanElement | null)[]>([]);
  const frame = useRef(0);
  const redraw = useRef<() => void>(() => {});
  const [ready, setReady] = useState(false);

  const onInvalidate = useCallback((fn: () => void) => {
    redraw.current = fn;
    fn();
  }, []);
  const onReady = useCallback(() => setReady(true), []);

  useEffect(() => {
    let raf = 0;

    function update() {
      raf = 0;
      const el = section.current;
      if (!el) return;
      const scrollable = el.offsetHeight - window.innerHeight;
      const progress = clamp(-el.getBoundingClientRect().top / scrollable);
      frame.current = progress * (FRAMES - 1);
      redraw.current();
      captions.current.forEach((caption, k) => {
        if (!caption) return;
        const v = visibility(frame.current, steps[k]);
        caption.style.opacity = String(v);
        caption.style.transform = `translateY(${(1 - v) * 24}px)`;
      });
      bars.current.forEach((bar, k) => {
        if (bar) bar.style.transform = `scaleX(${clamp((frame.current - STARTS[k]) / (STARTS[k + 1] - STARTS[k]))})`;
      });
    }

    function schedule() {
      if (!raf) raf = requestAnimationFrame(update);
    }

    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, []);

  return (
    <section ref={section} className="relative h-[600vh]" aria-label="How the box comes together">
      <div className="sticky top-0 flex h-svh items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-4 px-6 lg:grid-cols-[1fr_1.25fr] lg:gap-12">
          <div className="order-2 lg:order-1">
          <div className="relative h-48 lg:h-72">
            {steps.map((step, k) => (
              <div
                key={step.title}
                ref={(el) => {
                  captions.current[k] = el;
                }}
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
            className={`relative order-1 mx-auto aspect-square w-full max-w-[min(100%,60svh)] transition-opacity duration-700 lg:order-2 lg:max-w-[min(100%,80svh)] ${ready ? "opacity-100" : "opacity-0"}`}
          >
            <SceneBoundary>
              <BoxScene frame={frame} onInvalidate={onInvalidate} onReady={onReady} />
            </SceneBoundary>
            {/* Fade the edges into the white page so the arriving case and the
                cables never meet a hard border. Static white gradients, not a
                CSS mask: a mask over a canvas that redraws every frame is slow
                to composite on iOS. */}
            <div aria-hidden="true" className="pointer-events-none absolute inset-0">
              <div className="absolute inset-x-0 top-0 h-[10%] bg-gradient-to-b from-white" />
              <div className="absolute inset-x-0 bottom-0 h-[10%] bg-gradient-to-t from-white" />
              <div className="absolute inset-y-0 left-0 w-[10%] bg-gradient-to-r from-white" />
              <div className="absolute inset-y-0 right-0 w-[10%] bg-gradient-to-l from-white" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
