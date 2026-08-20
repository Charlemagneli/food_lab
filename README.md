# 食研所（FoodLab）

食研所是一个中文优先、响应式的菜谱社区。用户可以浏览和搜索菜谱、收藏与点赞、发表评论、维护个人资料，以及发布自己的菜谱；管理员可以审核投稿并为优质内容添加“编辑精选”标记。

项目采用原生多页面前端和 Flask JSON API，当前使用 SQLite，部署结构为 Nginx + Gunicorn + Flask。

## 当前功能

### 公开浏览

- 首页热门菜谱、最新菜谱和分类入口
- 按标题、简介、食材、菜系、标签和作者搜索
- 按最新、浏览量、点赞数和收藏数排序
- 中餐、西餐、日料、韩餐、东南亚、甜品和汤分类
- 菜谱默认按一人份展示，读者可自行调整食材份量；支持分步烹饪和复制链接
- 响应式布局、移动端导航和明暗主题
- “编辑精选”菜谱徽标

### 用户与互动

- 注册、登录、退出和 Cookie 会话恢复
- 个人主页、个人简介和兴趣标签
- 账户资料与密码修改
- 菜谱点赞、收藏、评论和评论点赞
- 顶部系统消息入口、未读提醒和平台通知列表
- 我的收藏与我的菜谱

### 菜谱创作

- 发布、编辑和删除菜谱
- 发布入口要求登录；未登录访客会先进入注册或登录流程
- 动态添加食材与制作步骤
- 封面和步骤图片上传、即时预览
- 保存草稿和提交审核
- 菜谱状态：`draft`、`pending`、`published`、`rejected`

### 管理员

- 后台访问权限保护
- 待审核、已发布和全部菜谱列表
- 通过、驳回和重新审核
- 隐藏违规菜谱、记录处理人/时间/原因并永久删除内容
- 设置或取消“编辑精选”
- 后台数据概览

管理员用户和评论管理已提供后台能力；分类属于系统基础数据，当前不提供管理员新增/删除接口，避免误操作破坏分类数据。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | HTML、CSS、原生 JavaScript |
| 后端 | Python、Flask、Blueprint |
| 数据访问 | SQLAlchemy Engine、SQLite |
| 生产服务 | Gunicorn、Nginx |
| 容器 | Docker、Docker Compose |
| 测试 | Python `unittest` |
| 版本控制 | Git、GitHub Actions |

SQLite 是当前默认数据库。项目配置保留了后续演进空间，但 PostgreSQL 和正式数据库迁移流程尚未接入。

## 项目结构

```text
food_lab/
├── backend/
│   ├── app.py                  # Flask 应用工厂及全局配置
│   ├── config.py               # 环境变量和运行配置
│   ├── wsgi.py                 # Gunicorn 入口
│   ├── database/
│   │   └── db.py               # 数据库结构、初始化和种子数据
│   ├── routes/
│   │   ├── auth.py             # 注册、登录、会话和密码
│   │   ├── recipes.py          # 菜谱、分类和社区互动 API
│   │   ├── messages.py         # 系统消息 API
│   │   ├── users.py            # 个人资料、收藏和个人菜谱 API
│   │   └── admin.py            # 管理员 API
│   └── services/
│       ├── recipe_service.py   # 菜谱数据组装
│       └── content_filter.py   # 评论内容屏蔽检测
├── frontend/
│   ├── css/                    # 全局、后台和烹饪模式样式
│   ├── js/                     # 各页面 JavaScript
│   ├── images/                 # 静态图片与本地上传目录
│   └── *.html                  # 多页面前端
├── tests/
│   └── test_api.py             # API 自动化测试
├── docker/
│   ├── Dockerfile
│   └── nginx.conf
├── .github/workflows/test.yml
├── .env.example
├── compose.yaml
├── requirements.txt
└── README.md
```

## 本地开发

### 1. 创建虚拟环境

Linux、macOS 或 WSL：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. 启动应用

```bash
python -m backend.app
```

