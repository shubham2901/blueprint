import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/explore/new", destination: "/research/explore/new", permanent: true },
      { source: "/explore/:journeyId", destination: "/research/explore/:journeyId", permanent: true },
      { source: "/dashboard", destination: "/research/dashboard", permanent: true },
    ];
  },
  async rewrites() {
    // Use internal URL for Railway (server-to-server), otherwise fall back to public API URL or localhost
    const backendUrl =
      (process.env.BACKEND_INTERNAL_URL && process.env.BACKEND_INTERNAL_URL.trim()) ||
      (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim()) ||
      "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
