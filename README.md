# Accio 多账号管理面板

[![LINUX DO](https://img.shields.io/badge/LINUX%20DO-社区认可-blue?style=flat-square&logo=linux)](https://linux.do)

基于 FastAPI 的本地管理面板，专注于 Accio 多账号的统一管理与快速切换。

- 多账号本地保存
- 登录链接生成
- 登录成功回调保存 Token
- 独立 OAuth 页面，支持手动粘贴回调地址导入
- 账号 JSON 下载与导入
- 查看额度与重置时间
- 单账号 / 批量刷新 Token
- 手动启用 / 禁用账号
- 额度耗尽自动禁用，账号恢复后自动重新启用
- 单后台调度器按账号下次检查时间自动巡检额度
- 切换账号：一键跳转回调地址，快速切换本地登录账号
- 支持全局上游代理：HTTP / HTTPS / SOCKS4 / SOCKS5

## 启动

```bash
uv sync
uv run accio-panel
```

也可以使用：

```bash
uv sync
uv run python main.py
```

启动后访问：

- `http://127.0.0.1:4097/dashboard` — 账号管理面板
- `http://127.0.0.1:4097/oauth` — OAuth 登录页
- `http://127.0.0.1:4097/login` — 登录跳转

## Docker

直接拉取镜像（推荐）：

```bash
docker pull ghcr.io/guji08233/accio-manager:latest
```

运行：

```bash
docker run -d \
  --name accio-panel \
  -p 4097:4097 \
  -v accio-panel-data:/app/data \
  -e ACCIO_CALLBACK_HOST=127.0.0.1 \
  ghcr.io/guji08233/accio-manager:latest
```

镜像由 GitHub Actions 自动构建，推送到 `main` 分支后会自动更新。

如需本地构建：

```bash
docker build -t accio-panel:latest .
docker run -d \
  --name accio-panel \
  -p 4097:4097 \
  -v accio-panel-data:/app/data \
  -e ACCIO_CALLBACK_HOST=127.0.0.1 \
  accio-panel:latest
```

说明：

- 容器内服务监听 `0.0.0.0:4097`
- 默认数据目录是 `/app/data`
- 服务器部署时，建议使用 `/oauth` 页面处理登录，并在需要时手动粘贴完整回调 URL 导入账号
- 新账号在回调导入后，会自动依次触发 `userinfo`、`invitation/query` 和 `channel/query` 完成激活

## GitHub Packages

仓库已添加 GitHub Actions 工作流：

- 文件：`.github/workflows/docker-publish.yml`
- 触发方式：`push` 到 `main`、`workflow_dispatch` 手动触发
- 推送目标：`ghcr.io/<owner>/<repo>`

首次推送成功后，可以在仓库的 `Packages` 页面看到镜像。

首次管理员密码默认值为：

```text
admin
```

可在 `data/config.json` 或面板内配置区中修改。

仓库默认只保留示例配置，不提交真实运行数据：

- `data/config.json`
- `data/stats.json`
- `data/accounts/*.json`
- `.env`

示例文件：

- `data/config.example.json`
- `.env.example`

## 数据目录

```text
data/
  config.json
  stats.json
  accio-accounts.json
  accounts/
    <account_id>.json
```

- `config.json`：全局配置、管理员密码、会话密钥
- `stats.json`：累计统计数据
- `accounts/*.json`：每个账号单独一个文件
- `accio-accounts.json`：旧版单文件账号列表，首次启动会自动迁移到 `accounts/` 目录
- 面板支持导入单账号 JSON，也支持直接导入旧版 `accio-accounts.json` 数组文件

## 自动调度

- 系统使用单个后台调度器，不为每个账号单独创建定时器
- 启用中的账号会低频巡检额度
- 自动禁用账号会基于接口返回的账单重置时间安排下次恢复检查
