"""股票 Agent API TDD 测试

TDD RED → GREEN → REFACTOR
批次 1：先写测试（红灯），再写实现（绿灯）

测试覆盖：
  模型层：表创建、CRUD、去重
  API 层：analyze 异步、报告分页、自选股 CRUD、大盘触发
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


import pytest


@pytest.fixture(autouse=True)
def _no_capture(capfd):
    """禁用 stdout/stderr 捕获（fastapi TestClient + httpx 后台线程兼容）

    TestClient 的 lifespan 会启动后台线程（如 ai_news 调度器），这些线程
    在 pytest 关闭捕获后仍写 stdout，触发 "I/O operation on closed file"。
    本文件是唯一使用 TestClient 的测试，因此仅在此处禁用捕获；
    capfd 与该文件内测试的 capsys 不冲突（无测试同时用两者）。
    """
    with capfd.disabled():
        yield


# ═══════════════════════════════════════════════
# 模型层测试
# ═══════════════════════════════════════════════

def test_stock_report_table_exists():
    """stock_reports 表应在 init_db() 后存在"""
    from database import engine
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "stock_reports" in tables, f"stock_reports 表应存在，现有表：{tables}"


def test_stock_watchlist_table_exists():
    """stock_watchlist 表应在 init_db() 后存在"""
    from database import engine
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "stock_watchlist" in tables, f"stock_watchlist 表应存在，现有表：{tables}"


def test_save_and_get_report():
    """保存一份报告，用 ID 查回，字段应一致"""
    from database import save_stock_report, get_stock_report_by_id, delete_stock_report

    report_data = {"score": 72, "decision": "看多", "summary": "测试摘要"}
    markdown = "# 测试报告\n这是一份测试报告。"
    report_id = save_stock_report(
        stock_code="600398",
        stock_name="海澜之家",
        report=report_data,
        markdown=markdown,
        token_used=1234,
    )
    assert report_id is not None, "save_stock_report 应返回有效 ID"
    assert isinstance(report_id, int), f"ID 应为 int，实际 {type(report_id)}"

    row = get_stock_report_by_id(report_id)
    assert row is not None, f"应能查到 id={report_id} 的报告"
    assert row["stock_code"] == "600398"
    assert row["stock_name"] == "海澜之家"
    assert row["score"] == 72
    assert row["decision"] == "看多"
    assert row["token_used"] == 1234
    # report_json 中存储的是 JSON 字符串
    import json
    stored_report = json.loads(row["report_json"]) if isinstance(row["report_json"], str) else row["report_json"]
    assert stored_report["score"] == 72
    print(f"[OK] save & get report — id={report_id}")

    # 清理
    delete_stock_report("600398", "海澜之家")


def test_get_latest_report():
    """同一股票插入两份报告，get_latest_report 应返回最新的"""
    from database import save_stock_report, get_latest_report, delete_stock_report

    id1 = save_stock_report("000001", "平安银行", {"score": 50}, "# 旧报告", 100)
    id2 = save_stock_report("000001", "平安银行", {"score": 80}, "# 新报告", 200)

    latest = get_latest_report("000001")
    assert latest is not None, "应查到最新报告"
    assert latest["id"] == id2, f"最新报告 id 应为 {id2}，实际 {latest.get('id')}"
    print(f"[OK] get_latest_report — 旧={id1} 新={id2}")

    # 清理
    delete_stock_report("000001", "平安银行")


def test_get_reports_pagination():
    """报告列表应支持分页"""
    from database import save_stock_report, get_stock_reports, delete_stock_report

    # 插入 3 条测试数据
    for i in range(3):
        save_stock_report(
            f"00000{i}", f"测试股{i}", {"score": i * 10}, f"# 报告{i}", i * 50
        )

    rows, total = get_stock_reports(page=1, page_size=2)
    assert len(rows) <= 2, f"page_size=2 最多返回 2 条，实际 {len(rows)}"
    assert total >= 3, f"total 应 >= 3，实际 {total}"
    print(f"[OK] reports pagination — page1: {len(rows)}/{total}")

    # 清理
    for i in range(3):
        delete_stock_report(f"00000{i}", f"测试股{i}")


def test_add_and_list_watchlist():
    """添加自选股后应能在列表中查到"""
    from database import add_watchlist, get_watchlist, delete_watchlist

    # 先清理可能残留的数据
    for code in ["600519", "000858"]:
        try:
            delete_watchlist(code)
        except Exception:
            pass

    ok = add_watchlist("600519", "贵州茅台", "白酒龙头")
    assert ok is True, "添加应成功"

    ok2 = add_watchlist("000858", "五粮液", "")
    assert ok2 is True, "添加第二只也应成功"

    items = get_watchlist()
    codes = [item["stock_code"] for item in items]
    assert "600519" in codes, "列表中应包含 600519"
    assert "000858" in codes, "列表中应包含 000858"
    print(f"[OK] add & list watchlist — {len(items)} 只")

    # 清理测试数据
    delete_watchlist("600519")
    delete_watchlist("000858")


def test_delete_watchlist():
    """删除自选股后列表不应再包含该股"""
    from database import add_watchlist, delete_watchlist, get_watchlist

    add_watchlist("300750", "宁德时代", "")
    ok = delete_watchlist("300750")
    assert ok is True, "删除应成功"

    items = get_watchlist()
    codes = [item["stock_code"] for item in items]
    assert "300750" not in codes, "列表中不应再包含 300750"
    print("[OK] delete watchlist")


def test_update_watchlist():
    """更新自选股备注后应能读到新值"""
    from database import add_watchlist, update_watchlist, get_watchlist, delete_watchlist

    add_watchlist("601318", "中国平安", "初始备注")
    ok = update_watchlist("601318", {"notes": "更新后的备注", "enabled": 0})
    assert ok is True, "更新应成功"

    items = get_watchlist()
    target = next((item for item in items if item["stock_code"] == "601318"), None)
    assert target is not None, "应能找到 601318"
    assert target["notes"] == "更新后的备注", f"备注应为 '更新后的备注'，实际 '{target['notes']}'"
    assert target["enabled"] == 0, f"enabled 应为 0，实际 {target['enabled']}"
    print("[OK] update watchlist")

    # 清理测试数据
    delete_watchlist("601318")


def test_duplicate_watchlist_rejected():
    """重复添加同一股票应返回 False"""
    from database import add_watchlist, delete_watchlist

    add_watchlist("600036", "招商银行", "")
    ok = add_watchlist("600036", "招商银行", "重复")
    assert ok is False, "重复添加应返回 False"

    # 清理
    delete_watchlist("600036")
    print("[OK] duplicate watchlist rejected")


# ═══════════════════════════════════════════════
# API 端点测试
# ═══════════════════════════════════════════════

def test_analyze_endpoint_returns_task_id():
    """POST /api/stock/analyze 应返回 task_id（不阻塞等待 LLM）"""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from main import app

    # 关键：patch _run_analysis，避免后台线程真实执行 SKILL 取数 + DeepSeek 分析
    # （否则测试结束 pytest 关闭捕获，后台线程写 stderr 触发 tempfile 错误，且污染测试库）
    with patch("routers.stock_api._run_analysis"):
        client = TestClient(app)
        resp = client.post("/api/stock/analyze", json={"stock_code": "600398"})
    assert resp.status_code == 200, f"HTTP 状态码应为 200，实际 {resp.status_code}"
    data = resp.json()
    assert data["code"] == 0, f"code 应为 0，实际 {data}"
    assert "task_id" in data, "响应中应包含 task_id"
    assert len(data["task_id"]) == 8, f"task_id 长度应为 8，实际 {len(data['task_id'])}"
    print(f"[OK] analyze 返回 task_id: {data['task_id']}")


def test_analyze_result_not_found():
    """查询不存在的 task_id 应返回 code=1"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.get("/api/stock/analyze/result/nonexist")
    data = resp.json()
    assert data["code"] == 1, f"不存在的 task 应返回 code=1，实际 {data}"
    print("[OK] analyze result not found → code=1")


