# MiroFish Docker 部署指南

> 📌 本文档使用 **MiniMax API** 作为演示案例。MiroFish 支持任意 OpenAI-Compatible 接口的模型（包括 OpenAI、Anthropic Claude、Groq、硅基流动、Ollama 等），其他模型可参考此流程配置。

## 🚀 快速开始（5 分钟搞定）

> 假设：已安装 Docker、已有 API Key。

```bash
# 第一步：下载代码
git clone https://github.com/666ghj/MiroFish.git ~/workspace/MiroFish
cd ~/workspace/MiroFish

# 第二步：配置 .env
cp .env.example .env
# 编辑 .env，填入你的 API Key、Base URL 和模型名称

# 第三步：启动
docker run -d --name mirofish \
  --env-file .env \
  -e HTTP_PROXY="" -e HTTPS_PROXY="" -e UV_NO_PROXY=1 \
  -p 3000:3000 -p 5001:5001 \
  -v $(pwd)/backend/uploads:/app/backend/uploads \
  ghcr.nju.edu.cn/666ghj/mirofish:latest

# 第四步：验证
curl http://localhost:5001/api/simulation/history
# 成功输出：{"count": 0, "data": [], "success": true}
```

**成功标志：**

```json
{"count": 0, "data": [], "success": true}
```

---

## 📋 前置条件检查

| 条件 | 检查命令 | 预期结果 |
|------|---------|---------|
| Docker 已安装 | `docker --version` | Docker version 20.x+ |
| Docker 运行中 | `docker ps` | 返回容器列表（非报错） |
| Git 已安装 | `git --version` | git version 2.x |
| API Key | 有 | 去平台获取 |
| 网络通畅 | `docker pull ghcr.nju.edu.cn/666ghj/mirofish:latest` | 能拉取镜像 |

> 💡 没有 Docker？Ubuntu/Debian 安装：
> ```bash
> sudo apt update && sudo apt install -y docker.io
> sudo systemctl start docker
> sudo usermod -aG docker $USER
> # 重新登录 shell 使用户组生效
> ```

---

## 📖 完整部署步骤

### 步骤 1 — 下载代码

```bash
git clone https://github.com/666ghj/MiroFish.git ~/workspace/MiroFish
cd ~/workspace/MiroFish
```

✅ 看到 `backend/`、`frontend/`、`docker-compose.yml` 等目录即正常。

### 步骤 2 — 配置 .env

```bash
cp .env.example .env
nano .env  # 或 vim、vscode 等任意编辑器
```

`.env` 文件配置说明：

| 变量名 | 值（示例） | 说明 |
|--------|-----------|------|
| `LLM_API_KEY` | `sk-cp-xxxxxxxx...` | 你的模型 API Key（必填） |
| `LLM_BASE_URL` | `https://api.minimaxi.com/v1`（示例） | 填你实际使用的 API 地址 |
| `LLM_MODEL_NAME` | `MiniMax-M2.7-highspeed`（示例） | 填你实际使用的模型名称 |
| `ZEP_API_KEY` | （留空或随便填） | 可选功能，不影响核心功能 |

> 📌 **本案例使用 MiniMax API**，其他模型请替换为对应的 API Key 和地址。

#### 支持的 LLM 模型

MiroFish 后端使用 OpenAI SDK，只要提供 OpenAI-Compatible 接口的模型均可使用。

| 模型名称 | 提供商 | 上下文 | 最大输出 | 特点 |
|---------|--------|--------|---------|------|
| **MiniMax-M2.7-highspeed** | MiniMax（本案例） | 200K tokens | 8192 tokens | ⭐ 推荐，速度快 |
| MiniMax-M2.5 | MiniMax | 200K tokens | 8192 tokens | 标准版，性价比均衡 |
| MiniMax-M2.5-Lightning | MiniMax | 200K tokens | 8192 tokens | 极速版，延迟低 |
| gpt-4o / gpt-4o-mini | OpenAI | 128K tokens | 16384 tokens | OpenAI 官方模型 |
| claude-sonnet-4-20250514 | Anthropic | 200K tokens | 8192 tokens | Anthropic Claude 系列 |
| groq 系列 | Groq | 以平台文档为准 | 以平台文档为准 | Groq LPU，极速 |
| qwen、deepseek 等 | 硅基流动/其他 | 以平台文档为准 | 以平台文档为准 | 国内平替方案 |

