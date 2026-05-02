import type { NextConfig } from "next";

const isStaticExport = process.env.STATIC_EXPORT === "true";
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "") || undefined;

const nextConfig: NextConfig = {
  ...(isStaticExport
    ? { output: "export" as const, images: { unoptimized: true }, trailingSlash: true }
    : {}),
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

export default nextConfig;
