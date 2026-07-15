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
      {/*
        No CDN fonts, no analytics, no external scripts.
        Inter Variable is served from /fonts/InterVariable.woff2.
      */}
      <head />
      <body>{children}</body>
    </html>
  );
}
