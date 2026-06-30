#!/bin/bash
# =============================================
# n8n AI Ticket System — 批量测试脚本
# 发送所有测试用例到 n8n Webhook
# =============================================

set -e

# 配置 —— 修改为你的 n8n Webhook 地址和认证头
WEBHOOK_URL="${N8N_WEBHOOK_URL:-http://localhost:5678/webhook-test/{{YOUR_WEBHOOK_ID}}}"
AUTH_HEADER="${N8N_AUTH_HEADER:-1234567890}"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

PASS=0
FAIL=0
TOTAL=0

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║     AI Ticket System — 批量测试运行器         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "Webhook: ${YELLOW}$WEBHOOK_URL${NC}"
echo ""

# 获取脚本所在目录
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for case_file in "$DIR"/case-*.json; do
    name=$(basename "$case_file" .json)
    TOTAL=$((TOTAL + 1))

    echo -e "${BOLD}[$TOTAL] 测试: ${name}${NC}"

    # 发送请求
    response=$(curl -s -o /tmp/n8n-test-resp.json -w "%{http_code}" \
        -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: $AUTH_HEADER" \
        -d @"$case_file" 2>/dev/null || true)

    http_code="$response"

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "  ${GREEN}✓ HTTP $http_code — 请求成功${NC}"
        # 如果有响应体，显示前200字符
        if [ -f /tmp/n8n-test-resp.json ]; then
            summary=$(head -c 200 /tmp/n8n-test-resp.json 2>/dev/null || echo "")
            [ -n "$summary" ] && echo -e "  ${CYAN}响应:${NC} $summary"
        fi
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗ HTTP $http_code — 请求失败${NC}"
        FAIL=$((FAIL + 1))
    fi
    echo ""
done

# 清理临时文件
rm -f /tmp/n8n-test-resp.json

# 汇总
echo -e "${BOLD}═══════════════════════════════════════════${NC}"
echo -e "  总计: ${TOTAL}  |  ${GREEN}通过: ${PASS}${NC}  |  ${RED}失败: ${FAIL}${NC}"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}✅ 全部通过!${NC}"
else
    echo -e "  ${RED}${BOLD}❌ 有 $FAIL 个测试失败，请检查配置${NC}"
fi
echo ""
