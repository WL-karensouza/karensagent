"""iFinD SKILL 调用封装

client.py 负责调用，extract.py 负责响应解析；本文件对外 re-export 保持
`from stock_agent.skill import call_skill, extract_text, extract_raw` 不变。
"""
from .client import call_skill, list_skill_tools  # noqa: F401
from .extract import extract_text, extract_raw  # noqa: F401

__all__ = ["call_skill", "list_skill_tools", "extract_text", "extract_raw"]
