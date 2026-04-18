import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  experimental: {
    // Avoid reusing persisted dev cache across sessions.
    // This mitigates stale chunk/manifest mismatches that can render
    // the UI as unstyled HTML when cached chunks fail with 500.
    turbopackFileSystemCacheForDev: false,
  },
  turbopack: {
    // Keep Turbopack rooted to the active UI workspace.
    // This avoids parent-directory lockfile auto-detection warnings.
    root: __dirname,
  },
};

export default nextConfig;
