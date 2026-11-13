"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";

const BoxScene = dynamic(() => import("./box-scene"), { ssr: false });

// CSS pixels; the canvas renders at twice this.
export const SIZE = 1440;

declare global {
  interface Window {
    captureFrame?: (frame: number) => string;
  }
}

// Renders the box at any frame on request, for scripts/build-frames.mjs.
export default function Capture() {
  const frame = useRef(0);
  const render = useRef<(() => void) | null>(null);
  const [ready, setReady] = useState(false);
  const onRenderer = useCallback((fn: () => void) => {
    render.current = fn;
  }, []);
  const onReady = useCallback(() => setReady(true), []);

  useEffect(() => {
    if (!ready) return;
    window.captureFrame = (f) => {
      frame.current = f;
      // Twice, so effects that lag a frame (the contact shadow) catch up.
      render.current?.();
      render.current?.();
      return document.querySelector("canvas")!.toDataURL("image/png");
    };
    document.body.dataset.ready = "true";
  }, [ready]);

  return (
    <div style={{ width: SIZE, height: SIZE }}>
      <BoxScene frame={frame} size={SIZE} onRenderer={onRenderer} onReady={onReady} />
    </div>
  );
}
