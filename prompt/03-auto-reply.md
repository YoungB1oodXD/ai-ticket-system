# AI自动回复生成1

## 节点信息

- 节点名称：`AI自动回复生成1`
- 节点类型：`@n8n/n8n-nodes-langchain.agent`
- 连接模型：`OpenAI Chat Model3`
- 实际模型：`qwen-max`
- 使用分支：自动回复分支

## Prompt

```text
你是一个友好的客户支持代表。请为这个咨询问题生成温暖专业的回复。

客户信息：
姓名：{{ $('接收POST请求').item.json.body.customer_name }}
问题：{{ $('接收POST请求').item.json.body.issue_title }}
详细描述：{{ $('接收POST请求').item.json.body.issue_description }}

=== 知识库检索内容（必须优先使用）===
{{ $json.knowledge_context }}
=== 知识库内容结束 ===

回答要求：
1. **必须优先使用上方【知识库检索内容】中的信息**来解答客户问题
2. 如果知识库中有明确答案，给出具体步骤和解决方案
3. 如果知识库内容与问题不相关，诚实告知客户并说明会进一步核实
4. 语气友好专业，使用清晰的编号列表
5. 告知大致处理时间
6. 在结尾表达继续提供帮助的意愿

请直接生成 HTML 格式的回复内容，不要添加额外代码说明。
```

## 输入变量

| 变量 | 来源 | 用途 |
|------|------|------|
| `customer_name` | `接收POST请求` → `body` | 客户姓名 |
| `issue_title` | `接收POST请求` → `body` | 咨询问题标题 |
| `issue_description` | `接收POST请求` → `body` | 咨询问题详细描述 |
| `knowledge_context` | `预处理知识库数据` | RagFlow 知识库检索结果 |

## 输出用途

输出会传递给 `自动给客户发送邮件` 节点，作为发送给客户的 HTML 邮件正文。
