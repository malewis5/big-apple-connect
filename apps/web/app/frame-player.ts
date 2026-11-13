// Plays the scroll story's pre-rendered frames on a canvas.
//
// Frames come from scripts/build-frames.mjs in several sizes. Each visitor
// downloads one size, chosen for their screen and connection, coarse to fine:
// a handful of frames spread across the story first, then the gaps. Whatever
// has arrived is playable, so a slow phone sees a working story early and it
// fills in as the rest lands. Only frames near the scroll position are kept
// decoded, which bounds memory on phones.

import manifest from "./story-frames.json";

export const FRAMES = manifest.frames;
const SIZES = manifest.sizes;
const BASE = `/story/${manifest.version}`;

const PARALLEL = 4; // downloads in flight
const NEARBY = 8; // frames kept decoded on each side of the current one
const ANCHOR = 24; // every Nth frame stays decoded, as a fallback when scrolling fast
const SLOW_BYTES_PER_SECOND = 60_000; // about 0.5 Mbps: below this, skip every other frame

export function frameUrl(size: number, frame: number) {
  return `${BASE}/${size}/${String(frame).padStart(3, "0")}.webp`;
}

// srcset for the first frame, shown when scripts are off.
export const POSTER_SRCSET = SIZES.map((size) => `${frameUrl(size, 0)} ${size}w`).join(", ");
export const POSTER_SRC = frameUrl(SIZES[1] ?? SIZES[0], 0);

type Connection = { saveData?: boolean; effectiveType?: string };

// The smallest size that stays sharp at the canvas's size on screen, one step
// smaller on slow or data-saving connections.
function chooseSize(cssWidth: number) {
  const connection = (navigator as Navigator & { connection?: Connection }).connection;
  const slow = Boolean(connection?.saveData) || /2g|3g/.test(connection?.effectiveType ?? "");
  const needed = cssWidth * Math.min(window.devicePixelRatio || 1, 2);
  let k = SIZES.findIndex((size) => size >= needed * 0.85);
  if (k < 0) k = SIZES.length - 1;
  if (slow) k = Math.max(0, k - 1);
  return { size: SIZES[k], slow };
}

// Every frame, coarse to fine: every 32nd, then every 16th, and so on. The
// frames around `from` come first, so a page reloaded mid-story shows the
// right picture straight away.
function downloadOrder(from: number) {
  const order = [from, from - 1, from + 1, from - 2, from + 2].filter((f) => f >= 0 && f < FRAMES);
  for (const f of [0, FRAMES - 1]) if (!order.includes(f)) order.push(f);
  for (let stride = 32; stride >= 1; stride /= 2) {
    for (let f = 0; f < FRAMES; f += stride) if (!order.includes(f)) order.push(f);
  }
  return order;
}

export class FramePlayer {
  private readonly context: CanvasRenderingContext2D;
  private readonly size: number;
  private readonly blobs: (Blob | undefined)[] = [];
  private readonly bitmaps: (ImageBitmap | undefined)[] = [];
  private readonly decoding = new Set<number>();
  private readonly abort = new AbortController();
  private skipOdd: boolean;
  private center = 0;
  private drawn = -1;
  private loading: "no" | "one" | "all" = "no";
  private queue: number[] = [];

  constructor(
    canvas: HTMLCanvasElement,
    private readonly onChange: () => void,
  ) {
    const { size, slow } = chooseSize(canvas.clientWidth || canvas.parentElement?.clientWidth || 720);
    this.size = size;
    this.skipOdd = slow;
    canvas.width = canvas.height = size;
    this.context = canvas.getContext("2d")!;
  }

