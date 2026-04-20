const vscode = require("vscode");

const DEFAULT_INTENT_API_URL = "http://127.0.0.1:5000/api/llm/intent";
const DEFAULT_EXECUTE_API_URL = "http://127.0.0.1:5000/api/tasks/execute";
const DEFAULT_HISTORY_API_URL = "http://127.0.0.1:5000/api/tasks/history";

function activate(context) {
  const askIntentDisposable = vscode.commands.registerCommand(
    "cloudCicdAssistant.askIntent",
    async () => {
      const userInput = await vscode.window.showInputBox({
        prompt: "输入你的 CI/CD 需求，例如：帮我部署这个项目",
        placeHolder: "帮我部署这个项目",
        ignoreFocusOut: true,
      });

      if (!userInput) {
        return;
      }

      const config = vscode.workspace.getConfiguration("cloudCicdAssistant");
      const apiUrl = config.get("intentApiUrl", DEFAULT_INTENT_API_URL);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Cloud CI/CD Assistant 正在识别意图",
          cancellable: false,
        },
        async () => {
          try {
            const result = await postJson(apiUrl, { user_input: userInput });
            const message = [
              `用户输入：${result.user_input}`,
              `识别意图：${result.intent}`,
              `置信度：${result.confidence}`,
              `原因：${result.reason}`,
              `建议动作：${result.suggested_action}`,
              `模型：${result.model}`,
            ].join("\n");

            await showResultDocument("Intent Result", message);
            vscode.window.showInformationMessage("意图识别完成");
          } catch (error) {
            showError(error);
          }
        }
      );
    }
  );

  const executeTaskDisposable = vscode.commands.registerCommand(
    "cloudCicdAssistant.executeTask",
    async () => {
      const payload = await collectTaskPayload();
      if (!payload) {
        return;
      }

      const config = vscode.workspace.getConfiguration("cloudCicdAssistant");
      const apiUrl = config.get("executeApiUrl", DEFAULT_EXECUTE_API_URL);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Cloud CI/CD Assistant 正在执行任务",
          cancellable: false,
        },
        async () => {
          try {
            const result = await postJson(apiUrl, payload);
            const message = formatExecutionResult(result);
            await showResultDocument("Execution Result", message);
            vscode.window.showInformationMessage(`任务执行完成，当前状态：${result.status}`);
          } catch (error) {
            showError(error);
          }
        }
      );
    }
  );

  const viewTaskHistoryDisposable = vscode.commands.registerCommand(
    "cloudCicdAssistant.viewTaskHistory",
    async () => {
      const config = vscode.workspace.getConfiguration("cloudCicdAssistant");
      const apiUrl = config.get("historyApiUrl", DEFAULT_HISTORY_API_URL);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Cloud CI/CD Assistant 正在读取任务历史",
          cancellable: false,
        },
        async () => {
          try {
            const listResult = await getJson(apiUrl);
            const records = Array.isArray(listResult.records) ? listResult.records : [];

            if (records.length === 0) {
              vscode.window.showInformationMessage("当前还没有任务历史记录");
              return;
            }

            const picked = await vscode.window.showQuickPick(
              records.map((record) => ({
                label: `#${record.id} ${record.status || "unknown"} · ${record.intent || "unknown"}`,
                description: record.summary || record.repo_url || "",
                detail: `${record.created_at || ""} ${record.repo_url || ""}`.trim(),
                recordId: record.id,
              })),
              {
                title: "选择要查看的任务历史",
                ignoreFocusOut: true,
                matchOnDescription: true,
                matchOnDetail: true,
              }
            );

            if (!picked) {
              return;
            }

            const detailResult = await getJson(`${apiUrl}/${picked.recordId}`);
            const message = formatHistoryResult(detailResult);
            await showResultDocument(`Task History #${picked.recordId}`, message);
            vscode.window.showInformationMessage(`已打开任务历史 #${picked.recordId}`);
          } catch (error) {
            showError(error);
          }
        }
      );
    }
  );

  context.subscriptions.push(
    askIntentDisposable,
    executeTaskDisposable,
    viewTaskHistoryDisposable
  );
}

