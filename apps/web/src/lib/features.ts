import type { IconName } from "@/components/Icons";

/**
 * 功能清单：全站唯一数据源。
 *
 * 结构上只有四个模块——"过渡段落"与"风格统一"是多部分整合的子页签，
 * "文献检索""数据补全"与"引用建议"同属引用助手。
 * 这样用户看到的是四件事，而不是七个并列的入口。
 */
export type Feature = {
  /** URL 片段，如 /features/merge */
  slug: string;
  title: string;
  /** 首页与功能页卡片上的一句话简介 */
  tagline: string;
  /** 模块内包含的子能力，用于卡片下方的补充说明 */
  includes?: string[];
  icon: IconName;
  /** Tailwind 渐变色，用于图标底板 */
  accent: string;
};

export const FEATURES: Feature[] = [
  {
    slug: "merge",
    title: "多部分整合",
    tagline: "把成员各自写的章节合成一份结构统一的文稿。",
    includes: ["多部分整合", "单文档分析", "过渡段落", "风格统一"],
    icon: "layers",
    accent: "from-indigo-500 to-blue-500",
  },
  {
    slug: "tasks",
    title: "分工记录",
    tagline: "谁负责哪一节、进度如何、什么时候交，一目了然。",
    icon: "checkSquare",
    accent: "from-emerald-500 to-teal-500",
  },
  {
    slug: "format",
    title: "AI 排版",
    tagline: "套用模板生成规范文稿：标题、目录、页码、参考文献。",
    icon: "layout",
    accent: "from-sky-500 to-cyan-500",
  },
  {
    slug: "citations",
    title: "引用助手",
    tagline: "读出论文里该补引用的地方，给出可核实的文献与来源。",
    includes: ["引用建议", "文献检索", "数据补全"],
    icon: "book",
    accent: "from-violet-500 to-indigo-500",
  },
];
