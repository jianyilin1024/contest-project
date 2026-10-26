import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 生成独立产物，便于 Docker 镜像瘦身
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,

  // 功能模块合并后，旧链接仍然可用——避免用户收藏夹或外部引用失效
  async redirects() {
    return [
      { source: "/features/transition", destination: "/features/merge/transition", permanent: true },
      { source: "/features/style", destination: "/features/merge/style", permanent: true },
      { source: "/features/references", destination: "/features/citations/search", permanent: true },
      { source: "/features/data", destination: "/features/citations/data", permanent: true },
    ];
  },
};

export default nextConfig;
