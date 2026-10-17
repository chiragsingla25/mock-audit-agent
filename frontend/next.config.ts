import type { NextConfig } from "next";

// NEXT_PUBLIC_MODE=showcase builds the static GitHub Pages site (spec Phase 6); live mode is the local app.
const showcase = process.env.NEXT_PUBLIC_MODE === "showcase";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  // Partial prerendering (cacheComponents / partialPrefetching) can't be used with a static export.
  ...(showcase
    ? { output: "export" as const, basePath, trailingSlash: true, images: { unoptimized: true } }
    : { cacheComponents: true, partialPrefetching: true }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
