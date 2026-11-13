"use client";

import { useEffect, useRef, useState } from "react";
import { SITE_NAME, demoVideo, hero } from "./site";
import { CARD, CONTAINER, SECTION_LEAD, SECTION_TITLE, SECTION_Y } from "./ui";

// AV1 at 1080p is the smallest, for browsers that can play it; H.264 at 720p
// plays everywhere.
const DEMO_VIDEO = demoVideo.files;

// Many people reading this page are on the connection they want to check, so
// the video costs nothing until it's wanted. It downloads only once it's on
// screen, and it never starts by itself for people who ask their device for
// less motion or to save data.
function mayAutoplay() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } })
    .connection;
  if (connection?.saveData) return false;
  if (connection?.effectiveType && /(^|-)2g$/.test(connection.effectiveType)) return false;
  return true;
}

function setTrackMode(track: TextTrack, mode: TextTrackMode) {
  track.mode = mode;
}

export default function DemoVideo() {
  const video = useRef<HTMLVideoElement>(null);
  const [caption, setCaption] = useState(""); // kept while it fades out
  const [captionShown, setCaptionShown] = useState(false);
  // It plays once, then rests on its last frame with a button to play again.
  const [ended, setEnded] = useState(false);

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    const onEnded = () => setEnded(true);
    const onPlay = () => setEnded(false);
    el.addEventListener("ended", onEnded);
    el.addEventListener("play", onPlay);
    return () => {
      el.removeEventListener("ended", onEnded);
      el.removeEventListener("play", onPlay);
    };
  }, []);

  function playAgain() {
    const el = video.current;
    if (!el) return;
    el.currentTime = 0;
    el.play().catch(() => {});
  }

  // Play while on screen, pause when scrolled away.
  useEffect(() => {
    const el = video.current;
    if (!el || !mayAutoplay()) return;
    // Once someone pauses it themselves, or it reaches the end, leave it
    // paused until they press play again.
    let userPaused = false;
    let ours = false; // the next pause event is one we caused
    const onPause = () => {
      if (ours) ours = false;
      else userPaused = true;
    };
    const onPlay = () => {
      userPaused = false;
    };
    el.addEventListener("pause", onPause);
    el.addEventListener("play", onPlay);
    const seen = new IntersectionObserver(
      ([entry]) => {
        if (userPaused) return;
        if (entry.isIntersecting) {
          el.play().catch(() => {}); // a browser may still refuse; the controls remain
        } else if (!el.paused) {
          ours = true;
          el.pause();
        }
      },
      { threshold: 0.5 },
    );
    seen.observe(el);
    return () => {
      seen.disconnect();
      el.removeEventListener("pause", onPause);
      el.removeEventListener("play", onPlay);
    };
  }, []);

  // Captions in the page's own style. Browsers draw captions their own way
  // (Chrome ignores a caption background), so the track runs hidden and the
  // page draws each line as the same white pill as the shared copies. In
  // full screen, where nothing of the page shows, the browser draws them.
  // Turning captions off in the player's menu turns the pill off too.
  useEffect(() => {
    const el = video.current;
    const track = el?.textTracks[0];
    if (!el || !track) return;
    let on = true;
    const fullScreen = () =>
      document.fullscreenElement === el || (el as HTMLVideoElement & { webkitDisplayingFullscreen?: boolean }).webkitDisplayingFullscreen;
    const show = () => {
      const cue = track.activeCues?.[0] as VTTCue | undefined;
      const visible = on && !fullScreen() && !!cue;
      if (visible) setCaption(cue.text);
      setCaptionShown(visible);
    };
    const sync = () => {
      if (track.mode === "disabled") on = false;
      else on = true;
      const want = on && fullScreen() ? "showing" : on ? "hidden" : "disabled";
      if (track.mode !== want) setTrackMode(track, want); // fires change again, which then matches
      show();
    };
    sync();
    track.addEventListener("cuechange", show);
    el.textTracks.addEventListener("change", sync);
    document.addEventListener("fullscreenchange", sync);
    el.addEventListener("webkitbeginfullscreen", sync);
    el.addEventListener("webkitendfullscreen", sync);
    return () => {
      track.removeEventListener("cuechange", show);
      el.textTracks.removeEventListener("change", sync);
      document.removeEventListener("fullscreenchange", sync);
      el.removeEventListener("webkitbeginfullscreen", sync);
      el.removeEventListener("webkitendfullscreen", sync);
    };
  }, []);

  return (
    // Lined up with the other sections. On a wide screen the words take the
    // left third and the video the rest, the same split as the questions
    // below, so the two fit on one screen together; on a narrow one the video
    // sits under the words at full width.
    <section id="demo" aria-labelledby="demo-title" className={`bg-white ${SECTION_Y}`}>
      <div className={`${CONTAINER} lg:grid lg:grid-cols-[1fr_2fr] lg:items-center lg:gap-16`}>
        <div>
          <h2 id="demo-title" className={SECTION_TITLE}>
            {demoVideo.title}
          </h2>
          <p className={SECTION_LEAD}>{demoVideo.body}</p>
        </div>
        <div className={`relative mt-12 w-full min-w-0 overflow-hidden [container-type:inline-size] lg:mt-0 ${CARD}`}>
          <video
            ref={video}
            className="block aspect-video w-full"
            width={1920}
            height={1080}
            poster={DEMO_VIDEO.poster}
            preload="none"
            muted
            playsInline
            controls={!ended}
            aria-label={demoVideo.label}
          >
            <source src={DEMO_VIDEO.webm} type='video/webm; codecs="av01.0.08M.10"' />
            <source src={DEMO_VIDEO.mp4} type="video/mp4" />
            <track src={DEMO_VIDEO.captions} kind="captions" srcLang="en" label="English" default />
            <p className="p-6 text-zinc-600">
              If your browser can&apos;t play this video, you can{" "}
              <a href={DEMO_VIDEO.mp4} className="underline">
                download it
              </a>{" "}
              instead.
            </p>
          </video>
          {/* Sized to the video's width, like the captions in the shared copies:
              about 2.4% of the width, a little larger on small screens. The
              words are also in the track and on the Markdown page. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 bottom-[16%] flex justify-center px-[4%]"
          >
            <p
              className={`max-w-full rounded-full bg-white/95 px-[1.1em] py-[0.45em] text-center text-[max(0.8rem,2.4cqw)] leading-snug font-medium text-pretty text-zinc-900 shadow-sm transition-opacity duration-300 motion-reduce:transition-none ${captionShown ? "opacity-100" : "opacity-0"}`}
            >
              {caption || "\u00a0"}
            </p>
          </div>
          {/* The end: like the end card in the shared copies, a soft cream
              wash with the site's question and a way to play it again. The
              player's own controls hide meanwhile, so their dark bar doesn't
              cut across it. */}
          {ended && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-[3cqw] bg-[#FBF8F3]/85 px-[6%] text-center backdrop-blur-sm">
              <p className="flex items-center gap-2.5 text-[max(0.75rem,1.6cqw)] font-semibold text-zinc-600">
                <span
                  aria-hidden="true"
                  className="size-2.5 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgb(16_185_129/0.15)]"
                />
                {SITE_NAME}
              </p>
              <p className="text-[max(1.25rem,4.2cqw)] leading-tight font-semibold tracking-tight text-balance text-zinc-900">
                {hero.title}
              </p>
              <button
                type="button"
                onClick={playAgain}
                className="inline-flex min-h-11 items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm ring-1 ring-zinc-900/10 transition hover:bg-zinc-50"
              >
                <svg
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                  className="size-4 text-emerald-600"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3.5 10a6.5 6.5 0 1 0 2-4.7" />
                  <path d="M3.5 3.5v3.5H7" />
                </svg>
                Play again
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
