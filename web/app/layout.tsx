import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "EDGE — Positive-EV Finder",
  description:
    "A daily, ranked board of positive expected-value bets with a plain-English reason for each. Decision support — not betting advice.",
};

export const viewport: Viewport = {
  themeColor: "#060810",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
