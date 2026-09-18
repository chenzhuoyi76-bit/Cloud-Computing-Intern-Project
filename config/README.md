# 配置分层约定（A0）

**当前 `app.py` 不加载 `config/examples/`。两份 JSON 是后续实现的配置契约草案，不是可运行的 Agent 安装包或安全开关。** 没有配置加载器、认证或远程路由隔离时，不得通过填写示例就开放云端访问。

## 1. 当前有效配置

`backend/config.py` 读取根目录 `.env`，已有进程环境变量优先。允许提交的模板为根目录 `.env.example`。

| 环境变量 | 当前用途与默认行为 |
| --- | --- |
| `OPENAI_API_KEY` | 旧意图识别所需的真实 key，仅放本地秘密配置 |
| `OPENAI_MODEL`、`OPENAI_BASE_URL`、`OPENAI_TIMEOUT` | 旧意图识别的模型、地址、请求超时；以代码默认值为准 |
| `TASK_WORKSPACE_ROOT` | 不设置则为仓库内 `runtime/workspaces` |
| `DATABASE_URL` | 不设置则为仓库内 `runtime/app.db` 的 SQLite URL |

可选路径应使用绝对路径；不要用空字符串代替“不设置”，否则会覆盖代码默认值。A0 未更改这些键的加载逻辑，也未新增 `AGENT_*` 运行时配置。

## 2. Agent 示例的预期用途

| 文件 | 预期环境 | 不代表什么 |
| --- | --- | --- |
| `examples/agent-local.example.json` | Windows 开发，隔离测试；连接实验集群需显式只读配置 | 不需要本机 VM；不会自动创建数据库或集群 |
| `examples/agent-cloud.example.json` | ECS 上的未来服务，独立 PostgreSQL、受限目录、内网/隧道入口 | 不创建 ECS，不安装 systemd，不开放公网、不授予写权限 |

示例共享一个登记集群 `lab-cluster` 和实验 namespace `release-lab`，这两个名称尚未实际创建。5100 是规划的新 API 端口，用于区分旧 5000 服务，不是已经监听的端口。诊断和恢复均默认关闭，实施后逐阶段验收再启用。

`*_env` 表示未来由指定进程从环境变量读取值，而不是把变量名当作值。`AGENT_DATABASE_URL` 的值不能出现在已提交 JSON 中；常规开发/云端预计使用专用 PostgreSQL，单测可用独立测试数据库，不把 SQLite 单测当作 PostgreSQL 行为验证。

| 变量引用 | 预期读取者 | 限制 |
| --- | --- | --- |
| `AGENT_DATABASE_URL` | API/Worker/执行器各自进程 | 同名变量在不同服务可映射不同数据库账号，禁止共享超级用户 |
| `AGENT_READONLY_KUBECONFIG` | 只读证据网关 | 仅为文件路径；模型进程不接收文件、挂载或此变量 |
| `AGENT_MODEL_ID`、`AGENT_MODEL_BASE_URL` | 诊断进程 | 接口和工具调用兼容性需在 A2 验证 |
| `AGENT_MODEL_API_KEY` | 诊断进程 | 不传给插件、执行器或模型工具返回值 |

写 kubeconfig **不包含在这两份共享示例中**。A4 另为独立执行器配置，仅允许指定恢复动作；不能把只读 kubeconfig 替换成管理员 kubeconfig 来“省配置”。公共文件里有 `recovery.enabled` 也不等于批准了动作，运行时必须同时满足审批、授权、策略和目标前置条件。

## 3. 私密内容与版本控制

- 可提交：无秘密的 `.env.example`、`config/examples/*.example.json`、脱敏测试样本和文档。
- 不可提交：`.env`/`.env.*` 实际配置、`config/local/` 的覆盖配置、`secrets/`、`.kube/`、实际 kubeconfig、token、数据库和运行日志。
- 本地私密文件统一放 `config/local/`、`secrets/` 或已忽略的 `runtime/`；不要随意散落到源码、测试或文档目录。云端文件放服务专用的受限目录，按进程授予读取权限。
- `.gitignore` 新增常见凭据路径、数据库扩展名保护，但无法识别任意文件里的秘密，更不能替代 ACL、RBAC、脱敏或历史秘密扫描。
- 忽略规则不影响已跟踪文件。如误提交秘密，先撤销/轮换凭证，再单独安排仓库清理；不要仅删除本地文件就视为处理完毕。

## 4. 后续加载器验收约束

这些是未来 A1/A3/A7 的实现要求，而非 A0 已提供的能力：校验版本与未知字段；缺配置失败关闭；不隐式回退到管理员 kubeconfig；远程模式不能注册 legacy 执行路由；按进程投影配置，不能将整份秘密环境复制给模型/工具；日志只记录脱敏配置和版本。

权限身份、模型版本、网关凭证、执行器凭证和费用预算在相应阶段补完整契约和测试，本阶段不填入猜测的真实值。
