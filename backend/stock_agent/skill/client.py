"""iFinD SKILL 调用封装

通过 sys.path 导入 ~/.claude/skills/ifind-finance-data/call.py
不复制文件，密钥配置由 call.py 自行读取同目录下的 mcp_config.json
"""
import sys
from pathlib import Path

# 历史遗留：call.py 曾用 verify=False 并在此压制 SSL 警告。
# 2026-07-29 已启用证书校验（verify=True），警告压制随之移除。

SKILL_DIR = str(Path("~/.claude/skills/ifind-finance-data").expanduser())
if SKILL_DIR not in sys.path:
    # NOTE: 导入期修改全局 sys.path 是加载用户级共享 skill 的既有机制，
    # 改 importlib 作用域加载牵动面大，暂保留（见实施计划"不修清单"第 3 条）
    sys.path.insert(0, SKILL_DIR)

from call import call as _call, list_tools as _list_tools  # noqa: E402


def call_skill(server_type: str, tool_name: str, params: dict) -> dict:
    """调用 iFinD SKILL 的 call 函数

    Args:
        server_type: stock | fund | edb | news | bond | global_stock | index
        tool_name: SKILL 工具名称，详见 references/ 下子服务文档
        params: 请求参数，自然语言工具用 {"query": "..."}，
                高频行情用 {"symbols": "...", "indicators": "...", "data_mode": "..."}

    Returns:
        {"ok": True/False, "status_code": int, "data": dict}
    """
    return _call(server_type, tool_name, params)


def list_skill_tools(server_type: str) -> dict:
    """获取某个服务当前可用的工具清单"""
    return _list_tools(server_type)
