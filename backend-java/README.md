# MiroFish Java Middleware (Spring Boot)

这是为 MiroFish 生成的 Java Spring Boot 中间层工程，目标是：

- 保留现有前端页面与调用路径（`/api/graph`、`/api/simulation`、`/api/report`）
- 保留 Graphiti 与 OASIS 能力
- 提供 Java 化的中间层入口，便于后续逐步迁移 Python 逻辑到 Java

## 架构说明

- `graph/simulation/report`：默认由 Java 中间层透传到现有 Python Backend（兼容迁移）
- `graphiti`：由 Java 直接通过 HTTP 调用 Graphiti REST
- `oasis`：保留桥接状态接口，当前建议继续由 Python 后端承载仿真核心

## 启动

```bash
cd backend-java
mvn spring-boot:run
```

默认端口：`8080`

## 关键配置（`application.yml`）

- `app.proxy.graph-base-url`：Graph API 上游地址（默认 `http://localhost:5001`）
- `app.proxy.simulation-base-url`：Simulation API 上游地址（默认 `http://localhost:5001`）
- `app.proxy.report-base-url`：Report API 上游地址（默认 `http://localhost:5001`）
- `app.graphiti.base-url`：Graphiti REST 地址（默认 `http://localhost:8000`）
- `app.graphiti.api-key`：Graphiti API Key（可选）

也可用环境变量覆盖：

- `APP_PROXY_GRAPH_BASE_URL`
- `APP_PROXY_SIMULATION_BASE_URL`
- `APP_PROXY_REPORT_BASE_URL`
- `GRAPHITI_BASE_URL`
- `GRAPHITI_API_KEY`

## 接口与文档

- 健康检查：`GET /health`
- Graphiti Swagger：`GET /api/graphiti/docs`
- Graphiti OpenAPI：`GET /api/graphiti/openapi.json`

## 前端切换到 Java 中间层

将前端环境变量设置为：

```bash
VITE_API_BASE_URL=http://localhost:8080
```

这样前端请求会先进入 Java 中间层，再由中间层分发到 Graphiti/Python 组件。
