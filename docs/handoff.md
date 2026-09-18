# 新会话交接说明

更新日期：2026-09-18。交接时进度：**A0 已完成；A1 尚未开始；集群搭建和故障用例尚未验收。**

本文是接手索引与状态快照，不替代主方案。新会话先检查当前文件和 Git 状态；若用户已经继续修改，以新的代码、验证记录和用户说明为准，不机械恢复成本快照。

## 1. 用户目标与项目方向

项目最初是导师指导下的 CI/CD 实践，现在由用户自主升级。用户关心技术深度、工程难度、实际用途、工程取舍和可复现落地，不要求市场上没有同类高星项目，也不希望只做一层模型调用的演示。

已确定方向：**Kubernetes 发布故障诊断与受控恢复 Agent**。关联一次发布的变更与运行证据，主动调查失败原因；在人工批准后执行有限恢复，并独立验证目标版本和业务是否真正恢复。

不要再次把主线改回“支持更多语言/部署器”，也不要无故推倒已有项目。导师指导的原始实践与个人后续迭代应区分，不包装成阿里云内部生产项目；当前没有企业用户采用或生产效果的证据。

## 2. 接手先读什么

| 顺序 | 文件 | 用途 |
| --- | --- | --- |
| 1 | [实施清单](checklist.md) | A 业务、B 集群、C 故障用例三条工作线；只按验收证据勾选 |
| 2 | [主技术方案](tech_design.md) | 项目目标、架构、技术选型、资源计划及验收标准 |
| 3 | [ADR-0001](adr/0001-incremental-readonly-agent.md) | 已采纳的范围、复用边界、模块位置和取舍 |
| 4 | [A0 基线报告](baselines/2026-09-18-a0.md) | 实际测试、现有接口/数据库/插件/执行器清单及缺口 |
| 5 | [配置约定](../config/README.md) | 当前有效环境变量与未来配置草案的区别 |

`docs/ai_agent_delivery_plan.md` 是之前的备选草案，不再作为实施依据；与主方案冲突时以 `tech_design.md` 和已采纳 ADR 为准。旧 README 主要描述 legacy 功能，不能由此推断 Agent 已实现。

## 3. 已定架构与范围

- 复用 Flask、SQLAlchemy、现有 VS Code 插件；旧 Python/Node.js/Java runner 和 Docker/server/Azure deployer 保留本地 legacy 用途，不作为模型工具或远程任意执行 API。
- 第一版只接入一个登记集群、一个受邀团队、指定 namespace 中的无状态 HTTP Deployment + Service。用户登记已有发布，Agent 首版不负责构建和执行陌生仓库。
- 首批诊断场景：镜像拉取失败、启动崩溃、Readiness 失败。其他故障在首批闭环后扩展。
- 工作方式：确定性流程包裹有界 ReAct 式只读调查。计划复用固定版本的 HolmesGPT，通过 `DiagnosticEngine` 适配；模型、SDK 版本和工具调用兼容性尚未验证，不能提前宣称可用。
- 计划使用 PostgreSQL + SQLAlchemy/Alembic，持久化任务、事件、证据、审批；低并发数据库 job/租约，不先堆 Redis/Celery 或多个 Agent 框架。现在仍是同步 Flask + SQLite 历史。
- 首版唯一恢复动作是 `restore_verified_pod_template`，只能恢复登记 Deployment 中有健康验证记录的模板；审批绑定目标 UID、配置/计划哈希、版本与有效期，缺可信基线或发生漂移时不执行。
- 模型不持有 Kubernetes 凭证；只读网关、独立恢复执行器、验证器责任分开。写操作必须等可靠任务、授权和审批就绪；不开放任意 shell、kubectl 或任意 patch。
- 恢复成功需校验版本、资源归属、就绪和业务断言，不能只看 Pod Running、HTTP 200 或命令返回 0。无证据就明确未验证，不能默认成功。

