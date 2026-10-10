import type { NextConfig } from "next";

// Static export served by FastAPI at /dashboard (see ../backend/app/main.py).
// No dynamic route segments: detail pages use query params (?id=...).
const nextConfig: NextConfig = {
  output: "export",
  basePath: "/dashboard",
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
