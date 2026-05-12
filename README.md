# ApeRAG 私有化部署（中冶环境）

本仓库包含在中冶环境部署 ApeRAG 所需的全部配置文件，**不含源码**。

## 前置条件

- Docker >= 20.10 + docker-compose-plugin（`docker compose` 命令可用）
- Python 3.8+（运行初始化脚本）
- 磁盘空间 >= 30GB
- 网络可访问 docker.io（拉取公开镜像）

## 快速启动

### 1. 配置环境变量

```bash
cp envs/env.template .env
```

编辑 `.env`，**必填**：

```bash
# JWT 密钥（强随机字符串）
JWT_SECRET=$(openssl rand -hex 32)

# LLM provider（按实际情况填写）
DASHSCOPE_API_KEY=sk-xxx          # 阿里云百炼
OPENROUTER_API_KEY=sk-or-v1-xxx   # OpenRouter（可选）

# 其余保持默认即可
```

> ⚠️ **安全提示**：`.env` 文件包含密钥，**不要提交到 git，不要在聊天中发送**。

### 2. 启动服务

```bash
docker compose pull
docker compose up -d
```

等待所有服务健康（约 2-3 分钟）：

```bash
docker compose ps
```

### 3. 初始化（首次运行）

```bash
pip install requests
APERAG_ADMIN_PASSWORD=<自定义管理员密码> \
DASHSCOPE_API_KEY=<填写同 .env 中的值> \
python scripts/init-local-demo.py
```

### 4. 访问

- **前端**：http://&lt;服务器IP&gt;:3000
- **API**：http://&lt;服务器IP&gt;:8000
- 账号：`admin` / `<上面设置的 APERAG_ADMIN_PASSWORD>`

## 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| api | 8000 | ApeRAG 后端 API |
| frontend | 3000 | ApeRAG 前端 |
| indexing-worker | - | 文档索引处理 |
| postgres | 5432 | 主数据库 |
| redis | 6379 | 缓存/队列 |
| qdrant | 6333 | 向量数据库 |
| elasticsearch | 9200 | 全文检索 |
| minio | 9000/9001 | 对象存储 |

## 版本信息

- 当前默认版本：`2.1.6`
- Image：`docker.io/apecloud/aperag-enterprise:2.1.6`

## 停止/重启

```bash
# 停止（保留数据）
docker compose down

# 停止并清除所有数据卷（危险！不可恢复）
docker compose down -v
```

## 问题排查

```bash
# 查看各服务日志
docker compose logs api
docker compose logs indexing-worker

# 检查服务状态
docker compose ps
```
