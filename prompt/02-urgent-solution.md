# AI解决方案生成

## 节点信息

- 节点名称：`AI解决方案生成`
- 节点类型：`@n8n/n8n-nodes-langchain.agent`
- 连接模型：`OpenAI Chat Model1`
- 实际模型：`qwen-max`
- 使用分支：紧急工单分支

## Prompt

```text
作为技术支持专家，请为这个紧急问题提供立即行动方案：

  问题：{{ $json.originalData.issue_title }}
  详细描述：{{ $json.originalData.issue_description }}
  问题类型：{{ $json.aiAnalysis.category }}
  客户情绪：{{ $json.aiAnalysis.sentiment }}

  请提供：
  1. 立即检查项（3个最重要的系统检查点）
  2. 临时解决方案（如果可以立即实施）
  3. 与客户沟通的关键话术
  4. 需要通知的团队或人员
重要约束：回答控制在 100 字以内，只写要点，不要表格、不要话术、不要分步骤。
用纯文字，不要任何 markdown 表格和 emoji 表情符号。
用清晰的markdown格式回复。
```

## 输入变量

| 变量 | 来源 | 用途 |
|------|------|------|
| `originalData.issue_title` | 上游数据 | 紧急工单标题 |
| `originalData.issue_description` | 上游数据 | 紧急工单详细描述 |
| `aiAnalysis.category` | 上游 AI 分析结果 | 问题类型 |
| `aiAnalysis.sentiment` | 上游 AI 分析结果 | 客户情绪 |

## 输出用途

输出会经过 `压缩并转义` 节点处理，然后用于 `向群组发送紧急工单信息` 节点的飞书群消息。

## 原 Prompt 备注

当前 Prompt 中存在几处约束冲突，但本文按实际工作流原样保留：

- 要求提供“与客户沟通的关键话术”，同时又要求“不要话术”。
- 要求按 1—4 项提供内容，同时又要求“不要分步骤”。
- 要求使用清晰的 Markdown 格式，同时要求“用纯文字”。
