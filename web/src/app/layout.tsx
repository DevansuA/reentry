import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReEntry",
  description: "Return to momentum. A temporal operating system for interrupted knowledge work.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      {/*
        No external fonts, CDN scripts, or analytics. The app works fully
        offline once npm install has run and the FastAPI server is up.
      */}
      <head />
      <body>{children}</body>
    </html>
  );
}