> 💡 核心要求：`LLM_BASE_URL` 指向一个 OpenAI-Compatible 的 API 端点，`LLM_MODEL_NAME` 填模型名称即可，MiroFish 不限制具体是哪家模型。

#### 各平台 LLM_BASE_URL 示例

| 提供商 | LLM_BASE_URL 示例 | 说明 |
|--------|------------------|------|
| MiniMax（本案例） | `https://api.minimaxi.com/v1` | 本文档演示使用 |
| OpenAI | `https://api.openai.com/v1` | 官方接口 |
| Anthropic | `https://api.anthropic.com/v1` | Claude 系列 |
| Groq | `https://api.groq.com/openai/v1` | Groq LPU，极速 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | 国内平替方案 |
| Ollama（本地） | `http://localhost:11434/v1` | 本地部署模型 |

> ⚠️ 国内部分平台 API 域名可能不同，请以平台实际文档为准。

#### 如何获取 API Key

1. 访问 **https://platform.minimaxi.com**（MiniMax）或你的模型提供商平台
2. 登录后进入「用户中心」→「API Key」→「创建 API Key」
3. 复制生成的 Key，格式类似：`sk-cp-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
4. 粘贴到 `.env` 的 `LLM_API_KEY` 一行

> ⚠️ API Key 等同于密码，请勿泄露或提交到 Git。`.env` 文件已在 `.gitignore` 中忽略。

### 步骤 3 — 拉取 Docker 镜像

```bash
docker pull ghcr.nju.edu.cn/666ghj/mirofish:latest
```

✅ 看到 `Status: Downloaded newer image` 即成功。

> ⚠️ 如果南京大学镜像也拉失败，说明该机器网络有限制，请改用本地构建方案（见文末）。

### 步骤 4 — 启动容器

#### 方式 A：docker-compose（推荐）

项目里已准备好 `docker-compose.yml`，用它启动最简单：

```bash
cd ~/workspace/MiroFish
docker-compose up -d
```

> ⚠️ `docker-compose.yml` 默认镜像地址是 `ghcr.io`（海外），需要手动改成南京大学镜像：
> 打开 `docker-compose.yml`，将 `image` 那行改为：
> ```yaml
> image: ghcr.nju.edu.cn/666ghj/mirofish:latest
> ```

#### 方式 B：docker run（更透明）

```bash
docker run -d --name mirofish \
  --env-file ~/workspace/MiroFish/.env \
  -e HTTP_PROXY="" -e HTTPS_PROXY="" -e UV_NO_PROXY=1 \
  -p 3000:3000 -p 5001:5001 \
  -v ~/workspace/MiroFish/backend/uploads:/app/backend/uploads \
  --restart unless-stopped \
  ghcr.nju.edu.cn/666ghj/mirofish:latest
