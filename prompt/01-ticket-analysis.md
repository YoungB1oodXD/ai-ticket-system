# AI工单情况及用户情感分析

## 节点信息

- 节点名称：`AI工单情况及用户情感分析`
- 节点类型：`@n8n/n8n-nodes-langchain.agent`
- 连接模型：`OpenAI Chat Model`
- 实际模型：`qwen-max`
- 输出解析器：`结构化输出`

## Prompt

```text
你是一个客户支持工单分析系统。分析以下工单并返回 JSON：

工单标题：{{ $('接收POST请求').item.json.body.issue_title }}
工单描述：{{ $('接收POST请求').item.json.body.issue_description }}
客户信息：{{ $('接收POST请求').item.json.body.customer_name }}

输出要求（必须遵守）：
1. 只返回 JSON，不要任何其他文字
2. 必须包含以下 6 个字段，缺一不可
3. 布尔值写 true 或 false，不要写 "true" 或 "false"

输出格式：
{
  "sentiment": "positive 或 neutral 或 negative 或 angry",
  "true_urgency": "critical 或 high 或 medium 或 low",
  "category": "billing 或 technical 或 bug 或 general",
  "summary": "一句话总结",
  "requires_immediate_human_intervention": true 或 false,
  "can_be_auto_replied": true 或 false
}

判断规则：
- can_be_auto_replied = true：询问操作方法、步骤、价格、功能等ai可以自动回复的常规问题
- can_be_auto_replied = false：账户异常、支付失败、数据丢失、投诉、退款、情绪愤怒
```

## 结构化输出约束

该 Agent 连接的 `结构化输出` 节点使用以下 JSON Schema 示例：

```json
{
  "sentiment": "angry",
  "true_urgency": "critical",
  "category": "billing",
  "summary": "客户支付成功但订单状态未更新，导致重复付款",
  "requires_immediate_human_intervention": true,
  "can_be_auto_replied": true
}
```

## 输入变量

| 变量 | 来源 | 用途 |
|------|------|------|
| `issue_title` | `接收POST请求` → `body` | 工单标题 |
| `issue_description` | `接收POST请求` → `body` | 工单详细描述 |
| `customer_name` | `接收POST请求` → `body` | 客户信息 |

## 输出用途

输出会传递给 `综合决策处理` 节点，用于判断工单进入紧急处理、常规处理还是自动回复分支。
