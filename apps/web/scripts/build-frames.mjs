// Render the scroll story's frames from the 3D scene in app/capture.
//
//   pnpm --filter web build:frames
//
// Starts `next dev` (or uses the one running), opens /capture in Chrome, captures every frame of the
// box animation at 2880 px, and writes WebP frames in several sizes to
// public/story/<version>/<size>/<frame>.webp, plus app/story-frames.json,
// which tells the website what exists. <version> is a hash of the frames, so
// they can be cached forever. Needs Google Chrome installed.

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import sharp from "sharp";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "public", "story");
const MANIFEST = path.join(ROOT, "app", "story-frames.json");
const PORT = 3999;
const FRAMES = 180; // the length of the animation in design/box/build_box.py
const SIZES = [480, 720, 1080, 1440]; // square, in pixels
const QUALITY = 80;
const EDGE = 0.1; // fade this share of each edge into the white page

// Start `next dev`, or use the one already running for this app (Next.js
// allows only one). Resolves to its URL and a function that stops it if we
// started it.
function startServer() {
  const server = spawn(path.join(ROOT, "node_modules", ".bin", "next"), ["dev", "-p", String(PORT)], {
    cwd: ROOT,
    stdio: ["ignore", "pipe", "pipe"],
  });
  return new Promise((resolve, reject) => {
    let output = "";
    let poll = 0;
    const done = (value) => {
      clearInterval(poll);
      resolve(value);
    };
    const read = (chunk) => {
      output += chunk;
      const existing = output.match(/existing server at (http:\/\/\S+?),?\s/);
      if (existing) done({ url: existing[1], stop: () => {} });
    };
    // "Ready" prints before Next.js checks for another dev server, so wait
    // until our port actually answers.
    const url = `http://localhost:${PORT}`;
    poll = setInterval(() => {
      fetch(`${url}/capture`)
        .then((response) => {
          if (response.ok) done({ url, stop: () => server.kill() });
        })
        .catch(() => {});
    }, 500);
    server.stdout.on("data", read);
    server.stderr.on("data", read);
    server.on("exit", (code) => {
      clearInterval(poll);
      read("\n");
      reject(new Error(`next dev exited with ${code}:\n${output}`));
    });
  });
}

// White gradients over each edge, so the arriving case and the cables fade
// into the page instead of meeting a hard border.
function edgeFade(size) {
  const e = size * EDGE;
  const stops = '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
    <defs>
      <linearGradient id="t" x1="0" y1="0" x2="0" y2="1">${stops}</linearGradient>
      <linearGradient id="b" x1="0" y1="1" x2="0" y2="0">${stops}</linearGradient>
      <linearGradient id="l" x1="0" y1="0" x2="1" y2="0">${stops}</linearGradient>
      <linearGradient id="r" x1="1" y1="0" x2="0" y2="0">${stops}</linearGradient>
    </defs>
    <rect width="${size}" height="${e}" fill="url(#t)"/>
    <rect y="${size - e}" width="${size}" height="${e}" fill="url(#b)"/>
    <rect width="${e}" height="${size}" fill="url(#l)"/>
    <rect x="${size - e}" width="${e}" height="${size}" fill="url(#r)"/>
  </svg>`;
  return Buffer.from(svg);
}

async function main() {
  const tmp = path.join(OUT, ".tmp");
  await rm(tmp, { recursive: true, force: true });
  await Promise.all(SIZES.map((size) => mkdir(path.join(tmp, String(size)), { recursive: true })));

  console.log("Starting next dev…");
  const server = await startServer();
  console.log(`Capturing from ${server.url}`);
  const browser = await chromium.launch({ channel: "chrome", args: ["--enable-gpu", "--ignore-gpu-blocklist"] });
  const hash = createHash("sha256");
  const bytes = Object.fromEntries(SIZES.map((size) => [size, 0]));
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1500 } });
    page.on("pageerror", (error) => console.error(error));
    await page.goto(`${server.url}/capture`);
    await page.waitForSelector("body[data-ready]", { state: "attached", timeout: 120_000 });

    let fade = null;
    for (let f = 0; f < FRAMES; f++) {
      const url = await page.evaluate((frame) => window.captureFrame(frame), f);
      const png = Buffer.from(url.slice(url.indexOf(",") + 1), "base64");
      const master = sharp(png);
      const { width } = await master.metadata();
      fade ??= await sharp(edgeFade(width)).png().toBuffer();
      const faded = await master.composite([{ input: fade }]).flatten({ background: "#ffffff" }).png().toBuffer();
      const name = `${String(f).padStart(3, "0")}.webp`;
      for (const size of SIZES) {
        const webp = await sharp(faded)
          .resize(size, size, { kernel: "lanczos3" })
          .webp({ quality: QUALITY, effort: 6, smartSubsample: true })
          .toBuffer();
        hash.update(webp);
        bytes[size] += webp.length;
        await writeFile(path.join(tmp, String(size), name), webp);
      }
      process.stdout.write(`\rFrame ${f + 1}/${FRAMES}`);
    }
    process.stdout.write("\n");
  } finally {
    await browser.close();
    server.stop();
  }

  // Swap in the new frames and remove older versions.
  const version = hash.digest("hex").slice(0, 10);
  for (const entry of await readdir(OUT)) {
    if (entry !== ".tmp") await rm(path.join(OUT, entry), { recursive: true, force: true });
  }
  await rename(tmp, path.join(OUT, version));
  const manifest = { version, frames: FRAMES, sizes: SIZES, bytes };
  await writeFile(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`);
  for (const size of SIZES) console.log(`${size}px: ${(bytes[size] / 1e6).toFixed(2)} MB`);
  console.log(`Wrote public/story/${version}/ and app/story-frames.json`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
