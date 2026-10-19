"""多部分整合（F1）测试：解析、合并、检测、接口。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.documents import merge_documents, parse_document
from app.services.documents.export import markdown_to_docx
from app.services.documents.merge import normalize_text
from app.services.documents.parsers import ParseError, detect_numbered_heading, strip_numbering

client = TestClient(app)

DOC_A = """# 一、研究背景

随着深度学习的发展，神经网络在图像识别领域取得了显著进展。
本文关注小样本条件下的模型泛化能力问题。

## 1.1 研究意义

小样本学习可以显著降低数据标注成本，具有重要的工程价值。

## 1.2 国内外现状

国外学者较早开展了相关研究，提出了多种元学习框架。
"""

DOC_B = """二、研究方法

本文采用卷积神经网络作为基础模型，并在小样本数据集上进行实验。
我们使用元学习策略提升模型的泛化能力。

（一）数据来源

数据来自公开数据集 MiniImageNet，共 60000 张图片。

（二）评价指标

采用准确率与 F1 值作为主要评价指标。
"""

DOC_C = """# 三、结论

本文采用卷积神经网络作为基础模型，并在小样本数据集上进行实验。

研究结果表明，类神经网络在小样本条件下同样具备良好的泛化能力。
"""


# ---------------- 解析 ----------------


def test_markdown_headings_parsed() -> None:
    doc = parse_document("a.md", DOC_A.encode("utf-8"), "张三")
    assert doc.author == "张三"
    assert doc.heading_count == 3
    levels = [n.level for n in doc.nodes if n.level >= 1]
    assert levels == [1, 2, 2]


def test_chinese_numbering_detected() -> None:
    assert detect_numbered_heading("二、研究方法") == 1
    assert detect_numbered_heading("（一）数据来源") == 2
    assert detect_numbered_heading("1.2 相关工作") == 2
    assert detect_numbered_heading("这是一句普通的正文，不应该被当成标题。") is None


def test_strip_numbering() -> None:
    assert strip_numbering("二、研究方法") == "研究方法"
    assert strip_numbering("（一）数据来源") == "数据来源"
    assert strip_numbering("1.2.3 实验设置") == "实验设置"


def test_txt_without_markdown() -> None:
    doc = parse_document("b.txt", DOC_B.encode("utf-8"))
    titles = [n.title for n in doc.nodes if n.level >= 1]
    assert "研究方法" in titles
    assert "数据来源" in titles


def test_unsupported_suffix_rejected() -> None:
    with pytest.raises(ParseError):
        parse_document("a.pdf", b"whatever")


def test_empty_file_rejected() -> None:
    with pytest.raises(ParseError):
        parse_document("a.md", b"")


# ---------------- 合并 ----------------


def test_merge_builds_one_chapter_per_document() -> None:
    docs = [
        parse_document("a.md", DOC_A.encode("utf-8"), "张三"),
        parse_document("b.txt", DOC_B.encode("utf-8"), "李四"),
    ]
    outcome = merge_documents(docs, ["绪论", "研究方法"])
    chapters = [n for n in outcome.nodes if n.level == 1]
    assert [c.title for c in chapters] == ["绪论", "研究方法"]
    assert outcome.stats["documents"] == 2
    # 章节下的子标题被下移一级
    assert any(n.level == 2 for n in outcome.nodes)


def test_merge_assigns_hierarchical_numbers() -> None:
    """显式给了章节名时，文稿自身的顶级标题降为章节下的子标题。"""
    docs = [parse_document("a.md", DOC_A.encode("utf-8"))]
    outcome = merge_documents(docs, ["绪论"])
    assert [n.number for n in outcome.nodes] == ["1", "1.1", "1.1.1", "1.1.2"]
    assert [n.title for n in outcome.nodes] == ["绪论", "研究背景", "研究意义", "国内外现状"]


def test_merge_uses_first_heading_as_chapter_when_no_title() -> None:
    """没给章节名时，文稿第一个标题直接充当章节名，不会被重复一层。"""
    docs = [parse_document("a.md", DOC_A.encode("utf-8"))]
    outcome = merge_documents(docs, None)
    assert [n.number for n in outcome.nodes] == ["1", "1.1", "1.2"]
    assert outcome.nodes[0].title == "研究背景"


def test_merge_markdown_contains_headings() -> None:
    docs = [parse_document("a.md", DOC_A.encode("utf-8"))]
    outcome = merge_documents(docs, ["绪论"], title="小组作业合并稿")
    assert outcome.markdown.startswith("# 小组作业合并稿")
    assert "## 1 绪论" in outcome.markdown
    assert "### 1.1 研究背景" in outcome.markdown
    assert "#### 1.1.1 研究意义" in outcome.markdown


def test_document_without_headings_gets_warning() -> None:
    doc = parse_document("plain.txt", "这是一段没有任何标题的正文，只用来测试兜底逻辑是否生效。".encode())
    outcome = merge_documents([doc], ["引言"])
    assert any("没有识别到标题" in w for w in outcome.warnings)
    assert outcome.nodes[0].title == "引言"


# ---------------- 检测 ----------------


def test_duplicate_detected_across_documents() -> None:
    docs = [
        parse_document("b.txt", DOC_B.encode("utf-8"), "李四"),
        parse_document("c.md", DOC_C.encode("utf-8"), "王五"),
    ]
    outcome = merge_documents(docs)
    assert outcome.stats["cross_duplicates"] >= 1
    assert any(d["cross_document"] for d in outcome.duplicates)


def test_term_conflict_detected() -> None:
    docs = [
        parse_document("b.txt", DOC_B.encode("utf-8")),
        parse_document("c.md", DOC_C.encode("utf-8")),
    ]
    conflicts = merge_documents(docs).terms
    pairs = {(c["short"], c["long"]) for c in conflicts}
    assert ("神经网络", "类神经网络") in pairs
    # 切词伪影不应出现
    assert not any(short == "标注成" for short, _ in pairs)


def test_normalize_text_removes_punctuation() -> None:
    assert normalize_text("你好，世界！") == "你好世界"


# ---------------- 接口 ----------------


def _files_payload():
    return [
        ("files", ("a.md", DOC_A.encode("utf-8"), "text/markdown")),
        ("files", ("b.txt", DOC_B.encode("utf-8"), "text/plain")),
    ]


def test_analyze_endpoint() -> None:
    meta = json.dumps([{"author": "张三", "title": "绪论"}, {"author": "李四", "title": "研究方法"}])
    response = client.post(
        "/api/v1/merge/analyze",
        files=_files_payload(),
        data={"meta": meta, "title": "小组作业合并稿"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["documents"] == 2
    assert body["stats"]["sections"] >= 2
    assert body["title"] == "小组作业合并稿"
    assert body["markdown"].startswith("# 小组作业合并稿")
    assert len(body["outline"]) >= 2
    assert body["stats"]["per_document"][0]["author"] == "张三"


def test_analyze_rejects_bad_file_type() -> None:
    response = client.post(
        "/api/v1/merge/analyze",
        files=[("files", ("a.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert response.status_code == 422
    assert "不支持的文件类型" in response.text


def test_analyze_rejects_empty_upload() -> None:
    response = client.post("/api/v1/merge/analyze", files=[("files", ("a.md", b"", "text/markdown"))])
    assert response.status_code == 422


def test_export_markdown() -> None:
    response = client.post(
        "/api/v1/merge/export",
        json={"markdown": "# 标题\n\n正文", "title": "合并稿", "format": "md"},
    )
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.decode("utf-8").startswith("# 标题")


def test_export_docx() -> None:
    response = client.post(
        "/api/v1/merge/export",
        json={"markdown": "# 标题\n\n## 小节\n\n正文段落", "title": "合并稿", "format": "docx"},
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"  # docx 是 zip 容器


def test_markdown_to_docx_returns_bytes() -> None:
    data = markdown_to_docx("# 标题\n\n正文", "测试")
    assert isinstance(data, bytes)
    assert data[:2] == b"PK"


def test_openapi_exposes_merge_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/merge/analyze" in paths
    assert "/api/v1/merge/export" in paths
