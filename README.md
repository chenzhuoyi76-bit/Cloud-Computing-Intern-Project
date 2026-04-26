## 项目简介

这是我的实习项目，目标是做一个基于大模型的本地 AI CI/CD 原型工具。

当前形态是：
- 一个最小可用的 VS Code 插件
- 一个本地运行的 Flask 后端
- 后端负责意图识别、任务分发、代码拉取、测试执行和基础部署

目前项目重点是先在本机上跑通完整链路，再逐步扩展到更多语言、更多部署目标和更完整的产品形态。

Python 版本：3.13.3

## 当前已完成

目前已经打通了下面这条最小闭环：

1. 用户通过 VS Code 插件或 HTTP 接口发起任务
2. 后端调用 OpenAI 做意图识别
3. 后端进行任务分发和质量门禁判断
4. 拉取目标 GitHub 仓库到本地工作目录
5. 针对 Python 项目安装依赖并执行 `python -m pytest`
6. 单元测试通过后执行 Docker 部署
7. 返回完整执行结果

已经验证通过的能力包括：
- Flask 后端 API
- VS Code 最小插件交互
- 意图识别接口 `/api/llm/intent`
- 分发和卡点接口 `/api/llm/dispatch`
- 统一执行接口 `/api/tasks/execute`
- Python `pytest` 执行器
- Node.js `npm` 测试执行器
- Java Maven 测试执行器
- Docker 部署器

## 当前项目结构

```text
backend/
  routes/
  schemas/
  services/
tests/
vscode-extension/
docs/
app.py
requirements.txt
```

关键模块说明：
- `backend/routes/llm.py`：意图识别接口
- `backend/routes/dispatch.py`：任务分发与质量门禁接口
- `backend/routes/tasks.py`：统一任务准备与执行接口
- `backend/schemas/task_request.py`：结构化任务请求校验
- `backend/services/repo_fetcher.py`：代码拉取器
- `backend/services/task_executor.py`：统一执行流水线
- `backend/services/test_runners/`：测试执行适配层
- `backend/services/deployers/`：部署执行适配层
- `vscode-extension/`：最小 VS Code 插件

## 本地运行

### 1. 安装依赖

建议先进入虚拟环境。

`cmd`：
```cmd
venv\Scripts\activate.bat
```

PowerShell：
```powershell
.\venv\Scripts\Activate.ps1
```

安装依赖：
```cmd
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env`，至少包含：

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT=60
```

### 3. 启动后端

```cmd
python app.py
```

默认地址：
```text
http://127.0.0.1:5000
```

### 4. 启动 VS Code 插件

1. 用 VS Code 打开 `vscode-extension` 目录
2. 按 `F5`
3. 在新的 Extension Development Host 窗口中执行命令 `Cloud CI/CD: Ask Assistant`

## 统一执行接口示例

### 真实执行 Python 测试并 Docker 部署

```cmd
curl -X POST http://127.0.0.1:5000/api/tasks/execute ^
  -H "Content-Type: application/json" ^
  -d "{\"intent\":\"deploy_project\",\"project\":{\"repo_url\":\"https://github.com/zche0345/demo.git\",\"project_type\":\"python\"},\"execution\":{\"install\":{\"enabled\":true,\"command\":\"pip install -r requirements.txt\"},\"test\":{\"enabled\":true,\"framework\":\"pytest\",\"command\":\"python -m pytest\",\"timeout_seconds\":600},\"deploy\":{\"enabled\":true,\"target\":\"docker\",\"docker\":{\"dockerfile_path\":\"Dockerfile\",\"image_name\":\"demo-app\",\"image_tag\":\"latest\",\"container_name\":\"demo-app\",\"ports\":[],\"env\":{}}}}}"
```

成功后返回结果中会包含：
- `install_result`
- `test_result`
- `deploy_result`
- `status = deployed`

## 当前设计原则

目前项目按“适配器/执行器”思路在扩展：
- 测试执行按项目类型适配
  - 当前已实现：`python`
  - 当前已实现：`nodejs`
  - 当前已实现：`java`
- 部署执行按部署目标适配
  - 当前已实现：`docker`
  - 计划扩展：`server`、`cloud`

质量门禁规则：
- `deploy_project`
- `package_project`
- `merge_code`

以上任务在当前设计下都要求先通过单元测试，否则流程会被阻塞。

## 当前限制

当前版本仍然是 MVP，主要限制包括：
- 测试执行器已覆盖 Python、Node.js 和 Java
- Java 执行器当前默认按 Maven 项目执行，Gradle 项目需要显式传入 install/test 命令
- 目前只完整实现了 Docker 部署器
- VS Code 插件当前主要用于最小交互演示，还没有完全接入统一执行接口
- 还没有接入 SQLite 日志持久化
- 还没有实现部署后监控检查

## 后续计划

下一步重点方向：
- 把插件接到统一执行接口
- 增加部署后状态检查
- 增加 SQLite 日志与任务历史
- 扩展 Node.js / Java 测试执行器
- 扩展更多部署目标
- 再考虑前后端分离与服务化部署

## 技术设计文档

详细设计见：
- `docs/tech_design.md`