GitOps 管理、外部配置/数据库变更、无可信旧版本等场景先移交人工。不做节点重启、修改安全组/RBAC/Secret、删除 namespace/PVC、无人审批生产发布或跨团队多租户 SaaS。

上述 Agent、安全与远程运行能力目前是**设计约束**，不是已实现功能。

## 4. A0 已交付内容

| 内容 | 位置与状态 |
| --- | --- |
| 现状与测试基线 | `docs/baselines/2026-09-18-a0.md`，已记录 40 个测试通过及环境偏差 |
| 已安装包快照 | `docs/baselines/requirements-2026-09-18.txt`，观测记录，不替代产品依赖锁定 |
| 第一份 ADR | `docs/adr/0001-incremental-readonly-agent.md`，范围与模块位置已确定 |
| 配置说明与草案 | `config/README.md`、`config/examples/agent-local.example.json`、`agent-cloud.example.json` |
| 基线复跑脚本 | `scripts/check_baseline.ps1`，已实际运行成功 |
| 忽略与配置模板 | `.gitignore`、`.env.example`，增加私密路径/数据库保护及当前有效配置说明 |
| 清单状态 | `docs/checklist.md` 仅 A0 的 5 项已勾选 |

JSON 示例均标记 `design_only_not_loaded`；旧 `app.py` 不会读取，里面的关闭 legacy、认证、诊断和恢复开关尚无运行时实现。A0 没有改业务执行代码、数据库结构、依赖版本，也没有操作 ECS。

## 5. 本地环境与安全复测

工作目录：`D:\AI-CICD\Cloud-Computing-Intern-Project`；Windows PowerShell。已有 `venv`，无需为了复测启动 Flask、Docker、虚拟机或真实部署。

最后一次 A0 实测：Windows 11 / Python 3.13.3 / Node.js v22.16.0；40 个 `unittest` 全部通过，无失败/错误/跳过；`pip check` 和插件 `node --check` 通过。JSON 解析、文档文件链接及忽略规则检查通过。部署和模型测试主要使用 Mock，未验证真实 Kubernetes/Azure、插件 UI、Linux 或云端容量。

从项目根目录复跑：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_baseline.ps1
```

重要：`tests/test_llm_api.py` 在导入 `app` 时就会初始化数据库。优先使用上述脚本，它在导入前覆盖为内存数据库、假模型配置，避免接触真实 `runtime/app.db`。新测试仍需审查网络和命令副作用，脚本不是沙箱。

当前 venv 的 Flask 为 **3.1.0**，根目录 `requirements.txt` 要求 **3.1.3**。这项差异已记录，不要未经验证就升级正在使用的 venv；后续另建隔离环境对齐并记录结果。方案中的云端 Python 3.12 尚未在此项目中验证。

## 6. Git 与文件状态

开始交接时 HEAD：`957b125e7e5b9fb511df87cfb906cb1a95515888`。助手在本会话没有执行暂存、commit 或创建/切换分支。交接期间最后一次检查已观察到下列文件进入暂存区，Git 状态可能继续变化，接手时重新检查；**未提交不等于可以丢弃**。

```text
相对基线修改的文件：
  .env.example
  .gitignore
  docs/tech_design.md

相对基线新增的文件/目录：
  config/
  docs/adr/
  docs/ai_agent_delivery_plan.md
  docs/baselines/
  docs/checklist.md
  docs/handoff.md
  scripts/
