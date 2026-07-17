"""stock_api 集成测试

验证:
  1. stock_api 从 render 模块导入而非 analyze 模块
  2. render_markdown 可从 stock_agent.render 独立导入
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_stock_api_uses_render_module():
    """stock_api._run_analysis 从 stock_agent.render 导入 render_markdown"""
    stock_api_path = BACKEND_DIR / "routers" / "stock_api.py"
    content = stock_api_path.read_text(encoding="utf-8")

    # 应该从独立的 render 模块导入
    assert "from stock_agent.render import render_markdown" in content or \
           "from stock_agent.render" in content, \
           "stock_api.py 应从 stock_agent.render 导入 render_markdown"

    print("[OK] stock_api 从 render 模块导入")


def test_render_markdown_import_path():
    """render_markdown 应从 stock_agent.render 导入（已独立）"""
    # 验证 render 模块可独立导入
    from stock_agent.render import render_markdown
    assert callable(render_markdown)
    print("[OK] render_markdown 可从 stock_agent.render 导入")


if __name__ == "__main__":
    print("=" * 50)
    print("stock_api 集成测试")
    print("=" * 50)

    test_stock_api_uses_render_module()
    test_render_markdown_import_path()
