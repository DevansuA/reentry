/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api/* to the FastAPI server so the browser never touches a
  // CDN or external host — everything stays on localhost.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
