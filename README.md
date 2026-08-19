# 食研所 FoodLab

中文优先的菜谱社区，前端使用原生 HTML/CSS/JavaScript，后端使用 Flask + SQLAlchemy（SQLite 起步），生产环境由 Gunicorn 和 Nginx 承载。

## 本地运行

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m backend.app
```

打开 <http://127.0.0.1:5000/>。默认种子管理员为 `admin@foodlab.local`，密码 `FoodLab-admin-123`，部署前请立即修改或删除该账号。

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Nginx 提供前端静态文件并将 `/api` 代理到 Flask；SQLite 数据和上传文件使用持久化卷。

## API 快速检查

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/recipes
```

生产环境请设置随机 `SECRET_KEY`、启用 HTTPS 后将 `SESSION_COOKIE_SECURE=1`，并通过 Nginx 配置域名和证书。