访问：

- 网站：<http://127.0.0.1:5000/>
- 健康检查：<http://127.0.0.1:5000/api/health>
- 管理后台：<http://127.0.0.1:5000/admin.html>

本地开发不必复制 `.env.example`。未设置环境变量时，数据库默认创建在 `instance/foodlab.sqlite3`，上传文件默认保存到 `frontend/images/uploads/`。

## 测试账号

首次初始化数据库时会自动创建以下账号：

| 角色 | 邮箱 | 密码 |
| --- | --- | --- |
| 管理员 | `admin@foodlab.local` | `FoodLab-admin-123` |
| 普通用户 | `user@foodlab.local` | `FoodLab-user-123` |

这些账号只用于本地开发和功能测试。部署到公网前必须修改密码，并更换 `SECRET_KEY`。

## 运行测试

```bash
python -m unittest discover -v
```

当前测试覆盖：

- 注册、登录与会话
- 点赞、收藏和评论
- 菜谱创建及审核状态
- 搜索和公开菜谱查询
- 个人资料和密码修改
- 管理员权限与基础数据保护
- 默认测试账号登录

## Docker 启动

### 1. 创建生产配置

```bash
cp .env.example .env
```

至少修改 `.env` 中的 `SECRET_KEY`。可以使用以下命令生成随机值：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

开发环境示例：

```dotenv
SECRET_KEY=请替换为随机长字符串
DATABASE_PATH=/app/instance/foodlab.sqlite3
UPLOAD_FOLDER=/app/frontend/images/uploads
SESSION_COOKIE_SECURE=0
FLASK_DEBUG=0
```

### 2. 构建并启动

```bash
docker compose up --build -d
docker compose ps
```

访问 <http://127.0.0.1/>。Nginx 提供前端静态文件，并将 `/api/` 和 `/uploads/` 请求代理到 Flask。

查看日志：

```bash
docker compose logs -f api nginx
```

停止服务：

```bash
docker compose down
```

SQLite 数据和上传目录使用 Docker 命名卷。普通的 `docker compose down` 不会删除它们；执行带 `-v` 的删除命令会同时删除数据卷，请谨慎使用。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 开发占位值 | Flask 会话和 CSRF 签名密钥 |
| `DATABASE_PATH` | `instance/foodlab.sqlite3` | SQLite 数据库路径 |
| `UPLOAD_FOLDER` | `frontend/images/uploads` | 图片上传目录 |
| `CONTENT_FILTER_WORDS_FILE` | `backend/data/blocked_words.txt` | 评论区屏蔽词库路径，格式为 `类别|短语` |
| `CONTENT_FILTER_EXTRA_WORDS` | 空 | 以英文逗号分隔的额外评论屏蔽短语 |
| `SESSION_COOKIE_SECURE` | `0` | HTTPS 环境设为 `1` |
| `FLASK_DEBUG` | `0` | 本地调试开关 |

`.env` 已被 Git 忽略，请勿提交真实密码、密钥或生产环境配置。

## API 概览

| 路径 | 用途 |
| --- | --- |
| `GET /api/health` | 服务健康检查 |
| `GET /api/categories` | 公开分类列表 |
| `GET /api/recipes` | 搜索、筛选、排序和分页 |
| `GET /api/recipes/:id` | 菜谱详情 |
| `POST /api/recipes` | 创建菜谱或草稿 |
| `PUT /api/recipes/:id` | 编辑菜谱 |
| `DELETE /api/recipes/:id` | 删除菜谱 |
| `POST /api/recipes/:id/like` | 点赞或取消点赞 |
| `POST /api/recipes/:id/favorite` | 收藏或取消收藏 |
| `POST /api/recipes/:id/comments` | 发布评论 |
| `POST /api/comments/:id/like` | 点赞或取消点赞评论 |
| `DELETE /api/comments/:id` | 删除自己的评论（管理员可管理全部评论） |
| `GET /api/auth/me` | 当前登录用户 |
| `PATCH /api/users/me` | 更新账户资料 |
| `POST /api/users/me/avatar` | 上传或更换头像（multipart 字段 `avatar`） |
| `POST /api/users/:id/follow` | 关注或取消关注用户 |
| `POST /api/auth/change-password` | 修改密码 |
| `GET /api/messages` | 当前用户的系统消息列表 |
| `GET /api/messages/unread-count` | 系统消息未读数 |
| `PATCH /api/messages/read` | 将系统消息标记为已读 |
| `GET /api/admin/recipes` | 管理员菜谱列表 |
| `PATCH /api/admin/recipes/:id` | 审核或设置编辑精选 |
| `PATCH /api/admin/recipes/:id/featured` | 独立设置或取消编辑精选 |
| `DELETE /api/admin/recipes/:id` | 管理员永久删除菜谱 |

