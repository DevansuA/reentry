/** @type {import('next').NextConfig} */
const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const nextConfig = {
  images: {
    // Screenshots are served from /public/screenshots/ — no remote hosts needed.
    unoptimized: false,
  },
  async rewrites() {
    // In demo mode the Next.js API routes in src/app/api/ handle all /api/*
    // requests using the pre-generated snapshot; no FastAPI server is needed.
    if (isDemoMode) return [];

    // In local mode proxy /api/* to the FastAPI server so the browser never
    // touches a CDN or external host — everything stays on localhost.
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
