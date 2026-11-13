import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";
// Preview deployments show the Vercel toolbar, which loads from vercel.live.
const isPreview = process.env.VERCEL_ENV === "preview";
const toolbar = (sources: string) => (isPreview ? ` ${sources}` : "");

// Scripts have to allow 'unsafe-inline': the page is pre-rendered, which
// rules out per-request nonces, and both Next.js and the story's Prepaint
// script run inline. Everything else is locked to this site.
// In development, the capture tool (app/capture) loads its model through
// blob: URLs, the dev server needs eval and its websocket, and Analytics and
// Speed Insights load debug scripts from va.vercel-scripts.com (deployments
// serve them from /_vercel on this site).
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval' https://va.vercel-scripts.com" : ""}${toolbar("https://vercel.live")}`,
  `style-src 'self' 'unsafe-inline'${toolbar("https://vercel.live")}`,
  `img-src 'self' blob: data:${toolbar("https://vercel.live https://vercel.com")}`,
  `font-src 'self'${toolbar("https://vercel.live https://assets.vercel.com")}`,
  `connect-src 'self' blob: data:${isDev ? " ws:" : ""}${toolbar("https://vercel.live wss://ws-us3.pusher.com")}`,
  "worker-src 'self' blob:",
  `frame-src ${isPreview ? "https://vercel.live" : "'none'"}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  headers() {
    return [
      { source: "/:path*", headers: securityHeaders },
      // Story frames live under a folder named for a hash of their contents
      // (scripts/build-frames.mjs), so they never change and can be cached forever.
      {
        source: "/story/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
