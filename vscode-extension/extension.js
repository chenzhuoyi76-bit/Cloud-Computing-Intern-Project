const vscode = require("vscode");

const DEFAULT_API_URL = "http://127.0.0.1:5000/api/llm/intent";

function activate(context) {
  const disposable = vscode.commands.registerCommand(
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
      const apiUrl = config.get("apiUrl", DEFAULT_API_URL);

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Cloud CI/CD Assistant 正在识别意图",
          cancellable: false,
        },
        async () => {
          try {
            const response = await fetch(apiUrl, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ user_input: userInput }),
            });

            const result = await response.json();

            if (!response.ok) {
              throw new Error(result.error || "后端请求失败");
            }

            const message = [
              `用户输入：${result.user_input}`,
              `识别意图：${result.intent}`,
              `置信度：${result.confidence}`,
              `原因：${result.reason}`,
              `建议动作：${result.suggested_action}`,
              `模型：${result.model}`,
            ].join("\n");

            vscode.window.showInformationMessage("意图识别完成");
            const document = await vscode.workspace.openTextDocument({
              content: message,
              language: "text",
            });
            await vscode.window.showTextDocument(document, {
              preview: false,
            });
          } catch (error) {
            const detail = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`调用后端失败：${detail}`);
          }
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
