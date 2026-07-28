# LLM Prompts

本目录整理自实际工作流文件：`workflow/7x24小时ai工单分诊自动化工作流.json`。

## Prompt 清单

| 文件 | 工作流节点 | 使用场景 |
|------|------|------|
| [`01-ticket-analysis.md`](01-ticket-analysis.md) | `AI工单情况及用户情感分析` | 分析工单情感、紧急度、分类和处理方式 |
| [`02-urgent-solution.md`](02-urgent-solution.md) | `AI解决方案生成` | 为紧急工单生成立即行动方案 |
| [`03-auto-reply.md`](03-auto-reply.md) | `AI自动回复生成1` | 根据知识库内容生成客户邮件回复 |

## 模型配置

上述 3 个 Agent 节点分别连接到工作流中的 `OpenAI Chat Model`、`OpenAI Chat Model1` 和 `OpenAI Chat Model3`，实际使用模型均为 `qwen-max`。

这 3 个 Chat Model 节点只配置模型，没有额外的独立 Prompt；具体 Prompt 由对应 Agent 节点中的 `text` 字段提供。

## 说明

- 文档中的 `{{ ... }}` 和 `$(...)` 是 n8n 表达式，运行时会从工作流输入或上游节点读取数据。
- 以下内容按实际工作流整理，保留原 Prompt 的措辞和约束，没有擅自修正其中可能存在的冲突。