  // Start downloading, nearest `from` first. Safe to call more than once.
  // With `only`, download just that frame, for when the story stands still;
  // a later call without it downloads the rest.
  load(from: number, only = false) {
    if (this.loading === "all" || (only && this.loading === "one")) return;
    this.loading = only ? "one" : "all";
    const first = Math.round(from);
    const queue = (this.queue = only ? [first] : downloadOrder(first).filter((f) => !this.blobs[f]));
    const started = performance.now();
    let received = 0;
    const next = async (): Promise<void> => {
      let f = queue.shift();
      while (f !== undefined && this.skipOdd && f % 2 === 1 && f !== FRAMES - 1) f = queue.shift();
      if (f === undefined || this.abort.signal.aborted) return;
      try {
        const response = await fetch(frameUrl(this.size, f), { signal: this.abort.signal });
        if (!response.ok) throw new Error(String(response.status));
        const blob = await response.blob();
        this.blobs[f] = blob;
        received += blob.size;
        // On a slow connection, settle for every other frame.
        const seconds = (performance.now() - started) / 1000;
        if (seconds > 2 && received / seconds < SLOW_BYTES_PER_SECOND) this.skipOdd = true;
        this.decodeNearby();
      } catch {
        if (this.abort.signal.aborted) return;
      }
      return next();
    };
    for (let k = 0; k < PARALLEL; k++) void next();
  }

  dispose() {
    this.abort.abort();
    this.bitmaps.forEach((bitmap) => bitmap?.close());
    this.bitmaps.length = 0;
    this.blobs.length = 0;
  }

  private wanted(f: number) {
    return Math.abs(f - this.center) <= NEARBY || f % ANCHOR === 0 || f === FRAMES - 1;
  }

  // Decode downloaded frames near the current one, nearest first, and free
  // the ones that drifted out of range.
  private decodeNearby() {
    // A decode that finishes after dispose() calls back in here; without this
    // it would decode, close and retry the same frames forever.
    if (this.abort.signal.aborted) return;
    this.bitmaps.forEach((bitmap, f) => {
      if (bitmap && !this.wanted(f)) {
        bitmap.close();
        this.bitmaps[f] = undefined;
      }
    });
    const candidates: number[] = [];
    for (let f = 0; f < FRAMES; f++) {
      if (this.blobs[f] && !this.bitmaps[f] && !this.decoding.has(f) && this.wanted(f)) candidates.push(f);
    }
    candidates.sort((a, b) => Math.abs(a - this.center) - Math.abs(b - this.center));
    for (const f of candidates.slice(0, Math.max(0, 3 - this.decoding.size))) {
      this.decoding.add(f);
      createImageBitmap(this.blobs[f]!)
        .then((bitmap) => {
          if (this.abort.signal.aborted || !this.wanted(f)) bitmap.close();
          else {
            this.bitmaps[f] = bitmap;
            this.onChange();
          }
        })
        .catch(() => {})
        .finally(() => {
          this.decoding.delete(f);
          this.decodeNearby();
        });
    }
  }

  // Draw the decoded frame nearest the scroll position. Always a single,
  // sharp frame: blending neighbours reads as motion blur.
  draw(frame: number) {
    const center = Math.round(frame);
    if (center !== this.center) {
      this.center = center;
      this.decodeNearby();
    }
    let nearest = -1;
    for (let d = 0; d < FRAMES; d++) {
      if (this.bitmaps[center - d]) nearest = center - d;
      else if (this.bitmaps[center + d]) nearest = center + d;
      if (nearest >= 0) break;
    }
    if (nearest < 0 || nearest === this.drawn) return;
    this.drawn = nearest;
    this.context.drawImage(this.bitmaps[nearest]!, 0, 0, this.size, this.size);
  }

  // Download the frames around `frame` next, after a jump (a reload that
  // restores the scroll position, or a link into the story).
  prioritize(frame: number) {
    const f = Math.round(frame);
    const near = [f, f - 1, f + 1, f - 2, f + 2].filter((k) => this.queue.includes(k));
    this.queue.splice(0, this.queue.length, ...near, ...this.queue.filter((k) => !near.includes(k)));
  }

  get hasDrawn() {
    return this.drawn >= 0;
  }
}
