import type { IconName } from "@/components/Icons";

export type FeatureStatus = "planned" | "building" | "done";

export type Feature = {
  /** 功能编号，如 F1 */
  code: string;
  /** URL 片段，如 /features/merge */
  slug: string;
  title: string;
  /** 首页卡片上的一句话简介 */
  tagline: string;
  /** 详情页的完整描述 */
  description: string;
  icon: IconName;
  /** Tailwind 渐变色，用于图标底板 */
  accent: string;
  /** 所属实施阶段 */
  stage: string;
  status: FeatureStatus;
  /** 计划具备的能力 */
  capabilities: string[];
  input: string;
  output: string;
  /** 是否已有独立实现的页面（有则不再走通用的 [slug] 占位页） */
  dedicated?: boolean;
};

export const FEATURES: Feature[] = [
  {
    code: "F1",
    slug: "merge",
    title: "多部分整合",
    tagline: "把成员各自写的章节合成一份结构统一的文稿。",
    description:
      "小组成员分头写作时，标题层级、编号方式、段落结构往往各不相同。多部分整合负责把它们收拢成一份可继续编辑的完整文稿，并在合并过程中标出重复内容与相互冲突的说法。",
    icon: "layers",
    accent: "from-indigo-500 to-blue-500",
    stage: "P5",
    status: "done",
    dedicated: true,
    capabilities: [
      "支持 docx / Markdown / 纯文本导入",
      "自动识别并归一标题层级与编号",
      "重复段落检测与冲突标记",
      "合并结果可整篇预览，并可直接送入排版导出",
    ],
    input: "多名成员提交的分部文稿",
    output: "结构完整的单一文稿 + 冲突报告",
  },
  {
    code: "F2",
    slug: "tasks",
    title: "分工记录",
    tagline: "谁负责哪一节、进度如何、什么时候交，一目了然。",
    description:
      "把分工从聊天记录里搬到看板上：每名成员认领章节、更新状态、设置截止时间。逾期任务会被标红提醒，并按成员统计完成情况，汇报时可直接展示。",
    icon: "checkSquare",
    accent: "from-emerald-500 to-teal-500",
    stage: "P6",
    status: "done",
    dedicated: true,
    capabilities: [
      "成员与角色管理（组长 / 成员）",
      "任务看板：待办 / 进行中 / 已完成",
      "截止时间提醒与进度可视化",
      "按成员统计完成数与逾期数",
    ],
    input: "成员名单与任务分配",
    output: "分工看板 + 成员进度统计",
  },
  {
    code: "F3",
    slug: "transition",
    title: "过渡段落生成",
    tagline: "在拼接处补写衔接文字，让文章读起来是一个人写的。",
    description:
      "章节直接拼接会产生语义断层。该模块分析相邻两节的内容关系，生成二到三个不同语气的过渡段落，承接上文结论并引出下文议题，可一键接受、换个备选，或自己改写。",
    icon: "link",
    accent: "from-amber-500 to-orange-500",
    stage: "P7",
    status: "done",
    dedicated: true,
    capabilities: [
      "识别章节之间的语义断点",
      "生成 1–2 段衔接文字",
      "明确承接上文、引出下文",
      "支持一键接受、切换备选，或自己改写",
    ],
    input: "相邻两节的正文内容",
    output: "衔接段落建议（可直接插入）",
  },
  {
    code: "F4",
    slug: "style",
    title: "用语风格统一",
    tagline: "统一术语与行文风格，并给出逐句修改对照。",
    description:
      "把全篇改写为统一的学术书面语：去掉口语与主观表述，统一术语与标点。逐段给出原文与改写对照，可逐段接受或回退；未改动的段落自动不勾选，避免无谓确认。",
    icon: "wand",
    accent: "from-fuchsia-500 to-purple-500",
    stage: "P8",
    status: "done",
    dedicated: true,
    capabilities: [
      "逐段改写为统一的学术书面语",
      "左右对照展示原文与改写结果",
      "每段可单独接受或回退，附改动说明",
      "只改语体不改事实，未改动的段落不勾选",
    ],
    input: "需要统一的正文",
    output: "改写稿 + 逐段对照",
  },
  {
    code: "F5",
    slug: "format",
    title: "AI 辅助排版",
    tagline: "套用模板生成规范文稿：标题、目录、页码、参考文献。",
    description:
      "排版是最耗时的收尾工作。该模块以结构化文稿为输入，套用学校或竞赛模板输出规范文档，自动生成目录与页码，并按 GB/T 7714-2015 格式化参考文献。",
    icon: "layout",
    accent: "from-sky-500 to-cyan-500",
    stage: "P9",
    status: "done",
    dedicated: true,
    capabilities: [
      "模板化排版（标题层级 / 字体 / 行距）",
      "自动生成目录与页码",
      "参考文献按 GB/T 7714-2015 编号",
      "导出 docx（在 Word / WPS 中可另存 PDF）",
    ],
    input: "结构化文稿 + 排版模板",
    output: "规范化的 docx 文件",
  },
  {
    code: "F6",
    slug: "data",
    title: "数据助手",
    tagline: "段落里缺的数据，帮你找到可核实的来源。",
    description:
      "识别段落中缺失或存疑的数据点，联网检索并抽取可核实的数据，每条结果都必须附带可点开的来源链接。AI 只做建议，是否采用由你决定。",
    icon: "database",
    accent: "from-rose-500 to-pink-500",
    stage: "P10",
    status: "done",
    dedicated: true,
    capabilities: [
      "识别段落中的数据缺口",
      "联网检索并抽取数据",
      "每条数据附来源链接与原文引用",
      "一键复制数据，来源随结果一并给出",
    ],
    input: "含数据缺口的段落",
    output: "带来源的数据建议",
  },
  {
    code: "F7",
    slug: "references",
    title: "参考文献助手",
    tagline: "按你的概要找到真实存在的文献，并生成标准引用。",
    description:
      "依据论文概要或大纲，从学术库与联网检索中查找真实文献，自动去重并按 GB/T 7714-2015 或 BibTeX 生成引用条目。文献必须真实可访问，杜绝编造。",
    icon: "book",
    accent: "from-violet-500 to-indigo-500",
    stage: "P11",
    status: "done",
    dedicated: true,
    capabilities: [
      "按概要 / 大纲检索相关文献",
      "接入 OpenAlex / Crossref / Open Library / 联网检索",
      "自动去重与相关性排序",
      "同时生成 GB/T 7714 与 BibTeX 条目",
    ],
    input: "论文概要 / 大纲 / 正文段落",
    output: "候选文献列表 + 标准引用条目（两种格式）",
  },
];

export const FEATURE_MAP: Record<string, Feature> = Object.fromEntries(
  FEATURES.map((feature) => [feature.slug, feature]),
);

export const STATUS_LABEL: Record<FeatureStatus, string> = {
  planned: "规划中",
  building: "开发中",
  done: "已完成",
};
