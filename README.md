# 参赛项目 · AI 赋能的小组作业与论文协作台

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
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/队列 | Redis 7 |
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

## 五、常用命令

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

## 六、部署

完整的服务器采购、初始化、域名解析、HTTPS、自动部署流程见
[docs/部署说明.md](docs/部署说明.md)。

一句话版本：

```bash
# 服务器上（已装 Docker、代码已克隆）
cp .env.example .env.prod && vim .env.prod
docker compose -f docker-compose.prod.yml up -d --build
```

## 七、开发约定

- **配置只走环境变量**：业务代码里不要出现 `os.environ`，统一从 `app.core.config.settings` 读取。
- **数据库模型**放在 `app/models/`，统一继承 `app.db.base.Base`，时间字段用 `TimestampMixin`。
- **新路由**注册到 `app/api/v1/router.py`，业务逻辑写在 `app/services/`，端点保持轻薄。
- **大模型调用**一律通过 `app.services.llm.get_llm_provider()`，不要直接 `httpx` 请求某家厂商。
- **提交前**跑一遍 `ruff check .`、`pytest`、`pnpm typecheck`；CI 也会检查。
- **不要提交** `.env`、密钥、模型 API Key。

## 八、路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 需求分析与实施计划 | ✅ |
| P1 | 工程骨架（本阶段） | ✅ |
| P2 | 数据模型 + 认证 + 项目/成员 | ⏳ |
| P3 | 文档导入与结构化解析 | ⏳ |
| P4 | 大模型网关（流式、结构化输出） | ⏳ |
| P5–P9 | F1 整合 / F2 分工 / F3 过渡 / F4 风格 / F5 排版 | ⏳ |
| P10–P11 | F6 数据助手 / F7 参考文献助手 | ⏳ |
| P12 | 联调、部署、演示材料 | ⏳ |

## 九、文档索引

- [需求分析与实施计划](docs/需求分析与实施计划.md)
- [环境配置说明](docs/环境配置说明.md)
- [部署说明](docs/部署说明.md)
