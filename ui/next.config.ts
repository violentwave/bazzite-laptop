import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    // Keep Turbopack rooted to the active UI workspace.
    // This avoids parent-directory lockfile auto-detection warnings.
    root: process.cwd(),
  },
};

export default nextConfig;
