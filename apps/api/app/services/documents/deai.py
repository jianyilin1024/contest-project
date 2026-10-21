"""AI 味检测与定点改写（去味）。

检测器只做两件事：**指出痕迹**、**给出可执行的最小改法**。不判断"是不是 AI 写的"。

特征清单来自 283 万字对照语料的实证结果，只收录通过显著性检验的项。
特别注意：
- 对举结构（不是…而是）在这份语料里是 3.4 倍，DeepSeek 侧 0.86 次/千字 vs 人类 0.22，
  仍是最稳定的可执行靶点之一；
- 破折号、提示性冒号、过长前置定语，DeepSeek 在五个模型里都是最高的；
- 段首零回指评论区分力最强（4.4 倍），修法最便宜：补一个指示代词。
"""

import re
from collections import Counter
from dataclasses import dataclass, field

# ---------------- 特征定义 ----------------

# 段首可能出现的引导符号，判定「零回指」前先剥掉
_LEAD_JUNK = "「『“”‘’'()（）【】[] \t"


@dataclass(frozen=True)
class Feature:
    code: str
    label: str
    pattern: re.Pattern[str]
    baseline: float  # 人类侧每千字频率（来自对照语料）
    severity: str  # high | medium | low
    howto: str


FEATURES: list[Feature] = [
    Feature(
        "contrast",
        "对举结构（不是…而是）",
        re.compile(r"(?:不是|并非|不只是|不仅是|不在于)[^。！？；\n]{1,24}(?:而是|更是|乃是)"),
        0.22,
        "high",
        "直接陈述后半句的判断，删掉「不是 X」的铺垫",
    ),
    Feature(
        "contrast_alt",
        "对举变体（…而非…）",
        re.compile(r"[^，。；！？]{0,12}而非[^，。；！？]{1,12}"),
        0.30,
        "medium",
        "改成正面陈述：直接说采用了什么，不写否定的那一半",
    ),
    Feature(
        "dash",
        "破折号",
        re.compile(r"——"),
        0.80,
        "medium",
        "改成句号、逗号或冒号，一句一个意思",
    ),
    Feature(
        "colon",
        "提示性冒号",
        re.compile(
            r"(?:核心|关键|重点|本质|结论|总结|问题|答案|原因|具体|例如|比如"
            r"|也就是说|换句话说|简单说|说白了|一句话)"
            r"(?:在于|是|就是|为|主要有|包括)?[：:]"
        ),
        0.08,
        "high",
        "去掉提示语，直接写内容",
    ),
    Feature(
        "ordinal",
        "序数词起句",
        re.compile(r"^(?:首先|其次|再次|最后|第一|第二|第三|一方面|另一方面)[，,]"),
        0.03,
        "low",
        "删掉序数词，或用内容本身承担顺序",
    ),
    Feature(
        "premodifier",
        "过长前置定语",
        re.compile(r"(?:一个|一种|一套|这种|这个)[^，。、；：！？\n]{15,}的"),
        0.40,
        "medium",
        "拆成两小句，把定语改成谓语",
    ),
    Feature(
        "persona_metaphor",
        "理想化喻体",
        re.compile(
            r"(?:像|如同|仿佛)(?:一位|一个|一名)[^，。\n]{0,12}"
            r"(?:导师|专家|医生|向导|老师|助手|工匠|守门人)"
        ),
        0.002,
        "medium",
        "换成本行业的具体事物，或直接去掉比喻",
    ),
]

# 段首零回指评论：单独实现，因为要看后文有没有回指成分
_COMMENT_START = re.compile(
    r"^(?:听起来|看起来|看上去|听上去|说白了|说到底|换句话说|意味着|值得注意"
    r"|不难看出|细看|再看|回过头看|问题在于|原因在于|结果是|有意思的是"
    r"|更重要的是|关键在于|真正的|本质上)"
)
_ANAPHOR = re.compile(
    r"^(?:这|那|其|此|该|它|他|她|上面|前面|以上|同样|类似|相比|反过来"
    r"|但|不过|所以|因此|于是|而)"
)

MAX_EXCERPT = 40


@dataclass
class Issue:
    code: str
    label: str
    severity: str
    excerpt: str
    howto: str

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "severity": self.severity,
            "excerpt": self.excerpt,
            "howto": self.howto,
        }


@dataclass
class Report:
    score: int
    characters: int
    issues: list[Issue] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "characters": self.characters,
            "clean": self.clean,
            "issues": [item.to_dict() for item in self.issues],
        }


