# 🧪 测试与评测

项目提供两层测试体系：

| 层级 | 工具 | 用途 |
|------|------|------|
| **冒烟测试** | `run-tests.sh` + `case-*.json` | 快速验证 Webhook 通不通 |
| **自动化评测** | `evaluate.py` + `suite-evaluation.json` | 量化 AI 准确率 + 回复质量 |

## 使用方式

### 方式 1：一键批量测试 (Bash)

```bash
# 设置你的 Webhook URL
export N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/你的webhookID
export N8N_AUTH_HEADER=你的认证头

# 运行所有测试
bash tests/run-tests.sh
```

### 方式 2：单个测试 (curl)

```bash
# 测试紧急工单
curl -X POST http://localhost:5678/webhook-test/你的webhookID \
  -H "Content-Type: application/json" \
  -H "Authorization: 你的认证头" \
  -d @tests/case-urgent.json

# 测试自动回复
curl -X POST http://localhost:5678/webhook-test/你的webhookID \
  -H "Content-Type: application/json" \
  -H "Authorization: 你的认证头" \
  -d @tests/case-auto-reply.json
```

### 方式 3：导入 Apifox (原有方式)

仍可使用 `tests/n8n测试.apifox.json` 导入 Apifox 进行可视化测试。

---

## 📊 自动化评测 (LLM-as-Judge)

### 前置准备

```bash
# 1. 复制评测配置并填入真实凭证
cp scripts/evaluate-config.json scripts/evaluate-config.local.json
# 编辑 evaluate-config.local.json，填入 n8n API Key 和 LLM Judge Key
```

### 运行评测

```bash
python scripts/evaluate.py
```

### 评测流程

```
评测数据集 (suite-evaluation.json)
  24条标注工单 × 标准答案
        │
        ▼
  POST → n8n Webhook → 触发工作流
        │
        ▼
  轮询 n8n API 拉取执行记录
        │
        ▼
  比对 AI 输出 vs 标注答案
  (sentiment/urgency/category/action)
        │
        ▼
  LLM Judge 对自动回复打分 (1-5)
        │
        ▼
  生成评测报告 (tests/reports/)
```

### 评测维度

| 维度 | 评估内容 | 量化方式 |
|------|---------|---------|
| 情感分类准确率 | sentiment 判定是否准确 | % |
| 紧急度分类准确率 | true_urgency 判定是否准确 | % |
| 问题分类准确率 | category 判定是否准确 | % |
| 决策路由准确率 | action_required 分支是否正确 | % |
| 自动回复质量 | 相关性/准确性/专业性/可操作性 | LLM Judge 1-5分 |

## 测试场景

| 文件 | 场景 | 预期行为 |
|------|------|----------|
| `case-urgent.json` | 紧急工单 - 支付问题 | → 紧急分支: 飞书群@所有人 + AI生成方案 |
| `case-normal.json` | 常规工单 - 技术问题 | → 常规分支: 等待2小时 + 群组通知 |
| `case-auto-reply.json` | 自动回复 - 普通咨询 | → 自动回复: 知识库检索 + 邮件回复 |
| `case-edge-empty.json` | 边界 - 空字段 | → 验证系统容错能力 |
| `case-edge-long-text.json` | 边界 - 超长文本 | → 验证系统对大数据量的处理 |
| `case-edge-emotional.json` | 边界 - 情绪激动 | → 应触发紧急处理流程 |
