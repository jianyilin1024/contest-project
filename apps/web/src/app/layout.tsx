import type { Metadata } from "next";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "大肥鱼小组工作台 · AI 协作写作与论文助手",
    template: "%s · 大肥鱼小组工作台",
  },
  description:
    "整合小组成员的分工内容，统一用语风格，辅助数据检索与参考文献查找，并自动完成论文排版。",
  keywords: ["小组作业", "论文协作", "AI 写作", "参考文献", "论文排版"],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className="flex min-h-screen flex-col font-sans text-slate-900 antialiased">
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
