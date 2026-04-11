const vscode = require("vscode");

const DEFAULT_INTENT_API_URL = "http://127.0.0.1:5000/api/llm/intent";
const DEFAULT_EXECUTE_API_URL = "http://127.0.0.1:5000/api/tasks/execute";

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

  context.subscriptions.push(askIntentDisposable, executeTaskDisposable);
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
        enabled: projectType.label === "python",
        command: "pip install -r requirements.txt",
      },
      test: {
        enabled: projectType.label === "python",
        framework: "pytest",
        command: "python -m pytest",
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
    "[仓库]",
    `仓库路径：${result.repository?.repo_path || ""}`,
    `分支：${result.repository?.branch || ""}`,
    `代码来源：${result.repository?.repo_url || ""}`,
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
  }

  if (result.test_result) {
    lines.push("", "[测试执行]");
    lines.push(`状态：${result.test_result.status}`);
    lines.push(`命令：${result.test_result.command}`);
    lines.push(`返回码：${result.test_result.returncode}`);
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