async function collectTaskPayload() {
  const userInput = await vscode.window.showInputBox({
    prompt: "输入任务描述，例如：拉取这个 Python 项目，跑测试并部署到 Docker",
    placeHolder: "拉取这个 Python 项目，跑测试并部署到 Docker",
    ignoreFocusOut: true,
  });
  if (!userInput) {
    return null;
  }

  const repoUrl = await vscode.window.showInputBox({
    prompt: "输入目标仓库地址",
    placeHolder: "https://github.com/your-name/your-repo.git",
    ignoreFocusOut: true,
  });
  if (!repoUrl) {
    return null;
  }

  const projectType = await vscode.window.showQuickPick(
    [
      { label: "python", detail: "使用 Python 执行器和 pytest" },
      { label: "nodejs", detail: "后续扩展" },
      { label: "java", detail: "后续扩展" },
    ],
    {
      title: "选择项目类型",
      ignoreFocusOut: true,
    }
  );
  if (!projectType) {
    return null;
  }

  const branch = await vscode.window.showInputBox({
    prompt: "输入分支名，默认 main",
    placeHolder: "main",
    value: "main",
    ignoreFocusOut: true,
  });
  if (branch === undefined) {
    return null;
  }

  const deployTarget = await vscode.window.showQuickPick(
    [
      { label: "docker", detail: "当前已实现" },
      { label: "server", detail: "后续扩展" },
      { label: "cloud", detail: "后续扩展" },
    ],
    {
      title: "选择部署目标",
      ignoreFocusOut: true,
    }
  );
  if (!deployTarget) {
    return null;
  }

  const rawImageName = deployTarget.label === "docker"
    ? await vscode.window.showInputBox({
        prompt: "输入 Docker 镜像名，默认根据仓库名生成",
        placeHolder: "demo-app",
        value: inferImageName(repoUrl),
        ignoreFocusOut: true,
      })
    : "";
  if (rawImageName === undefined) {
    return null;
  }

  const normalizedImageName = normalizeDockerName(rawImageName || inferImageName(repoUrl));

  const rawContainerName = deployTarget.label === "docker"
    ? await vscode.window.showInputBox({
        prompt: "输入 Docker 容器名，默认与镜像名相同",
        placeHolder: normalizedImageName,
        value: normalizedImageName,
        ignoreFocusOut: true,
      })
    : "";
  if (rawContainerName === undefined) {
    return null;
  }

  const normalizedContainerName = normalizeDockerName(rawContainerName || normalizedImageName);

  if (deployTarget.label === "docker") {
    const notices = [];
    if ((rawImageName || inferImageName(repoUrl)) !== normalizedImageName) {
      notices.push(`镜像名已规范化为：${normalizedImageName}`);
    }
    if ((rawContainerName || normalizedImageName) !== normalizedContainerName) {
      notices.push(`容器名已规范化为：${normalizedContainerName}`);
    }
    if (notices.length > 0) {
      vscode.window.showWarningMessage(notices.join("；"));
    }
  }

  return {
    user_input: userInput,
    intent: "deploy_project",
    project: {
      repo_url: repoUrl,
      branch: branch || "main",
      project_type: projectType.label,
    },
    execution: {
      install: {
        enabled: projectType.label === "python" || projectType.label === "nodejs",
        command: defaultInstallCommand(projectType.label),
      },
      test: {
        enabled: projectType.label === "python" || projectType.label === "nodejs",
        framework: defaultTestFramework(projectType.label),
        command: defaultTestCommand(projectType.label),
        timeout_seconds: 600,
      },
      deploy: {
        enabled: true,
        target: deployTarget.label,
        docker: deployTarget.label === "docker"
          ? {
              dockerfile_path: "Dockerfile",
              image_name: normalizedImageName,
              image_tag: "latest",
              container_name: normalizedContainerName,
              ports: [],
              env: {},
            }
          : null,
      },
    },
  };
}

