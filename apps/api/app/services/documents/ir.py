"""文档中间表示（IR）。

所有导入的文稿都先解析成统一结构，后续的合并、改写、排版、导出
全部基于 IR，而不是直接操作 docx 二进制——这是格式保真的前提。

层级约定：level 0 表示"没有归属章节的正文"，level >= 1 表示标题层级。
"""

from dataclasses import dataclass, field
from typing import Literal

BlockKind = Literal["paragraph", "list", "table", "quote"]


@dataclass
class Block:
    """章节下的一个内容块。"""

    kind: BlockKind
    text: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text}


@dataclass
class Node:
    """一个章节节点（扁平结构，靠 level 表达层级）。"""

    level: int
    title: str
    blocks: list[Block] = field(default_factory=list)
    number: str = ""
    source: str = ""
    # 标题在原文里的样子（含编号），版式识别需要它
    raw_title: str = ""

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "title": self.title,
            "number": self.number,
            "source": self.source,
            "raw_title": self.raw_title,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    @property
    def char_count(self) -> int:
        return sum(len(b.text) for b in self.blocks)


@dataclass
class ParsedDocument:
    """一份解析完成的文稿。"""

    filename: str
    author: str
    nodes: list[Node]
    raw_heading_levels: list[int] = field(default_factory=list)

    @property
    def heading_count(self) -> int:
        return sum(1 for n in self.nodes if n.level >= 1)

    @property
    def char_count(self) -> int:
        return sum(n.char_count for n in self.nodes)

    @property
    def min_heading_level(self) -> int:
        levels = [n.level for n in self.nodes if n.level >= 1]
        return min(levels) if levels else 1