```

`tech_design.md` 与旧备选草案包含 A0 之前已经存在的工作，不要覆盖或回滚。A0 后业务代码、现有测试、产品依赖和插件源码与上述 HEAD 无差异。新会话先运行 `git status --short`，不要使用 `git clean`、`reset --hard` 或把未跟踪目录当作无用文件删除。

真实 `.env`、runtime 历史/日志/仓库、kubeconfig、token 不应进入提交、报告或模型上下文。本交接没有复制任何真实凭证。Git 忽略规则不是完整秘密扫描，也不会删除历史提交中的秘密。

## 7. ECS 与集群现实约束

用户无法在本机运行虚拟机，后续实验放 ECS，不要求再折腾本机 VM/WSL2。

截至用户最后确认：只有一台 **CentOS 7.9 64 位、2 vCPU / 2 GiB** ECS；另外两台尚未创建。云盘、内核、地域/VPC、剩余额度和可选规格未确认，未建立可供本项目验证的集群。本次交接未连接 ECS。

规划是 K3s 1 control-plane + 2 worker，现有 2 GiB 实例倾向作为 worker；控制节点优先新建且有更多内存，实际以额度核实为准。系统更换前需要用户确认、备份与恢复检查，不擅自重装现有 CentOS。自建 K3s 不等于 ACK，单控制面不等于 HA。

B0/B1 先确认资源、数据与系统，随后 B2/B3/B4 做网络、集群和最小权限；C1/C2 准备健康应用与前三类故障。创建/升配资源、重装、开放公网、清理实例和注入故障均需另行明确授权，本交接不授权执行。

## 8. 下一步建议：A1 的第一个可验证切片

若用户在新会话要求继续业务开发，优先开始 A1，而不是再次只写宏观方案。没有真实集群不妨碍先做固定样本与契约，但不能提前勾选 A1 的真实集群验收。

1. 阅读上述文档与现有代码，核对工作树，安全复跑 A0；区分原有缺口与新回归。
2. 先建立 Cluster/Application/Release 输入契约及 Evidence 结构，明确资源身份、登记范围、digest、来源、时间、缺失原因和验证信息。不把客户端的“已健康”布尔值当作可信发布证明。
3. 做独立于真实网络的范围校验、对象归属关联与快照规范化/哈希；用合成或脱敏的 Deployment/ReplicaSet/Pod/Service/EndpointSlice 样本验证。测试跨 namespace、UID 不匹配、无 owner、证据缺失和状态更新不应造成配置漂移。
4. 再推进只读 Kubernetes 适配器的限范围查询、超时、分页、错误分类、日志脱敏和截断标记。引入新依赖前核对官方文档/兼容性，使用独立环境，不静默扩大权限。
5. 记录本轮实际完成的 A1 子项、测试数、尚未完成的真实验证。待 B3/B4/C1 就绪后补真实集群契约测试，再判断整个 A1 是否可验收。

A1 模块位置以 ADR 为准，主要涉及 `backend/registry/`、`backend/tools/`、`backend/evidence/`、模型/schema 及对应测试；这些目录中的新能力尚未实现。不要一次生成所有 A2-A7 的空类，也不要为了演示提前接任意 shell、审批写操作或模型自动恢复。

旧链路的安装失败仍尝试测试、clone/deploy 超时不足、无健康 URL 默认通过、缺认证与统一脱敏等问题已经列在 A0 报告。保留兼容性，相关修复单独记录，不把它们伪装为此次 Agent 回归。

## 9. 给新会话的开场消息

```text
请接手 D:\AI-CICD\Cloud-Computing-Intern-Project。
先读 docs/handoff.md，再按其中顺序阅读 checklist、tech_design、ADR 和基线报告，并检查实际代码与 git status。
当前只完成了 A0；请继续 A1，先做集群/应用/发布登记和证据结构、范围/归属校验、快照规范化及固定样本单测，再推进只读 Kubernetes 适配。
保留所有未提交改动，不读取或输出真实秘密，不操作 ECS，不改动旧 CI/CD 的运行方式。
真实集群尚未搭好：可以先做离线契约测试，但不要把 Mock 通过或配置草案写成真实集群已验收。
请实际实现并测试，最后说明完成项、验证结果和剩余依赖。
```

若新会话要先做 ECS 准备，把上面的 A1 请求换成“先推进 B0/B1 的资源和系统确认，先只读检查，不创建资源或重装”。
