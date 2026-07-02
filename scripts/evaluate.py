#!/usr/bin/env python3
"""
n8n AI Ticket System — 自动化评测脚本 (LLM-as-Judge)

用法:
    1. 复制 evaluate-config.json → evaluate-config.local.json，填入真实凭证
    2. python scripts/evaluate.py

流程:
    POST /webhook → 触发工作流 → 轮询 n8n API 获取执行数据 → 比对标注答案 → LLM Judge 打分 → 生成报告
"""

import json
import os
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ─── 路径 ─────────────────────────────────────────────────────
PROJ_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJ_ROOT / "scripts" / "evaluate-config.local.json"
SUITE_PATH = PROJ_ROOT / "tests" / "suite-evaluation.json"
REPORT_DIR = PROJ_ROOT / "tests" / "reports"

# ─── 加载配置 ──────────────────────────────────────────────────
def load_config():
    # 优先加载 local 配置（含真实凭证）
    if not CONFIG_PATH.exists():
        # fallback 到模板配置
        fallback = CONFIG_PATH.with_name("evaluate-config.json")
        if fallback.exists():
            print(f"⚠  请复制 evaluate-config.json → evaluate-config.local.json 并填入真实凭证")
            print(f"   cp scripts/evaluate-config.json scripts/evaluate-config.local.json")
        else:
            print(f"✗ 找不到配置文件: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    # 校验必要字段
    required = ["n8n_url", "n8n_api_key", "webhook_path", "workflow_id"]
    missing = [k for k in required if not cfg.get(k) or "你的" in str(cfg.get(k))]
    if missing:
        print(f"✗ 配置缺少必要字段: {missing}")
        print(f"  请填写 {CONFIG_PATH}")
        sys.exit(1)

    return cfg


def load_suite(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"📋 加载评测数据集: {data['meta']['name']}")
    print(f"   用例数: {data['meta']['total_cases']}")
    return data["test_cases"]


# ─── n8n API ──────────────────────────────────────────────────
def n8n_headers(cfg):
    return {"X-N8N-API-KEY": cfg["n8n_api_key"]}


def trigger_webhook(cfg, payload):
    """发送工单到 n8n Webhook，返回是否成功"""
    url = f"{cfg['n8n_url'].rstrip('/')}/{cfg['webhook_path'].lstrip('/')}"
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code in (200, 201), resp
    except requests.RequestException as e:
        return False, str(e)


def poll_execution(cfg, since_ts, timeout=90):
    """
    轮询 n8n API 获取执行记录。
    返回完整 execution data，或 None（超时/失败）。
    """
    list_url = f"{cfg['n8n_url'].rstrip('/')}/rest/executions"
    headers = n8n_headers(cfg)
    params = {"workflowId": cfg["workflow_id"], "limit": 5}

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(list_url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                time.sleep(2)
                continue

            results = resp.json().get("data", {}).get("results", [])
            if not results:
                time.sleep(2)
                continue

            # 找到最近的一条执行
            latest = results[0]
            exec_id = latest["id"]
            status = latest.get("status", "")

            # 跳过还在 waiting 的（常规分支 2h 等待）
            # 但如果已经有部分节点完成，仍然可以拉取
            if status == "waiting":
                # 仍然拉取看是否有部分数据
                pass

            # 拉取完整数据
            exec_url = f"{cfg['n8n_url'].rstrip('/')}/rest/executions/{exec_id}?includeData=true"
            exec_resp = requests.get(exec_url, headers=headers, timeout=10)
            if exec_resp.status_code == 200:
                exec_data = exec_resp.json().get("data", {})
                return exec_data

        except requests.RequestException:
            pass
        time.sleep(2)

    return None


# ─── 节点数据提取 ──────────────────────────────────────────────
def extract_node_output(exec_data, node_name):
    """
    从 execution data 中提取指定节点的输出。

    n8n runData 结构:
      runData["节点名"][0]["data"]["main"][0][0]["json"]
    或者有 outputParser 时可能不同，尝试多种提取策略。
    """
    run_data = exec_data.get("data", {}).get("resultData", {}).get("runData", {})
    if node_name not in run_data:
        return None

    node_execs = run_data[node_name]
    if not node_execs:
        return None

    main_data = node_execs[0].get("data", {}).get("main", [[]])
    if not main_data or not main_data[0]:
        return None

    first_item = main_data[0][0]

    # 策略 1: 直接 json
    if "json" in first_item:
        return first_item["json"]

    # 策略 2: json 嵌套在 output 下 (结构化输出)
    if isinstance(first_item, dict):
        for key in ("output", "result", "data"):
            if key in first_item:
                val = first_item[key]
                if isinstance(val, dict):
                    return val

    return first_item


def extract_latest_exec_time(exec_data):
    """从 execution 数据中提取各节点的执行耗时"""
    run_data = exec_data.get("data", {}).get("resultData", {}).get("runData", {})
    timings = {}
    for node_name, execs in run_data.items():
        if execs and "executionTime" in execs[0]:
            timings[node_name] = round(execs[0]["executionTime"] * 1000)  # ms
    return timings


# ─── 评分函数 ──────────────────────────────────────────────────
def evaluate_classification(actual, expected):
    """比对 AI 分析的分类结果与标准答案"""
    result = {
        "sentiment": {"actual": actual.get("sentiment"), "expected": expected.get("sentiment"), "pass": False},
        "true_urgency": {"actual": actual.get("true_urgency"), "expected": expected.get("true_urgency"), "pass": False},
        "category": {"actual": actual.get("category"), "expected": expected.get("category"), "pass": False},
        "requires_intervention": {"actual": actual.get("requires_immediate_human_intervention"), "expected": expected.get("requires_immediate_human_intervention"), "pass": False},
        "can_be_auto_replied": {"actual": actual.get("can_be_auto_replied"), "expected": expected.get("can_be_auto_replied"), "pass": False},
    }

    for key in result:
        result[key]["pass"] = str(result[key]["actual"]).lower() == str(result[key]["expected"]).lower()

    return result


def evaluate_action(actual_action, expected_action):
    return {
        "actual": actual_action,
        "expected": expected_action,
        "pass": str(actual_action).lower() == str(expected_action).lower()
    }


def llm_judge_scoring(cfg, test_case, actual_reply):
    """使用 LLM Judge 对自动回复质量进行打分 (1-5)"""
    judge_cfg = cfg.get("llm_judge", {})
    if not judge_cfg.get("api_key") or "你的" in str(judge_cfg.get("api_key", "")):
        return {"error": "LLM Judge 未配置"}

    prompt = f"""你是一个专业的客服回复质量评估员。请评估以下 AI 自动生成的客服回复质量。

## 客户问题
标题: {test_case['input']['issue_title']}
描述: {test_case['input']['issue_description']}

## AI 生成的回复
{actual_reply[:2000]}

## 评分标准（1-5分）
请从以下 4 个维度分别打分，并给出总分（加权平均）：

1. **相关性** (1-5): 回复是否直接回答了客户的问题
2. **准确性** (1-5): 回复中的信息是否正确
3. **专业性** (1-5): 语气是否专业、友好、有礼貌
4. **可操作性** (1-5): 客户看完是否知道下一步该怎么做

## 输出格式
请只返回 JSON，不要其他文字：
{{
    "relevance": <1-5>,
    "accuracy": <1-5>,
    "professionalism": <1-5>,
    "actionability": <1-5>,
    "overall": <1-5>,
    "strengths": "<优点>",
    "weaknesses": "<缺点>"
}}"""

    try:
        resp = requests.post(
            judge_cfg["api_url"],
            headers={
                "Authorization": f"Bearer {judge_cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": judge_cfg.get("model", "qwen-max"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # 尝试解析 JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"error": f"Judge 返回非 JSON: {content[:200]}"}
        else:
            return {"error": f"Judge API 返回 {resp.status_code}"}
    except requests.RequestException as e:
        return {"error": str(e)}


def llm_summarize_report(cfg, report_data):
    """用 LLM 生成报告的总结段"""
    judge_cfg = cfg.get("llm_judge", {})
    if not judge_cfg.get("api_key") or "你的" in str(judge_cfg.get("api_key", "")):
        return "（LLM Judge 未配置，无法生成总结分析）"

    prompt = f"""你是 AI 工单系统的质量分析师。以下是刚刚完成的一次自动化评测结果，请写一段 200 字以内的总结分析。

评测结果：
- 情感分类准确率: {report_data['sentiment_accuracy']}%
- 紧急度分类准确率: {report_data['urgency_accuracy']}%
- 决策路由准确率: {report_data['action_accuracy']}%
- 自动回复平均质量分: {report_data['avg_reply_score']}
- 总评测用例数: {report_data['total']}
- 通过数: {report_data['passed']}
- 失败数: {report_data['failed']}

请分析：
1. 系统的整体表现如何
2. 哪个维度最强、哪个最弱
3. 给出一个改进建议"""

    try:
        resp = requests.post(
            judge_cfg["api_url"],
            headers={
                "Authorization": f"Bearer {judge_cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": judge_cfg.get("model", "qwen-max"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return "（无法生成总结分析）"


# ─── 报告生成 ──────────────────────────────────────────────────
def generate_report(results, cfg):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"evaluation-report-{timestamp}.md"

    # 统计
    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])
    failed = total - passed

    sentiment_accuracy = sum(1 for r in results if r["classification"]["sentiment"]["pass"]) / total * 100 if total else 0
    urgency_accuracy = sum(1 for r in results if r["classification"]["true_urgency"]["pass"]) / total * 100 if total else 0
    category_accuracy = sum(1 for r in results if r["classification"]["category"]["pass"]) / total * 100 if total else 0
    action_accuracy = sum(1 for r in results if r["action"]["pass"]) / total * 100 if total else 0

    reply_scores = [r["reply_score"].get("overall", 0) for r in results if r.get("reply_score") and isinstance(r.get("reply_score"), dict) and "overall" in r["reply_score"]]
    avg_reply_score = round(sum(reply_scores) / len(reply_scores), 2) if reply_scores else 0

    report_data = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "sentiment_accuracy": round(sentiment_accuracy, 1),
        "urgency_accuracy": round(urgency_accuracy, 1),
        "category_accuracy": round(category_accuracy, 1),
        "action_accuracy": round(action_accuracy, 1),
        "avg_reply_score": avg_reply_score,
    }

    summary = llm_summarize_report(cfg, report_data)

    lines = [
        f"# AI 工单分诊系统 — 评测报告",
        f"",
        f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**评测数据集**: suite-evaluation.json ({total} 用例)",
        f"",
        f"---",
        f"",
        f"## 📊 总览",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总用例 | {total} |",
        f"| ✅ 通过 | {passed} |",
        f"| ❌ 失败 | {failed} |",
        f"| 通过率 | {round(passed/total*100,1) if total else 0}% |",
        f"",
        f"## 🎯 各维度准确率",
        f"",
        f"| 维度 | 准确率 |",
        f"|------|--------|",
        f"| 情感分类 | {sentiment_accuracy:.1f}% |",
        f"| 紧急度分类 | {urgency_accuracy:.1f}% |",
        f"| 问题分类 | {category_accuracy:.1f}% |",
        f"| 决策路由 | {action_accuracy:.1f}% |",
        f"| 自动回复质量(平均分) | {avg_reply_score}/5 |",
        f"",
        f"## 📈 执行耗时",
        f"",
    ]

    # 收集节点耗时
    all_nodes = set()
    for r in results:
        if r.get("node_timings"):
            all_nodes.update(r["node_timings"].keys())

    lines.append(f"| 节点 | 平均耗时 |")
    lines.append(f"|------|---------|")
    for node in sorted(all_nodes):
        times = [r["node_timings"][node] for r in results if r.get("node_timings") and node in r["node_timings"]]
        if times:
            avg = sum(times) / len(times)
            lines.append(f"| {node} | {avg:.0f}ms |")

    lines.extend([
        f"",
        f"## 🔍 失败用例详情",
        f"",
    ])
    for r in results:
        if not r["overall_pass"]:
            lines.append(f"### ❌ {r['id']}: {r['description']}")
            lines.append(f"")
            lines.append(f"| 字段 | 实际值 | 期望值 | 结果 |")
            lines.append(f"|------|--------|--------|------|")
            for dim, detail in r["classification"].items():
                mark = "✅" if detail["pass"] else "❌"
                lines.append(f"| {dim} | {detail['actual']} | {detail['expected']} | {mark} |")
            lines.append(f"| action_required | {r['action']['actual']} | {r['action']['expected']} | {'✅' if r['action']['pass'] else '❌'} |")
            lines.append(f"")

    # 回复质量分布
    if reply_scores:
        lines.extend([
            f"## ⭐ 回复质量分布",
            f"",
            f"| 分数段 | 数量 |",
            f"|--------|------|",
        ])
        for score_range in ["5", "4-4.9", "3-3.9", "2-2.9", "1-1.9"]:
            if "-" in score_range:
                lo, hi = map(float, score_range.split("-"))
                count = sum(1 for s in reply_scores if lo <= s <= hi)
            else:
                count = sum(1 for s in reply_scores if s == 5)
            if count:
                lines.append(f"| {score_range} | {count} |")
        lines.append(f"")

    lines.extend([
        f"## 💡 AI 总结分析",
        f"",
        f"{summary}",
        f"",
        f"---",
        f"*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📄 报告已生成: {report_path}")
    return report_path


# ─── 主流程 ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  n8n AI Ticket System — 自动化评测")
    print("=" * 60)
    print()

    cfg = load_config()
    test_cases = load_suite(SUITE_PATH)
    print()

    results = []
    total = len(test_cases)

    for idx, tc in enumerate(test_cases, 1):
        tc_id = tc["id"]
        print(f"[{idx}/{total}] {tc_id}: {tc['description']}")

        # 1. 触发 Webhook
        ok, webhook_resp = trigger_webhook(cfg, tc["input"])
        if not ok:
            print(f"  ✗ Webhook 请求失败: {webhook_resp}")
            results.append({
                "id": tc_id,
                "description": tc["description"],
                "overall_pass": False,
                "error": f"Webhook failed: {webhook_resp}",
                "classification": {},
                "action": {},
                "reply_score": None,
                "node_timings": None,
                "latency_ms": 0,
            })
            continue

        start_time = time.time()

        # 2. 轮询获取执行记录
        exec_data = poll_execution(cfg, start_time, timeout=90)
        if not exec_data:
            print(f"  ⏱ 轮询超时（90s），跳过")
            results.append({
                "id": tc_id,
                "description": tc["description"],
                "overall_pass": False,
                "error": "Timeout polling execution",
                "classification": {},
                "action": {},
                "reply_score": None,
                "node_timings": None,
                "latency_ms": round((time.time() - start_time) * 1000),
            })
            continue

        latency_ms = round((time.time() - start_time) * 1000)

        # 3. 提取节点数据
        analysis_output = extract_node_output(exec_data, cfg["analysis_node_name"])
        decision_output = extract_node_output(exec_data, cfg["decision_node_name"])
        reply_output = extract_node_output(exec_data, cfg["reply_node_name"]) if tc["scenario"] in ("auto_reply",) else None
        node_timings = extract_latest_exec_time(exec_data)

        # 4. 处理 AI 分析输出
        # 结构化输出节点会用 output 包裹
        actual_analysis = analysis_output.get("output", analysis_output) if isinstance(analysis_output, dict) else {}
        # 综合决策节点直接输出
        actual_decision = decision_output if isinstance(decision_output, dict) else {}

        # 修正: 决策输出中的 action_required 字段名
        action_actual = actual_decision.get("action_required", "")

        # 5. 评估
        classification_result = evaluate_classification(actual_analysis, tc["expected"])
        action_result = evaluate_action(action_actual, tc["expected"].get("action_required", ""))

        # 6. LLM Judge 对自动回复打分
        reply_score = None
        if tc["scenario"] == "auto_reply" and reply_output:
            reply_text = json.dumps(reply_output, ensure_ascii=False)
            reply_score = llm_judge_scoring(cfg, tc, reply_text)

        # 7. 综合判定是否通过
        dims = list(classification_result.values())
        all_class_pass = all(d["pass"] for d in dims)
        overall_pass = all_class_pass and action_result["pass"]

        result = {
            "id": tc_id,
            "description": tc["description"],
            "scenario": tc["scenario"],
            "overall_pass": overall_pass,
            "classification": classification_result,
            "action": action_result,
            "reply_score": reply_score,
            "node_timings": node_timings,
            "latency_ms": latency_ms,
            "error": None,
        }
        results.append(result)

        # 打印简况
        status = "✅" if overall_pass else "❌"
        print(f"  {status} 耗时={latency_ms}ms", end="")
        if not overall_pass:
            fails = [k for k, v in classification_result.items() if not v["pass"]]
            if not action_result["pass"]:
                fails.append("action")
            print(f" 失败维度: {fails}", end="")
        print()

    # ─── 生成报告 ──────────────────────────────────────────
    print()
    report_path = generate_report(results, cfg)

    # 控制台摘要
    total = len(results)
    passed = sum(1 for r in results if r.get("overall_pass"))
    failed = total - passed
    print()
    print("=" * 60)
    print(f"  结果: ✅ {passed}/{total} 通过  ❌ {failed} 失败")
    print(f"  报告: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