分类仅提供公开读取接口 `GET /api/categories`，不提供管理员新增或删除接口。

除登录和注册外，写请求使用 Cookie 会话与 CSRF 保护。浏览器端会先请求 `/api/auth/csrf`，再通过 `X-CSRF-Token` 请求头提交令牌。

### 评论内容治理

评论在服务端发布前经过基础屏蔽词检测，能够识别在短语中插入空格、常见标点或全角字符的规避方式。命中规则时接口返回 `422` 和 `content_blocked`，该评论不会写入评论表。

基础词库位于 `backend/data/blocked_words.txt`，每行使用 `类别|短语`，修改文件后会自动重新加载。建议使用具有明确违法招揽或交易含义的组合短语，避免用过于宽泛的单字词误伤正常讨论。系统仅记录评论用户、菜谱、规则类别、规则哈希和时间，不记录被拦截的评论正文。

关键词拦截只是基础技术措施，不能替代人工审核、用户举报、申诉处置、隐私政策、数据留存规则和正式法律合规审查。正式上线前应根据实际运营地区、用户规模和业务形态完善这些制度。

## 内容工作流

```text
保存草稿
   ↓
 draft
   ↓ 提交审核
 pending
   ├── 管理员通过  → published → 可在公开页面展示
   └── 管理员驳回  → rejected  → 可重新修改和提交

已发布内容如需下架，管理员可将其设为 `hidden`，系统会记录处理人、时间和原因，并立即从公开列表移除。
```

“编辑精选”是独立于审核状态的管理员标记。被标记的公开菜谱会在菜谱卡片、详情页和个人菜谱中显示精选徽标。

## 上线前检查

- 将管理员和测试用户密码改为高强度密码，或删除测试账号
- 使用随机值替换 `SECRET_KEY`
- 配置域名、HTTPS 和 Nginx 证书
- HTTPS 启用后设置 `SESSION_COOKIE_SECURE=1`
- 限制数据库、上传目录和 `.env` 的文件权限
- 配置数据库与上传文件备份
- 检查 8 MB 上传限制是否符合生产需求
- 不要把 `.env`、SQLite 数据库或用户上传文件提交到 Git

## 开发约定

建议采用功能分支开发：

```text
main
├── feat/recipe-review
├── feat/profile-settings
└── fix/mobile-navigation
```

提交信息使用 Conventional Commits：

```text
feat: add recipe moderation
fix: prevent duplicate favorites
docs: update local setup guide
test: cover administrator permissions
```

## 当前进度

- 阶段 0：项目骨架与设计系统——已完成基础版本
- 阶段 1：公开菜谱浏览——已完成基础版本
- 阶段 2：用户与个人空间——已完成基础版本
- 阶段 3：社区互动——已完成基础版本
- 阶段 4：菜谱创作工作流——已完成基础版本
- 阶段 5：管理员后台——菜谱审核与编辑精选已完成，其余管理界面待完善
- 阶段 6：测试与部署——已有自动化测试和 Docker 基础配置，生产部署验收待完成

## License

本项目使用仓库根目录 [LICENSE](LICENSE) 中声明的许可证。
