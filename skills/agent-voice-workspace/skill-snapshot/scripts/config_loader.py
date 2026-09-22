#!/usr/bin/env python3
"""config_loader.py — ttsd 配置解析：内置 config.toml 为基底 + 用户配置逐键合并。

优先级：~/.config/agent-voice/config.toml 中出现的每个键覆盖内置
scripts/config.toml 的同名键；未覆盖的键沿用内置值（dict 递归下钻合并，
标量/列表整体替换）。用户配置只需写想改的键，不必是完整副本。

仅依赖标准库，供 ttsd.py 与验证脚本共用。
"""
from __future__ import annotations

import pathlib
import tomllib

SKILL_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
USER_CONFIG_DIR = pathlib.Path.home() / ".config" / "agent-voice"


def deep_merge(base: dict, override: dict) -> dict:
    """递归合并：override 的键覆盖 base；双方同为 dict 时逐键下钻，
    标量/列表整体替换。返回新 dict，不修改任何入参。"""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(base_path=None, user_path=None):
    """加载内置配置；用户配置存在时逐键合并（用户优先）。

    返回 (cfg, cfg_path)。cfg_path 指向参与合并的用户配置文件；
    无用户配置时回退为基底文件路径。
    """
    base_path = pathlib.Path(base_path or SKILL_SCRIPTS_DIR / "config.toml")
    user_path = pathlib.Path(user_path or USER_CONFIG_DIR / "config.toml")
    cfg = tomllib.loads(base_path.read_text(encoding="utf-8"))
    if user_path.exists():
        user = tomllib.loads(user_path.read_text(encoding="utf-8"))
        return deep_merge(cfg, user), user_path
    return cfg, base_path