def _clip(text: str, limit: int = MAX_EXCERPT) -> str:
    text = text.strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _check_comment_start(text: str) -> Issue | None:
    """段落开头是评价语、却省掉了回指对象。"""
    stripped = text.lstrip(_LEAD_JUNK)
    match = _COMMENT_START.match(stripped)
    if not match:
        return None
    tail = stripped[match.end() : match.end() + 8]
    if _ANAPHOR.match(tail):
        return None  # 已经有回指，属于正常衔接
    return Issue(
        code="zero_anaphora",
        label="段首零回指评论",
        severity="high",
        excerpt=_clip(stripped),
        howto="补一个指示代词（这/该/上述），或者干脆删掉这句评价",
    )


def analyze(text: str) -> Report:
    """对一段文本做 AI 味体检。返回命中项与 0–100 的分数。"""
    stripped = (text or "").strip()
    chars = len(stripped)
    if chars == 0:
        return Report(score=100, characters=0)

    issues: list[Issue] = []

    for feature in FEATURES:
        matches = list(feature.pattern.finditer(stripped))
        if not matches:
            continue
        rate = len(matches) / chars * 1000
        # 短文本（≤120 字）只要出现 1 次就提示；长文本按每千字频率与人类基准比
        flagged = rate > feature.baseline * 2 if chars > 120 else True
        if not flagged:
            continue
        for match in matches:
            issues.append(
                Issue(
                    code=feature.code,
                    label=feature.label,
                    severity=feature.severity,
                    excerpt=_clip(match.group(0)),
                    howto=feature.howto,
                )
            )

    comment = _check_comment_start(stripped)
    if comment:
        issues.append(comment)

    weight = {"high": 18, "medium": 10, "low": 5}
    score = 100 - sum(weight.get(item.severity, 5) for item in issues)
    return Report(score=max(0, score), characters=chars, issues=issues)


# ---------------- 信息守恒 ----------------


_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_STRENGTH = ("显著", "明显", "大幅", "极大", "完全", "必然", "一定", "肯定")


def entity_counter(text: str) -> Counter:
    """抽取可核对的事实单元：数字与百分比。"""
    return Counter(_NUMBER.findall(text or ""))


def conservation_check(before: str, after: str) -> tuple[bool, list[str]]:
    """改写后不得丢失原文出现的数字/百分比，长度也不得过分离谱。"""
    problems: list[str] = []
    before_counts = entity_counter(before)
    after_counts = entity_counter(after)
    for value, count in before_counts.items():
        if after_counts[value] < count:
            problems.append(f"丢失数字 {value}")

    if before.strip():
        ratio = len(after.strip()) / len(before.strip())
        if ratio < 0.55:
            problems.append(f"篇幅压缩过度（{ratio:.0%}）")
        elif ratio > 1.8:
            problems.append(f"篇幅膨胀过度（{ratio:.0%}）")

    # 判断强度不得被拔高
    for word in _STRENGTH:
        if after.count(word) > before.count(word):
            problems.append(f"判断强度被加强：{word}")
            break

    return (not problems), problems


# ---------------- 改写提示词 ----------------

DEAI_PROMPT = """你是中文文字编辑，任务是去掉 AI 写作痕迹，同时严格保持原意。

只改被指出的问题，其余部分逐字保留。具体规则：

1. 对举结构（不是…而是 / …而非…）：直接陈述后半句的判断，删掉「不是 X」的铺垫；
   例如「不是简单替换，而是重构」→「是对训练范式的重构」；
   「以规则为主，而非统计」→「以规则为主」；
2. 破折号：改成句号或逗号，必要时拆成两句；
3. 提示性冒号（核心是：/关键：/具体：）：去掉提示语，直接写内容；
4. 段首零回指评论（值得注意/问题在于…）：**优先直接删掉这句评价**，
   让段落从事实开始；确实需要保留时，补一个指示代词（这/该/上述）让评价有对象。
   删掉后不要用别的评价句（「这一点值得注意」「值得强调的是」）填补；
5. 过长前置定语：拆成两个小句，把定语改成谓语；
6. 理想化喻体（像一位导师）：换成本行业的具体事物，或直接去掉比喻。

铁律：
- 不得新增任何数字、姓名、日期、来源或因果关系；
- 不得删除原文的数字、结论；
- **不得改变判断强度**：「可能提升」不能改成「提升」，「部分」不能改成「全部」；
- 不得改变专业术语；
- 长度与原文接近（±30% 以内）。

只输出 JSON。"""

DEAI_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "rewrites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "changed": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "text"],
            },
        }
    },
    "required": ["rewrites"],
}


def build_targets(items: list[dict]) -> str:
    blocks = []
    for item in items:
        labels = "、".join(issue["label"] for issue in item["issues"])
        blocks.append(f'[id={item["id"]}] 需修正：{labels}\n原文：{item["text"]}')
    return "\n\n".join(blocks)
