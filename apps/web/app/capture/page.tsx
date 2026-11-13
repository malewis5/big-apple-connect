import { notFound } from "next/navigation";
import Capture from "./capture";

// A tool for scripts/build-frames.mjs, not a page: it only exists under
// `next dev`.
export default function CapturePage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <Capture />;
}
