"""过渡段落（F3）测试：分块、断层检测、拼接、接口（LLM 打桩）。"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import transition as transition_endpoint
from app.main import app
from app.services.documents.transitions import (
    assemble_markdown,
    boundary_summary,
    build_blocks,
    find_boundaries,
)

client = TestClient(app)

MD = """# 小组作业合并稿

## 1 绪论

本文关注小样本条件下的模型泛化能力问题。

研究的意义在于降低标注成本。

## 2 研究方法

本文采用卷积神经网络作为基础模型。

实验在 MiniImageNet 上进行。

## 3 结论

实验表明该方法有效。
"""


# ---------------- 分块 ----------------


def test_build_blocks_assigns_sequential_ids() -> None:
    blocks = build_blocks(MD)
    assert [block.id for block in blocks] == list(range(1, len(blocks) + 1))
    assert blocks[0].kind == "heading"
    assert blocks[0].level == 1


def test_build_blocks_kinds() -> None:
    md = "# 标题\n\n正文\n\n- 列表项\n\n> 引用\n\n| a | b |\n|---|---|\n| 1 | 2 |"
    kinds = [block.kind for block in build_blocks(md)]
    assert kinds == ["heading", "paragraph", "list", "quote", "table", "table"]


# ---------------- 断层检测 ----------------


def test_find_boundaries_between_sections() -> None:
    """标题紧接标题不算断层（中间没有正文可承接），只统计有正文的章节结束处。"""
    blocks = build_blocks(MD)
    boundaries = find_boundaries(blocks)
    assert len(boundaries) == 2
    assert boundaries[0]["section_from"] == "绪论"
    assert boundaries[0]["section_to"] == "研究方法"
    assert boundaries[1]["section_from"] == "研究方法"
    assert boundaries[1]["section_to"] == "结论"


def test_boundary_points_at_last_content_block() -> None:
    blocks = build_blocks(MD)
    boundaries = find_boundaries(blocks)
    for boundary in boundaries:
        assert blocks[boundary["after_block_id"] - 1].kind != "heading"


def test_no_boundary_without_content() -> None:
    md = "# 标题\n\n## 空章节\n\n## 另一节\n\n正文。"
    boundaries = find_boundaries(build_blocks(md))
    # 标题紧邻标题，中间没有正文，不构成断层
    assert all(item["after_block_id"] > 0 for item in boundaries)
    assert len(boundaries) <= 1


def test_boundary_summary() -> None:
    boundaries = [
        {"needs": True, "options": [{"id": "x"}]},
        {"needs": False, "options": []},
        {"needs": True, "options": []},
    ]
    assert boundary_summary(boundaries) == {"candidates": 3, "needed": 1, "skipped": 2}


# ---------------- 拼接 ----------------


def test_assemble_markdown_inserts_after_block() -> None:
    blocks = [block.to_dict() for block in build_blocks(MD)]
    target = next(block for block in blocks if block["text"].startswith("研究的意义"))
    md = assemble_markdown(blocks, [{"after_block_id": target["id"], "text": "由此可见，降低成本是关键。"}])
    assert "由此可见，降低成本是关键。" in md
    assert md.index("研究的意义") < md.index("由此可见") < md.index("## 2 研究方法")


def test_assemble_markdown_preserves_structure() -> None:
    blocks = [block.to_dict() for block in build_blocks(MD)]
    md = assemble_markdown(blocks, [])
    assert "## 1 绪论" in md
    assert "实验表明该方法有效。" in md


def test_assemble_markdown_ignores_unknown_block() -> None:
    blocks = [block.to_dict() for block in build_blocks(MD)]
    md = assemble_markdown(blocks, [{"after_block_id": 9999, "text": "不该出现"}])
    assert "不该出现" not in md


# ---------------- 接口 ----------------


class FakeProvider:
    name = "fake"
    model = "fake-model"

    async def structured(self, messages, schema, **kwargs):  # noqa: ANN001, ANN003
        return {
            "boundaries": [
                {
                    "id": "b1",
                    "needs": True,
                    "reason": "第一节结尾停在研究意义，第二节直接进入方法，缺少承接。",
                    "confidence": 0.86,
                    "options": [
                        {"label": "简洁承接", "text": "基于上述问题，本文进一步给出研究方法。"},
                        {"label": "递进强调", "text": "为回答上述问题，需要在方法层面给出可操作的路径。"},
                    ],
                },
                {
                    "id": "b2",
                    "needs": False,
                    "reason": "第二节结尾已给出实验结论，与结论章自然衔接。",
                    "confidence": 0.7,
                    "options": [],
                },
                {
                    "id": "b3",
                    "needs": True,
                    "reason": "模型未覆盖该点",
                    "confidence": 0.5,
                    "options": [{"label": "备选", "text": "补充说明。"}],
                },
            ]
        }


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(transition_endpoint, "get_llm_provider", lambda: provider)
    return provider


def test_analyze_endpoint(fake_provider: FakeProvider) -> None:
    response = client.post("/api/v1/transition/analyze", json={"markdown": MD, "title": "测试"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["blocks"]) > 5
    assert len(body["boundaries"]) == 2
    first = body["boundaries"][0]
    assert first["needs"] is True
    assert len(first["options"]) == 2
    assert first["options"][0]["label"] == "简洁承接"
    assert body["stats"]["candidates"] == 2


def test_analyze_endpoint_without_headings(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(transition_endpoint, "get_llm_provider", lambda: provider)
    response = client.post("/api/v1/transition/analyze", json={"markdown": "只有一段正文。"})
    assert response.status_code == 200
    body = response.json()
    assert body["boundaries"] == []
    assert body["stats"]["candidates"] == 0


def test_apply_endpoint() -> None:
    blocks = [block.to_dict() for block in build_blocks(MD)]
    target = next(block for block in blocks if block["text"].startswith("研究的意义"))
    response = client.post(
        "/api/v1/transition/apply",
        json={
            "blocks": blocks,
            "insertions": [{"after_block_id": target["id"], "text": "由此引出方法。"}],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["inserted"] == 1
    assert "由此引出方法。" in body["markdown"]


def test_openapi_exposes_transition_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/transition/analyze" in paths
    assert "/api/v1/transition/apply" in paths
