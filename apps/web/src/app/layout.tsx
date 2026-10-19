import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "参赛项目 · AI 小组作业与论文协作台",
  description:
    "整合小组成员的分工内容，统一用语风格，辅助数据检索与参考文献查找，并自动完成论文排版。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-full font-sans text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