function formatExecutionResult(result) {
  const lines = [
    `整体状态：${result.status}`,
    `消息：${result.message}`,
    "",
    "[执行概览]",
    `总耗时：${formatDuration(result.timings?.total)}`,
    `代码拉取：${result.status_overview?.repository || ""}`,
    `依赖安装：${result.status_overview?.install || ""}`,
    `测试执行：${result.status_overview?.test || ""}`,
    `质量门禁：${result.status_overview?.quality_gate || ""}`,
    `部署执行：${result.status_overview?.deploy || ""}`,
    `部署监测：${result.status_overview?.monitoring || ""}`,
    "",
    "[仓库]",
    `仓库路径：${result.repository?.repo_path || ""}`,
    `分支：${result.repository?.branch || ""}`,
    `代码来源：${result.repository?.repo_url || ""}`,
    `拉取耗时：${formatDuration(result.timings?.repository)}`,
    "",
    "[测试门禁]",
    `门禁状态：${result.dispatch_result?.status || ""}`,
    `是否阻塞：${result.dispatch_result?.blocked ? "是" : "否"}`,
  ];

  if (result.install_result) {
    lines.push("", "[依赖安装]");
    lines.push(`状态：${result.install_result.status}`);
    lines.push(`命令：${result.install_result.command}`);
    lines.push(`返回码：${result.install_result.returncode}`);
    lines.push(`耗时：${formatDuration(result.timings?.install ?? result.install_result.duration_seconds)}`);
  }

  if (result.test_result) {
    lines.push("", "[测试执行]");
    lines.push(`状态：${result.test_result.status}`);
    lines.push(`命令：${result.test_result.command}`);
    lines.push(`返回码：${result.test_result.returncode}`);
    lines.push(`耗时：${formatDuration(result.timings?.test ?? result.test_result.duration_seconds)}`);
    lines.push("输出：");
    lines.push(result.test_result.stdout || "");
    if (result.test_result.stderr) {
      lines.push("错误输出：");
      lines.push(result.test_result.stderr);
    }
  }

  if (result.deploy_result) {
    lines.push("", "[部署执行]");
    lines.push(`状态：${result.deploy_result.status}`);
    lines.push(`目标：${result.deploy_result.target || ""}`);
    lines.push(`耗时：${formatDuration(result.timings?.deploy ?? result.deploy_result.duration_seconds)}`);
    if (result.deploy_result.image) {
      lines.push(`镜像：${result.deploy_result.image}`);
    }
    if (result.deploy_result.container_name) {
      lines.push(`容器名：${result.deploy_result.container_name}`);
    }
    if (result.deploy_result.container_id) {
      lines.push(`容器 ID：${result.deploy_result.container_id}`);
    }
    if (result.deploy_result.error) {
      lines.push(`错误：${result.deploy_result.error}`);
    }
  }

  if (result.monitoring_result) {
    lines.push("", "[部署后监测]");
    lines.push(`状态：${result.monitoring_result.status || ""}`);
    lines.push(`目标：${result.monitoring_result.target || ""}`);
    lines.push(`耗时：${formatDuration(result.timings?.monitoring ?? result.monitoring_result.duration_seconds)}`);
    if (result.monitoring_result.container_status) {
      lines.push(`容器状态：${result.monitoring_result.container_status}`);
    }
    if (typeof result.monitoring_result.running === "boolean") {
      lines.push(`是否运行中：${result.monitoring_result.running ? "是" : "否"}`);
    }
    if (result.monitoring_result.inspect_command) {
      lines.push(`检查命令：${result.monitoring_result.inspect_command}`);
    }
    if (result.monitoring_result.inspect_stderr) {
      lines.push("错误输出：");
      lines.push(result.monitoring_result.inspect_stderr);
    }
  }

  return lines.join("\n");
}

