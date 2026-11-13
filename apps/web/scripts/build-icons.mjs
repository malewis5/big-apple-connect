// Builds app/favicon.ico and app/apple-icon.png from app/icon.svg.
// Run with `pnpm build:icons` after changing the icon.
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const app = fileURLToPath(new URL("../app/", import.meta.url));
const svg = await readFile(`${app}icon.svg`);

const png = (size, input = svg) => sharp(input, { density: 72 * (size / 32) }).resize(size, size).png().toBuffer();

// favicon.ico: 16, 32 and 48 pixel PNGs in one ICO container.
const sizes = [16, 32, 48];
const images = await Promise.all(sizes.map((size) => png(size)));
const header = Buffer.alloc(6 + 16 * images.length);
header.writeUInt16LE(0, 0); // reserved
header.writeUInt16LE(1, 2); // type: icon
header.writeUInt16LE(images.length, 4);
let offset = header.length;
images.forEach((image, i) => {
  const entry = 6 + 16 * i;
  header.writeUInt8(sizes[i], entry); // width
  header.writeUInt8(sizes[i], entry + 1); // height
  header.writeUInt16LE(1, entry + 4); // color planes
  header.writeUInt16LE(32, entry + 6); // bits per pixel
  header.writeUInt32LE(image.length, entry + 8);
  header.writeUInt32LE(offset, entry + 12);
  offset += image.length;
});
await writeFile(`${app}favicon.ico`, Buffer.concat([header, ...images]));

// apple-icon.png: iOS rounds the corners itself, so fill the whole square.
const square = Buffer.from(svg.toString().replace('rx="7"', 'rx="0"'));
await writeFile(`${app}apple-icon.png`, await png(180, square));

console.log("Wrote app/favicon.ico and app/apple-icon.png");
