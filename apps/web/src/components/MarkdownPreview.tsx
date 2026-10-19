import type { ReactNode } from "react";

/**
 * 轻量 Markdown 预览。
 * 只渲染本项目合并稿会用到的子集（标题、段落、列表、引用、表格、加粗），
 * 因此不引入额外依赖，也不会因为输入任意 HTML 而产生安全问题。
 */

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.filter(Boolean).map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={key}>{part}</span>;
  });
}

const HEADING_CLASS: Record<number, string> = {
  1: "mt-0 mb-3 text-2xl font-extrabold text-slate-900",
  2: "mt-7 mb-2.5 text-xl font-bold text-slate-900",
  3: "mt-6 mb-2 text-base font-bold text-slate-800",
  4: "mt-5 mb-2 text-sm font-bold text-slate-800",
  5: "mt-4 mb-1.5 text-sm font-semibold text-slate-700",
  6: "mt-4 mb-1.5 text-sm font-semibold text-slate-700",
};

export function MarkdownPreview({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n");
  const blocks: ReactNode[] = [];
  let listBuffer: string[] = [];
  let tableBuffer: string[] = [];

  const flushList = (key: string) => {
    if (listBuffer.length === 0) return;
    blocks.push(
      <ul key={key} className="my-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {listBuffer.map((item, index) => (
          <li key={index}>{renderInline(item, `${key}-${index}`)}</li>
        ))}
      </ul>,
    );
    listBuffer = [];
  };

  const flushTable = (key: string) => {
    if (tableBuffer.length === 0) return;
    const rows = tableBuffer
      .filter((row) => !/^\s*\|[\s:|-]+\|\s*$/.test(row))
      .map((row) => row.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()));
    blocks.push(
      <div key={key} className="my-3 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <tbody>
            {rows.map((cells, rowIndex) => (
              <tr key={rowIndex} className={rowIndex === 0 ? "bg-slate-50 font-medium" : ""}>
                {cells.map((cell, cellIndex) => (
                  <td key={cellIndex} className="border border-slate-200 px-3 py-1.5 text-slate-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    );
    tableBuffer = [];
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trimEnd();
    const key = `b${index}`;

    if (!line.trim()) {
      flushList(key + "-l");
      flushTable(key + "-t");
      return;
    }
    if (/^\s*\|.*\|\s*$/.test(line)) {
      flushList(key + "-l");
      tableBuffer.push(line);
      return;
    }
    flushTable(key + "-t");

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushList(key + "-l");
      const level = heading[1].length;
      const Tag = `h${level}` as keyof React.JSX.IntrinsicElements;
      blocks.push(
        <Tag key={key} className={HEADING_CLASS[level]}>
          {heading[2]}
        </Tag>,
      );
      return;
    }

    const item = /^\s*(?:[-*+])\s+(.*)$/.exec(line);
    if (item) {
      listBuffer.push(item[1]);
      return;
    }
    flushList(key + "-l");

    const quote = /^\s*>\s?(.*)$/.exec(line);
    if (quote) {
      blocks.push(
        <blockquote
          key={key}
          className="my-3 border-l-4 border-indigo-200 bg-indigo-50/40 px-4 py-2 text-sm text-slate-600"
        >
          {renderInline(quote[1], key)}
        </blockquote>,
      );
      return;
    }

    blocks.push(
      <p key={key} className="my-2 text-sm leading-7 text-slate-700">
        {renderInline(line, key)}
      </p>,
    );
  });

  flushList("tail-l");
  flushTable("tail-t");

  return <div className="text-slate-800">{blocks}</div>;
}
