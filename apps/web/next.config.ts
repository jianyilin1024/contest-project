import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 生成独立产物，便于 Docker 镜像瘦身
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
};

export default nextConfig;
