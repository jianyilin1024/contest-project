"""论文排版引擎：把 Markdown 合并稿渲染成符合中文论文规范的 docx。

关键点：
- 样式全部通过 Word 内置样式（Normal / Heading N）设置，用户后续在 Word 里改模板仍能生效；
- 标题自动编号（1 / 1.1 / 1.1.1），并剥离原文自带的编号，避免出现「1 1 绪论」；
- 目录用 Word 域（TOC）而不是手写目录，配合 updateFields 让 Word 打开时自动填充；
- 页码用 PAGE 域放在页脚。
"""

import io
import re
from dataclasses import dataclass

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# ---------------- 模板 ----------------


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    description: str
    body_font_cn: str = "宋体"
    body_font_en: str = "Times New Roman"
    body_size: float = 12.0  # 小四
    line_spacing: float = 1.5
    first_line_indent: float = 24.0  # 磅，约两个汉字
    heading_font_cn: str = "黑体"
    heading_sizes: tuple[float, float, float] = (16.0, 14.0, 12.0)  # 三号 / 四号 / 小四
    margin_top_cm: float = 2.54
    margin_bottom_cm: float = 2.54
    margin_left_cm: float = 3.17
    margin_right_cm: float = 3.17
    toc: bool = True
    page_numbers: bool = True
    numbering: bool = True


TEMPLATES: dict[str, Template] = {
    "academic": Template(
        key="academic",
        name="通用学术论文",
        description="宋体小四、1.5 倍行距、首行缩进两字符、三级编号、含目录与页码",
    ),
    "course": Template(
        key="course",
        name="课程作业",
        description="宋体小四、1.5 倍行距、两级编号、不含目录，适合篇幅较小的作业",
        heading_sizes=(15.0, 13.0, 12.0),
        toc=False,
    ),
    "contest": Template(
        key="contest",
        name="竞赛报告",
        description="标题更醒目、段前段后留白更大，适合需要视觉层次的参赛文档",
        body_size=12.0,
        line_spacing=1.6,
        heading_sizes=(18.0, 15.0, 13.0),
    ),
}

DEFAULT_TEMPLATE = "academic"

# ---------------- Markdown 解析 ----------------

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_MD_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_MD_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_MD_TABLE_DIVIDER = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_LEADING_NUMBER = re.compile(r"^\s*\d+(?:\.\d+)*[、.．]?\s+")

# 这些章节按惯例不参与编号
_UNNUMBERED_SECTIONS = {
    "参考文献",
    "参考资料",
    "致谢",
    "附录",
    "摘要",
    "abstract",
    "关键词",
    "keywords",
    "目录",
}
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def parse_markdown(markdown: str) -> list[tuple]:
    """把 Markdown 拆成块：(kind, level, text) 或 ("table", 0, rows)。"""
    blocks: list[tuple] = []
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        if table_rows:
            blocks.append(("table", 0, [list(row) for row in table_rows]))
            table_rows.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_table()
            continue
        if _MD_TABLE_ROW.match(line):
            if _MD_TABLE_DIVIDER.match(line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            continue
        flush_table()

        heading = _MD_HEADING.match(line)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2).strip()))
            continue
        quote = _MD_QUOTE.match(line)
        if quote:
            blocks.append(("quote", 0, quote.group(1).strip()))
            continue
        item = _MD_LIST.match(line)
        if item:
            blocks.append(("list", 0, item.group(1).strip()))
            continue
        blocks.append(("paragraph", 0, line.strip()))
    flush_table()
    return blocks


# ---------------- docx 底层工具 ----------------


def _set_cjk_font(style, cn_font: str, en_font: str) -> None:  # noqa: ANN001
    style.font.name = en_font
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), en_font)
    fonts.set(qn("w:hAnsi"), en_font)
    fonts.set(qn("w:eastAsia"), cn_font)


def _set_run_font(run, cn_font: str, en_font: str, size: float | None = None) -> None:  # noqa: ANN001
    """安全地给单个 run 设置中西文字体（rFonts 可能尚未创建）。"""
    run.font.name = en_font
    if size is not None:
        run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), en_font)
    fonts.set(qn("w:hAnsi"), en_font)
    fonts.set(qn("w:eastAsia"), cn_font)


def _add_field(paragraph, instruction: str, placeholder: str = "") -> None:  # noqa: ANN001
    """在段落中插入一个 Word 域（TOC / PAGE 等）。"""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, text, end):
        run._r.append(element)


def _enable_update_fields(document) -> None:  # noqa: ANN001
    """让 Word 打开文档时自动更新域（目录因此自动生成）。"""
    settings = document.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def _add_page_number(section, cn_font: str, en_font: str, size: float) -> None:  # noqa: ANN001
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    _add_field(paragraph, "PAGE", "1")
    for run in paragraph.runs:
        _set_run_font(run, cn_font, en_font, size)


def _add_runs_with_bold(paragraph, text: str) -> None:  # noqa: ANN001
    """处理 **加粗**，其余按普通文本写入。"""
    position = 0
    for match in _BOLD.finditer(text):
        if match.start() > position:
            paragraph.add_run(text[position : match.start()])
        bold_run = paragraph.add_run(match.group(1))
        bold_run.bold = True
        position = match.end()
    if position < len(text):
        paragraph.add_run(text[position:])


