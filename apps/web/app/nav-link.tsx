"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";

// A link that tells screen readers, and shows sighted visitors, when it
// points at the page they are on.
export function NavLink({ href, ...props }: ComponentProps<typeof Link> & { href: string }) {
  const current = usePathname() === href;
  return <Link href={href} aria-current={current ? "page" : undefined} {...props} />;
}
