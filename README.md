# 大肥鱼小组工作台 · AI 赋能的小组作业与论文协作台

把多人分头写的作业与论文，合成一篇**风格统一、格式规范、引用可靠**的成品。

> 当前状态：**工程骨架 v0.1**（前后端脚手架、容器化、CI 已就绪，业务功能待开发）

---

## 一、要解决什么问题

| 痛点 | 对应功能 |
|---|---|
| 各写各的，合起来像四个人写的四篇文章 | F4 用语风格统一 |
| 拼接处生硬，没有过渡 | F3 过渡段落生成 |
| 分工靠群里喊，进度无据可查 | F2 分工记录 |
| 数据、文献现找现编，来源不可靠 | F6 数据助手 / F7 参考文献助手 |
| 排版反复返工 | F5 AI 辅助排版 |
| 成员交上来的章节格式五花八门 | F1 多部分整合 |

功能清单与验收标准见 [docs/需求分析与实施计划.md](docs/需求分析与实施计划.md)。

## 二、技术栈

| 层 | 选型 |
|---|---|
| 前端 | Next.js 16（App Router）+ React 19 + TypeScript + Tailwind CSS 4 |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0（异步）+ Pydantic v2 |
| 数据库 | PostgreSQL 16（pgvector 镜像，向量检索暂未启用） |
| 依赖 | Redis 7（用于就绪探针，未承载缓存职责） |
| 大模型 | OpenAI 兼容协议（DeepSeek / 通义 / 智谱 / OpenAI 可切换） |
| 文档处理 | pandoc + citeproc + CSL、docxtpl、LibreOffice（后续阶段接入） |
| 部署 | Docker Compose + Nginx + GitHub Actions |

## 三、目录结构

```
参赛项目/
├── apps/
│   ├── api/                    后端服务（FastAPI）
│   │   ├── app/
│   │   │   ├── main.py         应用入口
│   │   │   ├── core/           配置、日志
│   │   │   ├── db/             数据库引擎、基类
│   │   │   ├── api/v1/         路由与端点
│   │   │   ├── models/         ORM 模型（待填充）
│   │   │   └── services/llm/   大模型供应商抽象
│   │   ├── tests/              测试
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── web/                    前端（Next.js）
│       ├── src/app/            页面与布局
│       ├── src/components/     组件
│       ├── src/lib/            接口封装
│       └── Dockerfile
├── docs/                       项目文档
├── infra/
│   ├── nginx/default.conf      反向代理配置
│   └── scripts/                服务器初始化 / 部署 / 备份脚本
├── .github/workflows/          CI 与自动部署
├── docker-compose.yml          开发环境依赖（数据库 + Redis）
├── docker-compose.prod.yml     生产环境全栈
└── .env.example                环境变量模板
```

### 前端页面结构

| 路由 | 页面 |
|---|---|
| `/` | 首页：Hero + 7 个功能入口 + 主链路 + 实时运行状态 |
| `/features` | 功能分区总览（含三层支撑能力说明） |
| `/features/merge` | F1 多部分整合 |
| `/features/tasks` | F2 分工记录 |
| `/features/transition` | F3 过渡段落生成 |
| `/features/style` | F4 用语风格统一 |
| `/features/format` | F5 AI 辅助排版 |
| `/features/data` | F6 数据助手 |
| `/features/references` | F7 参考文献助手 |
| `/about` | 关于项目：定位、技术栈、实施路线 |

功能页由 `app/features/[slug]/page.tsx` 动态生成，功能元数据集中在
`apps/web/src/lib/features.ts`，新增功能只需在那里加一条记录。

路由冒烟测试（需先启动前端）：

```bash
cd apps/web && pnpm verify:routes
```

## 四、快速开始

> **Windows 用户最快路径**：依赖装好后，在仓库根目录执行 `.\start-dev.ps1`，
> 会自动启动数据库、后端、前端并打开浏览器；`.\stop-dev.ps1` 一键停止。

### 前置要求

- Node.js ≥ 20、pnpm ≥ 9
- Python ≥ 3.11
- Docker（可选，用于跑数据库与 Redis）

### 1. 克隆并准备环境变量

```bash
git clone https://github.com/jianyilin1024/contest-project.git
cd contest-project

cp .env.example .env                     # 根级：供 docker compose 使用
cp apps/api/.env.example apps/api/.env   # 后端
cp apps/web/.env.example apps/web/.env.local
```

> 按需修改 `.env` 中的 `LLM_API_KEY`，不填也能启动，只是 AI 功能不可用。
> 完整变量说明见 [docs/环境配置说明.md](docs/环境配置说明.md)。

### 2. 启动数据库与 Redis

```bash
docker compose up -d
docker compose ps        # 确认两个容器都 healthy
```

