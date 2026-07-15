import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReEntry",
  description:
    "Return to momentum. A temporal operating system for interrupted knowledge work.",
  openGraph: {
    title: "ReEntry",
    description: "Return to momentum.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/*
          Preload the self-hosted variable font so the browser fetches it
          before parsing the CSS @font-face rule. Eliminates FOIT on LCP.
          No CDN fonts, no analytics, no external scripts.
        */}
        <link
          rel="preload"
          href="/fonts/InterVariable.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
