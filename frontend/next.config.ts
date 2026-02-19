import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/explore/new", destination: "/research/explore/new", permanent: true },
      { source: "/explore/:journeyId", destination: "/research/explore/:journeyId", permanent: true },
      { source: "/dashboard", destination: "/research/dashboard", permanent: true },
    ];
  },
};

export default nextConfig;