### 3. 启动后端

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

- 接口文档：http://localhost:8000/docs
- 存活探针：http://localhost:8000/api/v1/health
- 就绪探针：http://localhost:8000/api/v1/health/ready

### 4. 启动前端

```bash
cd apps/web
pnpm install
pnpm dev
```

打开 http://localhost:3000 ，首页右上角会显示**后端连接状态**，绿色即表示前后端已打通。

## 五、一键成稿

打开 `/oneclick`，上传所有成员的文稿，一次完成：

```
合并归一 → 补写过渡段 → 检索真实参考文献 → 排版导出 Word
```

约 10–25 秒。参考文献来自 OpenAlex / Crossref 的真实记录，可点 DOI 核实。

**执行时是「规划 → 执行 → 自检」的 Agent 环路**，而不是固定流水线：

1. **规划**：模型读一眼合并稿，判断这次是否值得补过渡、需要多少条文献（并给出理由）；
2. **执行**：按规划调用工具，进度通过 SSE **实时推送**到界面（每一步的状态与耗时）；
3. **自检**：5 项确定性规则检查产出（正文未被截断、章节结构完整、过渡已插入、文献编号连续、无残留占位符）；
4. **修复**：文献检索为空时自动改用标题重试一次。

规划失败或用户关闭某步时自动退回用户设置，不会因为模型判断而擅自改变你的选择。

### MCP 服务端

本项目实现了一个**零依赖的 MCP（Model Context Protocol）服务端**，
任何支持 MCP 的客户端（Claude Desktop、Cursor、自研 Agent 等）都可以直接调用本项目的能力：

| 工具 | 能力 |
|---|---|
| `merge_documents` | 合并多人文稿：标题归一、重复段落检测、术语冲突提示 |
| `find_references` | 检索真实文献并按 GB/T 7714-2015 格式化（绝不编造） |
| `rewrite_style` | 逐段风格统一，返回原文/改后对照 |
| `deai_check` | 去 AI 味体检：破折号、提示性冒号、模板化转折等 |

启动（stdio 传输）：

```bash
cd apps/api
python mcp_server.py
```

客户端配置示例：

```json
{
  "mcpServers": {
    "dafeiyu": {
      "command": "python",
      "args": ["/path/to/apps/api/mcp_server.py"]
    }
  }
}
```

协议实现覆盖 `initialize`（握手）、`tools/list`（工具清单）、`tools/call`（调用）三个方法，
并有 8 个协议级测试保证行为正确。

---

## 六、接口一览（v0.1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 存活探针 |
| GET | `/api/v1/health/ready` | 就绪探针（检查数据库与 Redis） |
| GET | `/api/v1/llm/health` | **大模型连通性自检**，返回可用模型列表（不消耗 token） |
| POST | `/api/v1/llm/chat` | 一次性对话，返回 `content` / `reasoning` / `usage` |
| POST | `/api/v1/llm/chat/stream` | 流式对话（SSE），增量区分推理过程与正式回答 |
| POST | `/api/v1/merge/analyze` | **F1 多文档整合**：上传多份文稿 → 合并稿 + 目录 + 重复/术语报告 |
| POST | `/api/v1/merge/export` | 合并稿导出 md / docx |
| POST | `/api/v1/analysis/single` | **单文档 AI 分析**：文风异质性 + 归并建议 + 版式识别 |
| POST | `/api/v1/analysis/unify` | 按建议生成文风归并稿 |
| GET | `/api/v1/format/templates` | **F5 排版**模板列表 |
| POST | `/api/v1/format/docx` | 按模板渲染 docx（自动编号 / 目录 / 页码） |
| POST | `/api/v1/format/references` | AI 规范化参考文献（GB/T 7714-2015） |
| POST | `/api/v1/transition/analyze` | **F3 过渡段落**：识别章节断层 + 生成多备选 |
| POST | `/api/v1/transition/apply` | 按勾选把过渡段插入文档，返回 Markdown |
| POST | `/api/v1/references/search` | **F7 参考文献**：OpenAlex/Crossref 检索 + GB/T 7714 格式化 |
| POST | `/api/v1/references/insert` | 把选中条目写入文稿的「参考文献」段 |
| POST | `/api/v1/pipeline/oneclick` | **一键成稿**：合并 → 过渡 → 文献 → 返回成稿 Markdown |
| POST | `/api/v1/data/assist` | **F6 数据助手**：识别数据缺口 + 联网检索 + 带来源建议 |
| POST | `/api/v1/analysis/rewrite` | **F4 逐段风格统一**：返回原文/改后对照 |
| POST | `/api/v1/analysis/rewrite/assemble` | 应用用户勾选的改写 |
| GET/POST | `/api/v1/projects` | **F2 分工记录**：项目列表 / 新建 |
| POST | `/api/v1/projects/{id}/members` | 添加成员 |
| POST | `/api/v1/projects/{id}/tasks` | 新建任务 |
| PATCH | `/api/v1/tasks/{id}` | 更新任务（状态流转） |

