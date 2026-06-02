# ApeMind 私有化部署指南

本仓库包含部署 ApeMind 知识库系统所需的全部配置文件，不含源代码。

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

# 2. 其他 AI Provider API Key 可在管理员页面配置；
#    如果使用初始化脚本批量创建模型，再按脚本说明导出对应环境变量。
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
✔ Image docker.io/apecloud/apemind-enterprise:v2.3.4   Pulled
✔ Image docker.io/apecloud/apemind-enterprise-frontend:v2.3.4   Pulled
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

正常情况下，以下长期服务应全部显示 `healthy` 或 `running`，`apemind-minio-init` 显示 `Exited (0)` 属于正常（它是一次性初始化任务，完成后退出）：

```
apemind-api               Up X minutes (healthy)
apemind-frontend          Up X minutes
apemind-nginx             Up X minutes
apemind-indexing-worker   Up X minutes
apemind-postgres          Up X minutes (healthy)
apemind-postgres-graph    Up X minutes (healthy)
apemind-redis             Up X minutes (healthy)
apemind-qdrant            Up X minutes (healthy)
apemind-es                Up X minutes (healthy)
apemind-minio             Up X minutes (healthy)
apemind-minio-init        Exited (0)          ← 正常，初始化完成退出
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

### 更新到新版本（保留数据）

```bash
# 1. 拉取最新配置
git pull

# 2. 拉取新版本镜像
docker compose pull

# 3. 重建容器，让 docker-compose.yml / nginx.conf / init-es.sh 等变更全部生效
docker compose up -d --force-recreate
```

> ⚠️ **重要**：大版本升级（如 2.1.x → 2.2.x）前请先查看 release note，可能包含数据库 schema 迁移步骤，需要按顺序执行，不可跳过。

### 彻底清理并升级（危险，数据不可恢复）

本次中冶升级已和客户确认可以不保留旧数据。执行下面命令会删除旧系统容器和所有数据卷，然后用当前仓库配置重新启动最新版本：

```bash
# 停止并删除所有数据卷（不可恢复）
docker compose down -v

# 拉取最新配置和镜像
git pull
docker compose pull

# 全新启动
docker compose up -d --force-recreate
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

首先一次性查看所有 ApeMind 所需端口是否冲突：
```bash
sudo ss -lntp | grep -E ":(3000|8000|5432|5433|6379|6333|9200|9000)"
```

| 端口 | 服务 | Ubuntu 常见冲突来源 | 解决方案 |
|------|------|---------------------|---------|
| 5432 | postgres | 系统预装 PostgreSQL | `sudo systemctl stop postgresql && sudo systemctl disable postgresql` |
| 5433 | postgres-graph | 系统预装 PostgreSQL | 同上 |
| 6379 | redis | 系统预装 Redis | `sudo systemctl stop redis-server && sudo systemctl disable redis-server` |
| 9200 | elasticsearch | 系统 ES | `sudo systemctl stop elasticsearch` |
| 6333 | qdrant | 少见 | 改端口映射（见下方） |
| 9000 | minio | 少见 | 改端口映射（见下方） |
| 8000 | api | 其他 Web 服务 | 改端口映射（见下方） |
| 3000 | frontend | 其他 Web 服务 | 改端口映射（见下方） |

**方案 A（推荐）：停止系统服务**

如果冲突来自系统 PostgreSQL（Ubuntu 最常见）：
```bash
sudo systemctl stop postgresql
sudo systemctl disable postgresql   # 禁止开机自启
docker compose up -d                 # 重新启动
```

**方案 B：修改端口映射**（系统服务不能停时使用）

编辑 `docker-compose.yml`，找到对应服务的 `ports` 配置，修改宿主机端口（冒号左边的数字）。示例：
```yaml
# 把 5432 改为 15432（冒号左边是宿主机端口，右边是容器内端口，不要改右边）
ports:
  - "15432:5432"
```
> 注意：容器之间通过服务名互相访问（如 `postgres`），不受宿主机端口影响，只改宿主机映射即可。修改后重新 `docker compose up -d`。

**问题 4：Qdrant / Redis 连接报 "Server disconnected" 错误**

通常是公司 HTTP 代理拦截了内部请求，请参考**第三步 3.3** 添加 `NO_PROXY` 配置后重启服务。

**问题 5：磁盘空间不足**
```bash
# 清理不用的 Docker 资源（不影响正在运行的容器）
docker system prune
```

---

## 版本信息

- 当前版本：`v2.3.4`
- 镜像来源：Docker Hub 公开镜像（`docker.io/apecloud/apemind-enterprise:v2.3.4`）