def test_reports_list_pagination():
    """GET /api/stock/reports 应返回分页结构"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.get("/api/stock/reports?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"code 应为 0，实际 {data}"
    assert "items" in data["data"], "data 中应包含 items"
    assert "total" in data["data"], "data 中应包含 total"
    assert isinstance(data["data"]["items"], list), "items 应为列表"
    assert isinstance(data["data"]["total"], int), "total 应为整数"
    print(f"[OK] reports list — {data['data']['total']} 条")


def test_reports_detail_not_found():
    """GET /api/stock/reports/99999 应返回 code=1"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.get("/api/stock/reports/99999")
    data = resp.json()
    assert data["code"] == 1, f"不存在的报告应返回 code=1，实际 {data}"
    print("[OK] report detail not found → code=1")


def test_watchlist_crud_flow():
    """自选股完整 CRUD 流程：添加 → 列表 → 更新 → 删除 → 确认消失"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # 1. 添加
    resp = client.post("/api/stock/watchlist", json={
        "stock_code": "000001",
        "stock_name": "平安银行",
        "notes": "测试",
    })
    assert resp.json()["code"] == 0, f"添加应成功: {resp.json()}"

    # 2. 列表包含
    resp = client.get("/api/stock/watchlist")
    assert resp.json()["code"] == 0
    items = resp.json()["data"]
    assert any(item["stock_code"] == "000001" for item in items), "列表中应包含 000001"

    # 3. 更新
    resp = client.put("/api/stock/watchlist/000001", json={"notes": "已更新"})
    assert resp.json()["code"] == 0, f"更新应成功: {resp.json()}"

    # 4. 验证更新
    resp = client.get("/api/stock/watchlist")
    items = resp.json()["data"]
    target = next(item for item in items if item["stock_code"] == "000001")
    assert target["notes"] == "已更新"

    # 5. 删除
    resp = client.delete("/api/stock/watchlist/000001")
    assert resp.json()["code"] == 0, f"删除应成功: {resp.json()}"

    # 6. 确认消失
    resp = client.get("/api/stock/watchlist")
    items = resp.json()["data"]
    assert not any(item["stock_code"] == "000001" for item in items), "列表中不应再包含 000001"

    print("[OK] watchlist CRUD full flow")


def test_market_report_trigger_returns_task_id():
    """POST /api/stock/trigger/market-report 应返回 task_id"""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from main import app

    # patch 后台分析，避免真实执行自选股分析（网络请求 + LLM）
    with patch("routers.stock_api._run_watchlist_analyze"):
        client = TestClient(app)
        resp = client.post("/api/stock/trigger/market-report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"code 应为 0，实际 {data}"
    assert "task_id" in data, "响应中应包含 task_id"
    print(f"[OK] market report trigger — task_id: {data.get('task_id')}")


# ═══════════════════════════════════════════════
# Slice 1: 推送报告到飞书
# ═══════════════════════════════════════════════

def test_push_report_endpoint_accepts_valid_id():
    """POST /api/stock/reports/{id}/push 应对有效 ID 返回合理响应"""
    from unittest.mock import patch
    from database import save_stock_report
    from fastapi.testclient import TestClient
    from main import app

    report_id = save_stock_report("600398", "海澜之家", {"score": 72}, "# 测试推送报告", 100)

    # patch 飞书推送，避免真实网络请求
    with patch("stock_agent.analyze.push_to_feishu", return_value=True):
        client = TestClient(app)
        resp = client.post(f"/api/stock/reports/{report_id}/push")
    assert resp.status_code == 200, f"HTTP 应为 200，实际 {resp.status_code}"
    data = resp.json()
    assert "code" in data, "响应应包含 code"
    assert "message" in data, "响应应包含 message"
    print(f"[OK] push report valid id={report_id} — code={data['code']}, msg={data['message']}")


def test_push_report_endpoint_rejects_invalid_id():
    """POST /api/stock/reports/99999/push 应对不存在的 ID 返回 code=1"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.post("/api/stock/reports/99999/push")
    data = resp.json()
    assert data["code"] == 1, f"不存在的报告应返回 code=1，实际 {data}"
    print(f"[OK] push report invalid id → code=1, msg={data['message']}")