`/llm/chat` 请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"一句话说明什么是论文摘要"}],"max_tokens":400}'
```

> 当前模型为**推理模型**：`max_tokens` 太小会被思考过程吃光导致回答为空，
> 网关默认已设为 2048。详见 [环境配置说明](docs/环境配置说明.md)。

## 七、常用命令

| 目的 | 命令 |
|---|---|
| 启动依赖（数据库 + Redis） | `docker compose up -d` |
| 停止依赖 | `docker compose down` |
| 清空数据库重来 | `docker compose down -v` |
| 后端测试 | `cd apps/api && pytest` |
| 后端静态检查 | `cd apps/api && ruff check .` |
| 前端类型检查 | `cd apps/web && pnpm typecheck` |
| 前端构建 | `cd apps/web && pnpm build` |
| 生产环境启动全栈 | `docker compose -f docker-compose.prod.yml up -d --build` |

## 八、部署

完整的服务器采购、初始化、域名解析、HTTPS、自动部署流程见
[docs/部署说明.md](docs/部署说明.md)。

一句话版本：

```bash
# 服务器上（已装 Docker、代码已克隆）
cp .env.example .env.prod && vim .env.prod
docker compose -f docker-compose.prod.yml up -d --build
```

## 九、开发约定

- **配置只走环境变量**：业务代码里不要出现 `os.environ`，统一从 `app.core.config.settings` 读取。
- **数据库模型**放在 `app/models/`，统一继承 `app.db.base.Base`，时间字段用 `TimestampMixin`。
- **新路由**注册到 `app/api/v1/router.py`，业务逻辑写在 `app/services/`，端点保持轻薄。
- **大模型调用**一律通过 `app.services.llm.get_llm_provider()`，不要直接 `httpx` 请求某家厂商。
- **提交前**跑一遍 `ruff check .`、`pytest`、`pnpm typecheck`；CI 也会检查。
- **不要提交** `.env`、密钥、模型 API Key。

## 十、路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 需求分析与实施计划 | ✅ |
| P1 | 工程骨架（本阶段） | ✅ |
| P2 | 数据模型 + 自动建表 + 项目/成员 | ✅ |
| P3 | 文档导入与结构化解析 | ✅ |
| P4 | 大模型网关（流式、结构化输出、降级重试） | ✅ |
| P5 | F1 多部分整合（含单文档 AI 文风分析） | ✅ |
| P6 | F2 分工记录（项目 / 成员 / 任务看板） | ✅ |
| P7 | F3 过渡段落生成（AI 定位 + 多备选 + 勾选式预览） | ✅ |
| P8 | F4 用语风格统一（逐段 diff，可逐句接受/回退） | ✅ |
| P9 | F5 AI 辅助排版 | ✅ |
| P11 | F7 参考文献助手（OpenAlex/Crossref + GB/T 7714） | ✅ |
| P10 | F6 数据助手（DeepSeek 搜索 + 带来源的数据建议） | ✅ |
| P12 | 联调、部署、演示材料 | ⏳ |

## 十一、文档索引

- [需求分析与实施计划](docs/需求分析与实施计划.md)
- [环境配置说明](docs/环境配置说明.md)
- [部署说明](docs/部署说明.md)
- [去 AI 味方案调研](docs/去AI味方案调研.md)
- [参赛要求符合性自检报告](docs/参赛自检报告.md)
- [技术文档（草稿）](docs/技术文档草稿.md)
- [更新日志](CHANGELOG.md)

---

## 十二、团队信息

> 以下信息需在提交前补全。

| 角色 | 姓名 | 学校 / 单位 | 主要职责 |
|---|---|---|---|
| 队长 | 【待填写】 | 【待填写】 | 需求分析、后端架构、AI 方案设计 |
| 队员 | 【待填写】 | 【待填写】 | 前端实现、交互设计 |
| 队员 | 【待填写】 | 【待填写】 | 文档处理、测试与部署 |

**指导教师**：【待填写】

**项目信息**

| 项目 | 内容 |
|---|---|
| 项目名称 | 大肥鱼小组工作台 |
| 版本 | v1.0.0（2026-10-25） |
| 代码仓库 | https://github.com/jianyilin1024/contest-project |
| 在线演示 | http://118.178.171.177 |
| 技术栈 | Next.js 16 · React 19 · TypeScript · FastAPI · PostgreSQL · DeepSeek |

---

*本项目为参赛作品，代码与文档均原创。*
