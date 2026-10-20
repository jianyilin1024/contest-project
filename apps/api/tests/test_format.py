"""排版（F5）测试：Markdown 解析、docx 生成、参考文献识别与规范化。"""

import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api.v1.endpoints import format as format_endpoint
from app.main import app
from app.services.documents.references import find_reference_section, rewrite_section
from app.services.documents.typesetting import TEMPLATES, build_docx, parse_markdown

client = TestClient(app)

MD = """# 小组作业合并稿

## 1 绪论

### 1.1 研究背景

本文关注小样本条件下的模型泛化能力问题，**重点** 在于降低标注成本。

- 第一条要点
- 第二条要点

> 这是一段引用。

## 2 研究方法

| 方法 | 准确率 |
|---|---|
| 基线 | 0.81 |

## 3 结论

实验表明该方法有效。
"""


def _paragraphs(data: bytes) -> list[str]:
    document = Document(io.BytesIO(data))
    return [paragraph.text for paragraph in document.paragraphs]


# ---------------- Markdown 解析 ----------------


def test_parse_markdown_blocks() -> None:
    blocks = parse_markdown(MD)
    kinds = [block[0] for block in blocks]
    assert kinds.count("heading") == 5
    assert kinds.count("list") == 2
    assert kinds.count("quote") == 1
    assert kinds.count("table") == 1


def test_parse_markdown_table_shape() -> None:
    table = next(block for block in parse_markdown(MD) if block[0] == "table")
    assert table[2][0] == ["方法", "准确率"]
    assert table[2][1] == ["基线", "0.81"]


# ---------------- docx 生成 ----------------


@pytest.mark.parametrize("key", list(TEMPLATES))
def test_build_docx_returns_zip(key: str) -> None:
    data = build_docx(MD, key, "小组作业合并稿")
    assert data[:2] == b"PK"
    assert len(data) > 10000


def test_heading_numbering_is_applied() -> None:
    texts = _paragraphs(build_docx(MD, "academic", "小组作业合并稿"))
    assert "1 绪论" in texts
    assert "1.1 研究背景" in texts
    assert "2 研究方法" in texts


def test_existing_numbers_are_not_duplicated() -> None:
    texts = _paragraphs(build_docx(MD, "academic", "小组作业合并稿"))
    assert not any(text.startswith("1 1 ") for text in texts)
    assert not any(text.startswith("1.1 1.1 ") for text in texts)


def test_numbering_can_be_disabled() -> None:
    texts = _paragraphs(build_docx(MD, "academic", "标题", numbering=False))
    assert "绪论" in texts
    assert "1 绪论" not in texts


def test_reference_section_is_not_numbered() -> None:
    md = "# 标题\n\n## 1 绪论\n\n正文。\n\n## 参考文献\n\n[1] 某某. 书名[M]. 北京: 出版社, 2020."
    texts = _paragraphs(build_docx(md, "academic", "标题"))
    assert "1 绪论" in texts
    assert "参考文献" in texts
    assert not any(text.startswith("2 参考文献") for text in texts)


def test_toc_only_in_templates_that_want_it() -> None:
    with_toc = _paragraphs(build_docx(MD, "academic", "标题"))
    without_toc = _paragraphs(build_docx(MD, "course", "标题"))
    assert "目　录" in with_toc
    assert "目　录" not in without_toc


def test_title_appears_once() -> None:
    texts = _paragraphs(build_docx(MD, "academic", "小组作业合并稿"))
    assert texts.count("小组作业合并稿") == 1


# ---------------- 参考文献 ----------------


REF_MD = """# 标题

## 1 绪论

正文。

## 参考文献

[1] 张三, 李四. 深度学习综述[J]. 计算机学报, 2023, 46(5): 1-20.
[2] 王五. 小样本学习[M]. 北京: 科学出版社, 2022.

## 附录

其他内容。
"""


def test_find_reference_section() -> None:
    section = find_reference_section(REF_MD)
    assert section is not None
    assert len(section["entries"]) == 2
    assert section["entries"][0].startswith("张三")
    assert section["end_index"] == len(REF_MD.splitlines()) - 3


def test_find_reference_section_missing() -> None:
    assert find_reference_section("# 没有参考文献的文档\n\n正文") is None


def test_rewrite_section_keeps_surroundings() -> None:
    section = find_reference_section(REF_MD)
    normalized = [
        {"index": 1, "formatted": "张三, 李四. 深度学习综述[J]. 计算机学报, 2023."},
        {"index": 2, "formatted": "王五. 小样本学习[M]. 北京: 科学出版社, 2022."},
    ]
    result = rewrite_section(REF_MD, section, normalized)
    assert "[1] 张三, 李四. 深度学习综述[J]. 计算机学报, 2023." in result
    assert "## 附录" in result
    assert "其他内容。" in result


# ---------------- 接口 ----------------


class FakeProvider:
    name = "fake"
    model = "fake-model"

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        return {
            "entries": [
                {
                    "index": 1,
                    "type": "journal",
                    "formatted": "张三, 李四. 深度学习综述[J]. 计算机学报, 2023, 46(5): 1-20.",
                    "note": "",
                },
                {
                    "index": 2,
                    "type": "book",
                    "formatted": "王五. 小样本学习[M]. 北京: 科学出版社, 2022.",
                    "note": "缺 ISBN",
                },
            ]
        }


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(format_endpoint, "get_llm_provider", lambda: provider)
    return provider


def test_templates_endpoint() -> None:
    response = client.get("/api/v1/format/templates")
    assert response.status_code == 200
    keys = [item["key"] for item in response.json()]
    assert {"academic", "course", "contest"} <= set(keys)


def test_docx_endpoint() -> None:
    response = client.post(
        "/api/v1/format/docx",
        json={"markdown": MD, "title": "测试稿", "template": "academic"},
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert "attachment" in response.headers["content-disposition"]


def test_docx_endpoint_rejects_unknown_template() -> None:
    response = client.post(
        "/api/v1/format/docx", json={"markdown": MD, "template": "不存在"}
    )
    assert response.status_code == 422


def test_references_endpoint(fake_provider: FakeProvider) -> None:
    response = client.post("/api/v1/format/references", json={"markdown": REF_MD})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["found"] is True
    assert len(body["entries"]) == 2
    assert body["entries"][0]["type"] == "journal"
    assert any("缺 ISBN" in note for note in body["notes"])
    assert "[1] 张三" in body["markdown"]
    assert "## 附录" in body["markdown"]


def test_references_endpoint_without_section() -> None:
    response = client.post("/api/v1/format/references", json={"markdown": "# 只有正文"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["notes"]


def test_openapi_exposes_format_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/format/docx" in paths
    assert "/api/v1/format/references" in paths
    assert "/api/v1/format/templates" in paths
