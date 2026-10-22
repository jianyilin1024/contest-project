"""参考文献与一键成稿测试。"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import pipeline as pipeline_endpoint
from app.api.v1.endpoints import references as references_endpoint
from app.main import app
from app.services.references.gbt import format_author, format_authors, format_gbt
from app.services.references.sources import ReferenceRecord

client = TestClient(app)


# ---------------- GB/T 7714 格式化 ----------------


def test_format_author_western() -> None:
    assert format_author("Jane Smith") == "Smith J"
    assert format_author("Smith, Jane") == "Smith J"


def test_format_author_chinese() -> None:
    # OpenAlex 对中文作者可能给「名 姓」，应还原为「姓名」
    assert format_author("孟月 宋") == "宋孟月"
    assert format_author("关曼玉") == "关曼玉"


def test_format_authors_truncates() -> None:
    assert format_authors(["A B", "C D", "E F"]) == "B A, D C, F E"
    assert format_authors(["A B", "C D", "E F", "G H"]) == "B A, D C, F E, et al"
    assert format_authors(["关曼玉", "简蕊", "李慢", "王五"]) == "关曼玉, 简蕊, 李慢, 等"


def test_format_journal_entry() -> None:
    record = ReferenceRecord(
        title="Deep Few-Shot Learning",
        authors=["Jane Smith", "John Doe"],
        year=2018,
        venue="IEEE Transactions on Geoscience",
        volume="57",
        issue="4",
        pages="1056-1065",
        doi="10.1109/TGRS.2018.1",
        kind="journal",
    )
    text = format_gbt(record)
    assert text.startswith("Smith J, Doe J. Deep Few-Shot Learning[J].")
    assert "2018, 57(4): 1056-1065" in text
    assert "DOI: 10.1109/TGRS.2018.1" in text


def test_format_book_entry() -> None:
    record = ReferenceRecord(
        title="小样本学习", authors=["王五"], year=2022, venue="北京: 科学出版社", kind="book"
    )
    text = format_gbt(record)
    assert text.startswith("王五. 小样本学习[M].")


# ---------------- 检索接口（打桩） ----------------


def _fake_record() -> ReferenceRecord:
    return ReferenceRecord(
        title="Few-Shot Learning Survey",
        authors=["Jane Smith"],
        year=2020,
        venue="IEEE TPAMI",
        volume="42",
        issue="1",
        pages="1-20",
        doi="10.1109/TPAMI.2020.1",
        kind="journal",
        source="openalex",
    )


def test_search_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(queries, limit=8, **kwargs):  # noqa: ANN001, ANN003
        return [_fake_record()]

    monkeypatch.setattr(references_endpoint, "search_all", fake_search)
    response = client.post("/api/v1/references/search", json={"query": "few-shot", "limit": 5})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["entries"][0]["text"].startswith("[1] Smith J.")
    assert "IEEE TPAMI" in body["entries"][0]["text"]


def test_search_endpoint_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(queries, limit=8, **kwargs):  # noqa: ANN001, ANN003
        return []

    monkeypatch.setattr(references_endpoint, "search_all", fake_search)
    response = client.post("/api/v1/references/search", json={"query": "nothing"})
    assert response.status_code == 404


def test_search_endpoint_accepts_source_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def fake_search(queries, limit=8, **kwargs):  # noqa: ANN001, ANN003
        captured.update(kwargs)
        return [_fake_record()]

    monkeypatch.setattr(references_endpoint, "search_all", fake_search)
    client.post(
        "/api/v1/references/search",
        json={"query": "x", "sources": ["book"]},
    )
    assert captured["include_books"] is True
    assert captured["include_academic"] is False
    assert captured["include_web"] is False


def test_insert_references_appends_section() -> None:
    response = client.post(
        "/api/v1/references/insert",
        json={"markdown": "# 标题\n\n正文。", "entries": ["[1] 某某. 书名[M]. 北京: 出版社, 2020."]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "## 参考文献" in body["markdown"]
    assert "[1] 某某" in body["markdown"]


def test_insert_references_replaces_existing() -> None:
    md = "# 标题\n\n## 参考文献\n\n[9] 旧条目.\n"
    response = client.post(
        "/api/v1/references/insert",
        json={"markdown": md, "entries": ["[1] 新条目[M]."]},
    )
    body = response.json()
    assert "新条目" in body["markdown"]
    assert "旧条目" not in body["markdown"]


# ---------------- 一键成稿 ----------------


class FakeProvider:
    name = "fake"
    model = "fake-model"

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        required = schema.get("required", [])
        if "boundaries" in required:
            return {
                "boundaries": [
                    {
                        "id": "b1",
                        "needs": True,
                        "reason": "两节之间缺少承接",
                        "confidence": 0.9,
                        "options": [
                            {"label": "简洁承接", "text": "基于上述背景，本文给出研究方法。"}
                        ],
                    }
                ]
            }
        if "rewrites" in required:
            return {"rewrites": []}
        return {}


DOC_A = "# 一、绪论\n\n这是绪论部分的内容，交代研究背景与问题。\n"
DOC_B = "# 二、方法\n\n这是方法部分，说明本文采用的技术路线。\n"


@pytest.fixture
def fake_pipeline(monkeypatch: pytest.MonkeyPatch):
    async def fake_search(query: str, limit: int = 8):  # noqa: ANN001
        return [_fake_record()]

    monkeypatch.setattr(pipeline_endpoint, "get_llm_provider", lambda: FakeProvider())
    monkeypatch.setattr(pipeline_endpoint, "search_references", fake_search)


def test_oneclick_endpoint(fake_pipeline) -> None:
    response = client.post(
        "/api/v1/pipeline/oneclick",
        files=[
            ("files", ("a.md", DOC_A.encode("utf-8"), "text/markdown")),
            ("files", ("b.md", DOC_B.encode("utf-8"), "text/markdown")),
        ],
        data={
            "meta": '[{"author":"张三","title":"绪论"},{"author":"李四","title":"方法"}]',
            "title": "小组作业合并稿",
            "add_transitions": "true",
            "find_references": "true",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["documents"] == 2
    assert "小组作业合并稿" in body["final_markdown"]
    assert "参考文献" in body["final_markdown"]
    assert body["references"]["inserted"] == 1
    names = [step["name"] for step in body["steps"]]
    assert "合并文稿" in names
    assert all(step["status"] in ("ok", "skipped", "failed") for step in body["steps"])


def test_oneclick_skips_optional_steps(fake_pipeline) -> None:
    response = client.post(
        "/api/v1/pipeline/oneclick",
        files=[("files", ("a.md", DOC_A.encode("utf-8"), "text/markdown"))],
        data={"add_transitions": "false", "find_references": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transitions"]["skipped"] is True
    assert body["references"]["skipped"] is True


def test_openapi_exposes_new_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/references/search" in paths
    assert "/api/v1/pipeline/oneclick" in paths
