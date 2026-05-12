# ApeRAG 私有化部署指南

本仓库包含部署 ApeRAG 知识库系统所需的全部配置文件，不含源代码。

---

## 第一步：检查环境要求

在服务器上运行以下命令，确认环境满足要求：

```bash
# 检查 Docker 版本（需要 >= 20.10）
docker --version

# 检查 docker compose 是否可用
docker compose version

# 检查 Python（需要 3.8+）
python3 --version

# 检查磁盘空间（需要至少 30GB 可用）
df -h .
```

> **如果 `docker compose` 命令不可用**，在 Ubuntu 上运行以下命令安装：
> ```bash
> sudo apt-get update
> sudo apt-get install -y docker.io docker-compose-plugin
> sudo systemctl enable --now docker
> sudo usermod -aG docker $USER  # 无需 sudo 运行 docker，需重新登录生效
> ```

---

## 第二步：下载部署配置

```bash
git clone https://github.com/earayu/apemind-zhongye-deploy.git
cd apemind-zhongye-deploy
```

---

## 第三步：配置环境变量

**3.1 复制配置模板**

```bash
cp envs/env.template .env
```

**3.2 编辑 `.env` 文件，填写以下必填项**

打开 `.env` 文件，找到并修改下面几项（其余保持默认）：

```bash
# 1. JWT 密钥（必填，用于用户登录认证）
#    运行下面命令生成随机密钥：openssl rand -hex 32
JWT_SECRET=在这里填写随机字符串

# 2. 阿里云百炼 API Key
DASHSCOPE_API_KEY=sk-xxxx

# 3. OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-xxxx
```

> ⚠️ **安全提示**：`.env` 文件包含密钥，请勿发送给他人，请勿上传到任何代码仓库。

**3.3 代理环境配置（如果公司网络有 HTTP/HTTPS 代理）**

如果服务器配置了 `HTTP_PROXY` / `HTTPS_PROXY`，需要在 `.env` 中添加 `NO_PROXY` 配置，否则 Docker 容器内部的组件（如 Qdrant、Redis、Elasticsearch）会尝试通过代理访问本地地址，导致连接失败。

在 `.env` 文件中找到如下注释行，删除 `#` 号并保留：

```bash
NO_PROXY=mineru.net,localhost,127.0.0.1,::1
no_proxy=mineru.net,localhost,127.0.0.1,::1
```

---

## 第四步：拉取镜像并启动服务

**4.1 拉取所有服务镜像**（约需 5-10 分钟，取决于网速）

```bash
docker compose pull
```

看到类似输出表示成功：
```
✔ Image docker.io/apecloud/aperag-enterprise:2.1.6   Pulled
✔ Image docker.io/apecloud/aperag-enterprise-frontend:2.1.6   Pulled
...
```

**4.2 启动所有服务**

```bash
docker compose up -d
```

**4.3 等待服务启动完成**（约 2-3 分钟）

```bash
docker compose ps
```

正常情况下，以下 9 个长期服务应全部显示 `healthy` 或 `running`，`aperag-minio-init` 显示 `Exited (0)` 属于正常（它是一次性初始化任务，完成后退出）：

```
aperag-api               Up X minutes (healthy)
aperag-frontend          Up X minutes
aperag-indexing-worker   Up X minutes
aperag-postgres          Up X minutes (healthy)
aperag-postgres-graph    Up X minutes (healthy)
aperag-redis             Up X minutes (healthy)
aperag-qdrant            Up X minutes (healthy)
aperag-es                Up X minutes (healthy)
aperag-minio             Up X minutes (healthy)
aperag-minio-init        Exited (0)          ← 正常，初始化完成退出
```

> **如果某个服务一直显示 `starting`**，等待 3 分钟后再次运行 `docker compose ps` 查看。

---

## 第五步：初始化系统（⚠️ 仅首次部署需要，切勿重复执行）

> ⚠️ **重要**：初始化脚本只需运行一次。重复运行会导致重复创建配置项，请确认是全新部署后再执行。

```bash
# 安装依赖（Ubuntu 22.04+ 若报 "externally-managed-environment" 错误，改用下面的命令）
pip3 install requests
# 若报错，改用：pip3 install requests --break-system-packages

# 加载 .env 中的配置（避免重复填写）
set -a && source .env && set +a

# 设置管理员密码（自定义，与 .env 无关）
export APERAG_ADMIN_PASSWORD=自定义管理员密码

# 运行初始化
python3 scripts/init-local-demo.py
```

初始化脚本会自动创建：
- 管理员账号（用户名 `admin`，密码为上面设置的 `APERAG_ADMIN_PASSWORD`）
- 默认 AI 模型和 provider 配置

---

## 第六步：访问系统

服务启动后，在浏览器中打开：

| 地址 | 说明 |
|------|------|
| `http://服务器IP:3000` | 系统前端页面 |
| `http://服务器IP:8000/docs` | API 文档 |

**登录账号**：
- 用户名：`admin`
- 密码：第五步中设置的 `APERAG_ADMIN_PASSWORD`

**查看服务器 IP 地址**：

```bash
hostname -I
```

---

## 日常运维

### 查看服务状态

```bash
docker compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志（实时）
docker compose logs -f api
docker compose logs -f indexing-worker
```

### 停止服务（保留数据）

```bash
docker compose down
```

### 重启服务

```bash
docker compose down
docker compose up -d
```

### 更新到新版本

```bash
# 1. 拉取最新配置
git pull

# 2. 拉取新版本镜像
docker compose pull

# 3. 重启服务
docker compose down
docker compose up -d
```

> ⚠️ **重要**：大版本升级（如 2.1.x → 2.2.x）前请先查看 release note，可能包含数据库 schema 迁移步骤，需要按顺序执行，不可跳过。

### 彻底清理（危险，数据不可恢复）

```bash
# 停止并删除所有数据卷
docker compose down -v
```

---

## 遇到问题？

**问题 1：`docker compose up -d` 报错 "env file not found"**
```bash
# 检查 .env 文件是否存在
ls -la .env
# 如果不存在，重新执行第三步
cp envs/env.template .env
```

**问题 2：某个服务一直不健康（unhealthy）**
```bash
# 查看该服务的详细日志
docker compose logs <服务名>
# 例如：
docker compose logs api
docker compose logs es
```

**问题 3：端口被占用**
```bash
# Linux - 查看占用 3000 端口的进程
lsof -i :3000
# 确认不是重要业务进程后，再停止该进程
kill <PID>

# 常用端口：3000（前端）、8000（API）、5432（数据库）、6379（Redis）、6333（Qdrant）、9200（ES）
```

**问题 4：Qdrant / Redis 连接报 "Server disconnected" 错误**

通常是公司 HTTP 代理拦截了内部请求，请参考**第三步 3.3** 添加 `NO_PROXY` 配置后重启服务。

**问题 5：磁盘空间不足**
```bash
# 清理不用的 Docker 资源（不影响正在运行的容器）
docker system prune
```

---

## 版本信息

- 当前版本：`2.1.6`
- 镜像来源：Docker Hub 公开镜像（`docker.io/apecloud/aperag-enterprise:2.1.6`）