```

| 参数 | 说明 |
|------|------|
| `--name mirofish` | 容器命名，方便管理 |
| `--env-file .env` | 加载 API Key 等配置 |
| `-e HTTP_PROXY=""` | **必须！** 禁用代理，否则 PyPI 访问失败 |
| `-p 3000:3000` | 前端界面端口 |
| `-p 5001:5001` | 后端 API 端口 |
| `-v ./backend/uploads` | 持久化上传文件 |
| `--restart unless-stopped` | 机器重启后容器自动启动 |

> 💡 `--restart unless-stopped` 表示机器重启后容器会自动启动，不需要手动再跑。

### 步骤 5 — 等待服务启动（约 30 秒）

```bash
docker logs -f mirofish
# 等待出现 "MiroFish Backend 启动完成"，按 Ctrl+C 退出
```

**预期日志输出：**

```
frontend  VITE ready in 784 ms
frontend  Local: http://localhost:3000/
backend   * Running on http://127.0.0.1:5001
backend   MiroFish Backend 启动完成
```

### 步骤 6 — 验证服务

```bash
curl -s http://localhost:5001/api/simulation/history
```

**成功输出：**

```json
{"count": 0, "data": [], "success": true}
```

```bash
curl -s -o /dev/null -w "Frontend HTTP Status: %{http_code}\n" http://localhost:3000/
```

**成功输出：**

```
Frontend HTTP Status: 200
```

✅ 两个都正常就可以打开浏览器访问了。

### 步骤 7 — 访问界面

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:3000 | 浏览器打开 |
| 后端 API | http://localhost:5001 | API 端点 |

> 💡 如果从局域网其他机器访问，把 `localhost` 换成电脑的 IP，例如 `http://192.168.1.100:3000`。云服务器记得在安全组/防火墙开放 3000 和 5001 端口。

---

## 🔧 常见问题与解决

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| `docker-compose up` 报错 network | 默认用 ghcr.io 镜像拉不到 | 把 `docker-compose.yml` 里的 image 改成 `ghcr.nju.edu.cn/666ghj/mirofish:latest` |
| 容器启动后立刻退出 | 最可能：代理问题导致 PyPI 下载失败 | 确认加了 `-e HTTP_PROXY=""`，然后 `docker logs mirofish` 查看具体错误 |
| `npm run backend exited with code 1` | PyPI 请求走了主机的坏代理 | `docker run` 加 `-e HTTP_PROXY="" -e UV_NO_PROXY=1` |
| 提示 `ZEP_API_KEY 未配置` | 代码有这个验证但实际是可选功能 | 启动时加 `-e ZEP_API_KEY=sk-fake` 绕过，或修改 `backend/app/config.py`（见下） |
| `docker run` 报 `port is already allocated` | 3000 或 5001 端口被占用 | `docker ps` 检查，`-p 3001:3000` 映射到其他端口 |
| `docker pull` 拉不下来 | 网络限制 | 用本地构建方案替代（见文末） |
| 重启服务器后 MiroFish 没起来 | 没有加自动重启参数 | 加 `--restart unless-stopped`，或用 docker-compose（它默认有 restart） |
| `curl` 返回 `Connection refused` | 容器没启动成功 | `docker ps` 看状态，`docker logs mirofish` 查原因 |
| 浏览器打不开 `localhost:3000` | 防火墙阻止 / 容器没启动 | `sudo ufw allow 3000`（Ubuntu），确认 `docker ps` 里 mirofish 状态是 Up |

### ZEP_API_KEY 验证报错（代码修复方案）

如果不想每次启动都加 `-e ZEP_API_KEY=sk-fake`，可以直接改源码：

**文件：** `backend/app/config.py`

找到：
```python
if not cls.ZEP_API_KEY:
    errors.append("ZEP_API_KEY 未配置")
```

改为：
```python
if not cls.ZEP_API_KEY:
    pass  # ZEP is optional
```

保存后，重新运行（需要挂载本地代码）：
```bash
docker stop mirofish && docker rm mirofish
docker run -d --name mirofish \
  --env-file ~/workspace/MiroFish/.env \
  -e HTTP_PROXY="" -e UV_NO_PROXY=1 \
  -p 3000:3000 -p 5001:5001 \
  -v ~/workspace/MiroFish/backend/uploads:/app/backend/uploads \
  -v ~/workspace/MiroFish/backend:/app/backend \
  --restart unless-stopped \
  ghcr.nju.edu.cn/666ghj/mirofish:latest
```

