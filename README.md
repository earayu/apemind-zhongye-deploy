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

> **如果 `docker compose` 命令不可用**，请参考 [Docker 官方文档](https://docs.docker.com/compose/install/) 安装 docker-compose-plugin。

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

当所有服务显示 `healthy` 或 `running` 状态时，表示启动成功：

```
NAME                    STATUS
aperag-api              Up X minutes (healthy)
aperag-frontend         Up X minutes
aperag-postgres         Up X minutes (healthy)
aperag-redis            Up X minutes (healthy)
...
```

> **如果某个服务一直显示 `starting`**，等待 3 分钟后再次运行 `docker compose ps` 查看。

---

## 第五步：初始化系统（仅首次部署需要）

> 此步骤需要安装 Python requests 库，并需要真实的 API Key 才能完成。

```bash
# 安装依赖
pip3 install requests

# 运行初始化脚本（替换下面的密码和 API Key）
APERAG_ADMIN_PASSWORD=自定义管理员密码 \
DASHSCOPE_API_KEY=与.env中相同的值 \
python3 scripts/init-local-demo.py
```

初始化脚本会自动创建：
- 管理员账号（用户名 `admin`，密码为上面设置的值）
- 默认 AI 模型配置

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

> **查看服务器 IP**：运行 `hostname -I` 或 `ip addr show`

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
# 拉取最新配置
git pull

# 拉取新版本镜像
docker compose pull

# 重启服务
docker compose down
docker compose up -d
```

---

## 遇到问题？

**问题 1：`docker compose up -d` 报错 "env file not found"**
```bash
# 检查 .env 文件是否存在
ls -la .env
# 如果不存在，重新执行第三步
```

**问题 2：某个服务一直不健康（unhealthy）**
```bash
# 查看该服务的详细日志
docker compose logs <服务名>
# 例如：docker compose logs api
```

**问题 3：端口被占用**
```bash
# 查看哪个进程占用了 3000 端口
lsof -i :3000
```

**问题 4：磁盘空间不足**
```bash
# 清理不用的 Docker 资源
docker system prune
```

---

## 版本信息

- 当前版本：`2.1.6`
- 镜像来源：Docker Hub 公开镜像（`docker.io/apecloud/aperag-enterprise:2.1.6`）