function formatHistoryResult(record) {
  const lines = [
    `任务记录：#${record.id || ""}`,
    `创建时间：${record.created_at || ""}`,
    `整体状态：${record.status || ""}`,
    `消息：${record.message || ""}`,
    "",
    "[执行概览]",
    `总耗时：${formatDuration(record.timings?.total)}`,
    `代码拉取：${record.status_overview?.repository || ""}`,
    `依赖安装：${record.status_overview?.install || ""}`,
    `测试执行：${record.status_overview?.test || ""}`,
    `质量门禁：${record.status_overview?.quality_gate || ""}`,
    `部署执行：${record.status_overview?.deploy || ""}`,
    `部署监测：${record.status_overview?.monitoring || ""}`,
    "",
    "[任务信息]",
    `意图：${record.intent || ""}`,
    `项目类型：${record.project_type || ""}`,
    `仓库：${record.repo_url || ""}`,
  ];

  if (record.repository) {
    lines.push("", "[仓库]");
    lines.push(`仓库路径：${record.repository.repo_path || ""}`);
    lines.push(`分支：${record.repository.branch || ""}`);
    lines.push(`代码来源：${record.repository.repo_url || ""}`);
    lines.push(`拉取耗时：${formatDuration(record.timings?.repository ?? record.repository.duration_seconds)}`);
  }

  if (record.dispatch_result) {
    lines.push("", "[测试门禁]");
    lines.push(`门禁状态：${record.dispatch_result.status || ""}`);
    lines.push(`是否阻塞：${record.dispatch_result.blocked ? "是" : "否"}`);
    if (record.dispatch_result.message) {
      lines.push(`门禁消息：${record.dispatch_result.message}`);
    }
  }

  if (record.install_result) {
    lines.push("", "[依赖安装]");
    lines.push(`状态：${record.install_result.status || ""}`);
    lines.push(`命令：${record.install_result.command || ""}`);
    lines.push(`返回码：${record.install_result.returncode ?? ""}`);
    lines.push(`耗时：${formatDuration(record.timings?.install ?? record.install_result.duration_seconds)}`);
  }

  if (record.test_result) {
    lines.push("", "[测试执行]");
    lines.push(`状态：${record.test_result.status || ""}`);
    lines.push(`命令：${record.test_result.command || ""}`);
    lines.push(`返回码：${record.test_result.returncode ?? ""}`);
    lines.push(`耗时：${formatDuration(record.timings?.test ?? record.test_result.duration_seconds)}`);
    if (record.test_result.stdout) {
      lines.push("输出：");
      lines.push(record.test_result.stdout);
    }
    if (record.test_result.stderr) {
      lines.push("错误输出：");
      lines.push(record.test_result.stderr);
    }
  }

  if (record.deploy_result) {
    lines.push("", "[部署执行]");
    lines.push(`状态：${record.deploy_result.status || ""}`);
    lines.push(`目标：${record.deploy_result.target || ""}`);
    lines.push(`耗时：${formatDuration(record.timings?.deploy ?? record.deploy_result.duration_seconds)}`);
    if (record.deploy_result.image) {
      lines.push(`镜像：${record.deploy_result.image}`);
    }
    if (record.deploy_result.container_name) {
      lines.push(`容器名：${record.deploy_result.container_name}`);
    }
    if (record.deploy_result.container_id) {
      lines.push(`容器 ID：${record.deploy_result.container_id}`);
    }
    if (record.deploy_result.error) {
      lines.push(`错误：${record.deploy_result.error}`);
    }
  }

  if (record.monitoring_result) {
    lines.push("", "[部署后监测]");
    lines.push(`状态：${record.monitoring_result.status || ""}`);
    lines.push(`目标：${record.monitoring_result.target || ""}`);
    lines.push(`耗时：${formatDuration(record.timings?.monitoring ?? record.monitoring_result.duration_seconds)}`);
    if (record.monitoring_result.container_status) {
      lines.push(`容器状态：${record.monitoring_result.container_status}`);
    }
    if (typeof record.monitoring_result.running === "boolean") {
      lines.push(`是否运行中：${record.monitoring_result.running ? "是" : "否"}`);
    }
    if (record.monitoring_result.inspect_command) {
      lines.push(`检查命令：${record.monitoring_result.inspect_command}`);
    }
    if (record.monitoring_result.inspect_stderr) {
      lines.push("错误输出：");
      lines.push(record.monitoring_result.inspect_stderr);
    }
  }

  return lines.join("\n");
}

function inferImageName(repoUrl) {
  const parts = repoUrl.split("/");
  const repoName = parts[parts.length - 1] || "app";
  return normalizeDockerName(repoName.replace(/\.git$/, "") || "app");
}

function normalizeDockerName(value) {
  return String(value || "app")
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^[._-]+|[._-]+$/g, "")
    || "app";
}

function defaultInstallCommand(projectType) {
  const mapping = {
    python: "pip install -r requirements.txt",
    nodejs: "npm install",
    java: "mvn dependency:resolve",
  };
  return mapping[projectType] || "";
}

function defaultTestFramework(projectType) {
  const mapping = {
    python: "pytest",
    nodejs: "npm",
    java: "maven",
  };
  return mapping[projectType] || "";
}

function defaultTestCommand(projectType) {
  const mapping = {
    python: "python -m pytest",
    nodejs: "npm test",
    java: "mvn test",
  };
  return mapping[projectType] || "";
}

function formatDuration(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }
  return `${value.toFixed(3)}s`;
}

async function postJson(apiUrl, payload) {
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "后端请求失败");
  }
  return result;
}

async function getJson(apiUrl) {
  const response = await fetch(apiUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "后端请求失败");
  }
  return result;
}

async function showResultDocument(title, content) {
  const document = await vscode.workspace.openTextDocument({
    content,
    language: "text",
  });
  await vscode.window.showTextDocument(document, { preview: false });
}

function showError(error) {
  const detail = error instanceof Error ? error.message : String(error);
  vscode.window.showErrorMessage(`调用后端失败：${detail}`);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