---

## 🛠 常用命令速查

### 容器管理

```bash
docker ps                           # 查看运行中的容器
docker ps -a                        # 查看所有容器（含已停止）
docker logs -f mirofish             # 实时查看日志
docker logs mirofish 2>&1 | tail -30  # 最近 30 行日志
docker stop mirofish                # 停止
docker start mirofish               # 启动
docker restart mirofish             # 重启
docker rm mirofish                  # 删除（需先 stop）
docker rm -f mirofish               # 强制删除（运行中也删）
docker exec -it mirofish /bin/bash  # 进入容器终端
```

### docker-compose 方式

```bash
docker-compose up -d     # 启动（后台运行）
docker-compose down       # 停止并删除容器
docker-compose restart    # 重启
docker-compose logs -f   # 实时日志
docker-compose pull       # 拉取最新镜像
```

### 验证命令

```bash
curl http://localhost:5001/api/simulation/history        # 验证后端
curl -o /dev/null -w "%{http_code}" localhost:3000/  # 验证前端
docker exec mirofish env | grep LLM                     # 查看容器内 LLM 配置
```

---

## 🌐 端口说明

| 端口 | 服务 | 说明 | 验证 |
|------|------|------|------|
| 3000 | 前端 | 浏览器访问的用户界面 | http://localhost:3000 |
| 5001 | 后端 | Flask REST API | `curl localhost:5001/api/simulation/history` |

> 💡 云服务器（阿里云/腾讯云等）需在安全组规则里开放 3000 和 5001 端口入站。

---

## 💿 备选：本地构建镜像

当所有镜像地址都无法访问时，可以在有网络的机器上本地构建。

### 前提条件

- 一台能访问 Docker Hub 的机器（构建时需要拉取 `python:3.11-slim` 等基础镜像）
- 约 2-3 GB 磁盘空间
- 构建耗时约 20-30 分钟（网络速度决定）

### 构建步骤

**第一步：修改 Dockerfile（减小镜像体积）**

```bash
cd ~/workspace/MiroFish
nano Dockerfile
# 将第一行 FROM python:3.11 改为 FROM python:3.11-slim
```

**第二步：执行构建（必须覆盖代理）**

```bash
docker build \
  --build-arg HTTP_PROXY="" \
  --build-arg HTTPS_PROXY="" \
  -t mirofish:local .
```

> ⚠️ 必须加 `--build-arg` 覆盖代理参数，否则构建会因代理不存在而失败。

**第三步：导出镜像（拷贝到目标机器）**

```bash
docker save mirofish:local -o mirofish-local.tar
# 将镜像文件拷贝到目标机器，然后：
docker load -i mirofish-local.tar
```

**第四步：在目标机器启动**

```bash
docker run -d --name mirofish \
  --env-file ~/workspace/MiroFish/.env \
  -e HTTP_PROXY="" -e UV_NO_PROXY=1 \
  -p 3000:3000 -p 5001:5001 \
  -v ~/workspace/MiroFish/backend/uploads:/app/backend/uploads \
  --restart unless-stopped \
  mirofish:local
```

---

## ✅ 部署检查清单

完成后逐项核对，确保全部 OK：

- [ ] 代码已下载：`ls ~/workspace/MiroFish` 有 `backend/`
- [ ] `.env` 已配置 `LLM_API_KEY`：`grep LLM_API_KEY .env` 有值
- [ ] 镜像已拉取：`docker images | grep mirofish`
- [ ] 容器在运行：`docker ps | grep mirofish` 状态 Up
- [ ] 后端 API 正常：`curl localhost:5001/api/simulation/history` 返回 `success:true`
- [ ] 前端 HTTP 200：`curl -o /dev/null -w "%{http_code}" localhost:3000/`
- [ ] 浏览器能打开：http://localhost:3000 看到界面
- [ ] 重启后自启：重启机器后 `docker ps` 仍 Up
