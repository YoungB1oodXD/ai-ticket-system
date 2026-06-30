# 🧪 测试用例

轻量级测试方案，替代 Apifox 手动测试。

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

仍可使用项目根目录的 `n8n测试.apifox.json` 导入 Apifox 进行可视化测试。

## 测试场景

| 文件 | 场景 | 预期行为 |
|------|------|----------|
| `case-urgent.json` | 紧急工单 - 支付问题 | → 紧急分支: 飞书群@所有人 + AI生成方案 |
| `case-normal.json` | 常规工单 - 技术问题 | → 常规分支: 等待2小时 + 群组通知 |
| `case-auto-reply.json` | 自动回复 - 普通咨询 | → 自动回复: 知识库检索 + 邮件回复 |
| `case-edge-empty.json` | 边界 - 空字段 | → 验证系统容错能力 |
| `case-edge-long-text.json` | 边界 - 超长文本 | → 验证系统对大数据量的处理 |
| `case-edge-emotional.json` | 边界 - 情绪激动 | → 应触发紧急处理流程 |
