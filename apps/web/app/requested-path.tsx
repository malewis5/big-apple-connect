"use client";

import { usePathname } from "next/navigation";

// The address the visitor asked for, shown on the 404 page's test result.
// Kept tiny: the root not-found page ships with every route.
export function RequestedPath() {
  return <>{usePathname()}</>;
}