# ═══════════════════════════════════════════════
# E1 v2：trend API 测试
# ═══════════════════════════════════════════════

def test_trend_api_returns_ascending_order():
    """GET /api/stock/reports/trend/{code} 应返回时间升序数据"""
    from fastapi.testclient import TestClient
    from main import app
    from database import save_stock_report, delete_stock_report

    TEST_CODE = "TEST_TREND"

    # 造两份报告：先存旧的、再存新的（id 递增，created_at 相近但不同）
    rid1 = save_stock_report(TEST_CODE, "测试趋势", {"score": 72}, "# 旧报告", 100)
    rid2 = save_stock_report(TEST_CODE, "测试趋势", {"score": 80}, "# 新报告", 120)

    client = TestClient(app)
    resp = client.get(f"/api/stock/reports/trend/{TEST_CODE}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    items = data["data"]
    assert isinstance(items, list)
    assert len(items) >= 2

    # 验证升序：时间戳应递增
    timestamps = [item["created_at"] for item in items]
    assert timestamps == sorted(timestamps), f"trend 应返回升序，实际: {timestamps}"

    # 验证 score 字段存在
    for item in items:
        assert "score" in item
        assert isinstance(item["score"], (int, float))

    # 清理：按 stock_code 删除
    delete_stock_report(TEST_CODE)
    print("[OK] trend API：升序 + 字段正确")


def test_trend_api_skips_invalid_scores():
    """trend API 应跳过 score 为 None 或非数值的行"""
    from fastapi.testclient import TestClient
    from main import app
    from database import SessionLocal, delete_stock_report
    from models import StockReport

    TEST_CODE = "SKIP_NONE"

    # 先建一条正常报告，确保有数据供趋势查询
    from database import save_stock_report
    save_stock_report(TEST_CODE, "测试跳过", {"score": 60}, "# 正常", 100)

    # 直接通过 ORM 插入一条 score=None 的记录
    db = SessionLocal()
    try:
        r = StockReport(stock_code=TEST_CODE, stock_name="测试跳过", report_json="{}", score=None)
        db.add(r)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get(f"/api/stock/reports/trend/{TEST_CODE}")
    assert resp.status_code == 200
    items = resp.json()["data"]
    # 不应包含 score=None 的记录
    scores = [item["score"] for item in items]
    assert None not in scores, f"trend 不应包含 score=None 的记录，实际 scores: {scores}"

    # 清理
    delete_stock_report(TEST_CODE)
    print("[OK] trend API：跳过无效 score")
    print("[OK] trend API：跳过无效 score")


def test_trend_api_empty_for_unknown_code():
    """未知股票代码应返回空 data 列表"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.get("/api/stock/reports/trend/UNKNOWN999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"] == []
    print("[OK] trend API：未知代码返回空列表")


# ============================================================
# 测试隔离性：验证测试不会残留数据到生产库
# ============================================================

def test_watchlist_tests_leave_no_residual():
    """所有自选股测试完成后，不应在库中残留测试数据"""
    from database import get_watchlist
    items = get_watchlist()
    polluted = [item["stock_code"] for item in items
                if item["stock_code"] in ("600519", "000858", "601318")]
    assert polluted == [], (
        f"测试残留数据: {polluted}，"
        "请检查 test_add_and_list_watchlist / test_update_watchlist 是否缺少清理"
    )
    print(f"[OK] 无测试残留 — watchlist 共 {len(items)} 条")


def test_reports_tests_leave_no_residual():
    """所有报告测试完成后，不应在库中残留测试数据"""
    from database import get_stock_reports
    rows, total = get_stock_reports(page=1, page_size=200)
    polluted = [r for r in rows
                if r["stock_code"].startswith("00000") or r["stock_name"].startswith("测试股")]
    assert polluted == [], (
        "测试残留报告: " + str([(r["stock_code"], r["stock_name"]) for r in polluted]) + ", "
        "请检查 test_save_and_get_report / test_get_latest_report / test_get_reports_pagination 是否缺少清理"
    )
    print(f"[OK] 无测试残留 — 总共 {total} 条报告")


# ═══════════════════════════════════════════════
# 运行入口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    passed = 0
    failed = 0
    tests = [
        # 模型层
        test_stock_report_table_exists,
        test_stock_watchlist_table_exists,
        test_save_and_get_report,
        test_get_latest_report,
        test_get_reports_pagination,
        test_add_and_list_watchlist,
        test_delete_watchlist,
        test_update_watchlist,
        test_duplicate_watchlist_rejected,
        # API 层
        test_analyze_endpoint_returns_task_id,
        test_analyze_result_not_found,
        test_reports_list_pagination,
        test_reports_detail_not_found,
        test_watchlist_crud_flow,
        test_market_report_trigger_returns_task_id,
        # Slice 1: 推送飞书
        test_push_report_endpoint_accepts_valid_id,
        test_push_report_endpoint_rejects_invalid_id,
        # E1 v2: trend API
        test_trend_api_returns_ascending_order,
        test_trend_api_skips_invalid_scores,
        test_trend_api_empty_for_unknown_code,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test_fn.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    print(f"{'='*50}")