# ---------------- 样式 ----------------


def _apply_styles(document, template: Template) -> None:  # noqa: ANN001
    normal = document.styles["Normal"]
    _set_cjk_font(normal, template.body_font_cn, template.body_font_en)
    normal.font.size = Pt(template.body_size)
    normal.paragraph_format.line_spacing = template.line_spacing
    normal.paragraph_format.first_line_indent = Pt(template.first_line_indent)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    for index, size in enumerate(template.heading_sizes):
        level = index + 1
        style = document.styles[f"Heading {level}"]
        _set_cjk_font(style, template.heading_font_cn, template.body_font_en)
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.space_before = Pt(12 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(6 if level == 1 else 4)
        style.paragraph_format.keep_with_next = True


# ---------------- 主流程 ----------------


def _strip_number(text: str) -> str:
    return _LEADING_NUMBER.sub("", text).strip() or text.strip()


def build_docx(
    markdown: str,
    template_key: str = DEFAULT_TEMPLATE,
    title: str | None = None,
    *,
    toc: bool | None = None,
    numbering: bool | None = None,
    page_numbers: bool | None = None,
) -> bytes:
    template = TEMPLATES.get(template_key) or TEMPLATES[DEFAULT_TEMPLATE]
    want_toc = template.toc if toc is None else toc
    want_numbering = template.numbering if numbering is None else numbering
    want_page_numbers = template.page_numbers if page_numbers is None else page_numbers

    document = Document()
    _apply_styles(document, template)

    section = document.sections[0]
    section.top_margin = Cm(template.margin_top_cm)
    section.bottom_margin = Cm(template.margin_bottom_cm)
    section.left_margin = Cm(template.margin_left_cm)
    section.right_margin = Cm(template.margin_right_cm)

    blocks = parse_markdown(markdown)

    # 文档标题：优先用参数，其次用第一个一级标题
    doc_title = (title or "").strip()
    if not doc_title:
        for kind, level, text in blocks:
            if kind == "heading" and level == 1:
                doc_title = _strip_number(text)
                break
    if doc_title:
        heading = document.add_paragraph()
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        heading.paragraph_format.first_line_indent = Pt(0)
        heading.paragraph_format.space_after = Pt(18)
        run = heading.add_run(doc_title)
        run.bold = True
        _set_run_font(run, template.heading_font_cn, template.body_font_en, template.heading_sizes[0] + 4)

    # 目录页
    if want_toc:
        toc_heading = document.add_paragraph()
        toc_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        toc_heading.paragraph_format.first_line_indent = Pt(0)
        toc_heading.paragraph_format.space_after = Pt(12)
        toc_run = toc_heading.add_run("目　录")
        toc_run.bold = True
        _set_run_font(toc_run, template.heading_font_cn, template.body_font_en, template.heading_sizes[0])

        toc_paragraph = document.add_paragraph()
        toc_paragraph.paragraph_format.first_line_indent = Pt(0)
        _add_field(toc_paragraph, 'TOC \\o "1-3" \\h \\z \\u', "（打开后按 F9 或右键“更新域”生成目录）")

        document.add_page_break()

    # 去掉充当文档标题的那一行，并计算正文标题的起始层级。
    # 合并稿常见结构是「# 文档标题 / ## 1 绪论 / ### 1.1 …」，
    # 若不重设基准，编号会变成 0.1 而不是 1。
    filtered: list[tuple] = []
    title_consumed = False
    for kind, level, text in blocks:
        if (
            kind == "heading"
            and doc_title
            and not title_consumed
            and _strip_number(text) == doc_title
        ):
            title_consumed = True
            continue
        filtered.append((kind, level, text))

    base_level = min((level for kind, level, _ in filtered if kind == "heading"), default=1)

    counters = [0, 0, 0]
    for kind, level, text in filtered:
        if kind == "heading":
            effective = max(1, min(level - base_level + 1, 4))
            clean = _strip_number(text)
            unnumbered = clean.strip().lower() in _UNNUMBERED_SECTIONS
            if not unnumbered:
                num_level = min(effective, 3)
                counters[num_level - 1] += 1
                for deeper in range(num_level, 3):
                    counters[deeper] = 0
                if want_numbering:
                    prefix = ".".join(str(counters[i]) for i in range(num_level))
                    clean = f"{prefix} {clean}"
            document.add_heading(clean, level=effective)
        elif kind == "list":
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _add_runs_with_bold(paragraph, text)
        elif kind == "quote":
            paragraph = document.add_paragraph(style="Quote")
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _add_runs_with_bold(paragraph, text)
        elif kind == "table":
            rows = text
            if rows:
                width = max(len(row) for row in rows)
                table = document.add_table(rows=len(rows), cols=width)
                table.style = "Table Grid"
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                for row_index, row in enumerate(rows):
                    for col_index in range(width):
                        cell = table.cell(row_index, col_index)
                        cell.text = row[col_index] if col_index < len(row) else ""
                        if row_index == 0:
                            for run in cell.paragraphs[0].runs:
                                run.bold = True
        else:
            paragraph = document.add_paragraph()
            _add_runs_with_bold(paragraph, text)

    if want_page_numbers:
        _add_page_number(section, template.body_font_cn, template.body_font_en, template.body_size - 2)

    _enable_update_fields(document)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
