#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1 LLM 任务：DeepSeek API 命令行调用测试。

用法：
    python w1_api_test.py
    python w1_api_test.py --prompt "解释一下最大回撤" --temp 0.1 --max_tokens 300
    python w1_api_test.py --top_p 0.8 --max_tokens 150

运行前：
    1. python -m pip install openai
    2. 复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY

安全约定：
    - API Key 只从环境变量读取，绝不写死在代码里。
    - .env 已被 .gitignore 忽略，不要提交到公开仓库。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    print("未安装 openai。请先运行：python -m pip install openai")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent


def load_dotenv(path: Path) -> None:
    """加载 .env 的最小实现：只支持 KEY=VALUE 与 # 注释。

    已存在的环境变量优先，不会被 .env 覆盖。
    生产项目建议改用 python-dotenv 或专门的密钥管理服务。
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def build_client() -> OpenAI:
    """从环境变量构造 DeepSeek 的 OpenAI 兼容客户端。"""
    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("未找到 DEEPSEEK_API_KEY。")
        print("请在当前目录创建 .env（可从 .env.example 复制），内容示例：")
        print("  DEEPSEEK_API_KEY=sk-你的密钥")
        print("或临时设置环境变量（PowerShell）：")
        print("  $env:DEEPSEEK_API_KEY='sk-你的密钥'")
        raise SystemExit(1)

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    return OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)


def ask(
    prompt: str,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 200,
    client: OpenAI | None = None,
) -> tuple[str, Any]:
    """调用 deepseek-chat，返回（回复文本，token 用量对象）。

    client 参数主要用于测试注入；不传时自动从环境变量构造。
    """
    client = client or build_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个严谨、简洁的助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    content = (response.choices[0].message.content or "").strip()
    return content, response.usage


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="调用 DeepSeek API 的最小命令行工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prompt",
        default="什么是夏普比率",
        help="要发送给模型的问题",
    )
    parser.add_argument(
        "--temp",
        type=float,
        default=0.3,
        help="temperature，0-2，越低越稳定",
    )
    parser.add_argument(
        "--top_p",
        type=float,
        default=0.9,
        help="top_p 核采样，0-1",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=200,
        help="最大生成 token 数",
    )
    args = parser.parse_args(argv)

    if not 0.0 <= args.temp <= 2.0:
        parser.error("--temp 必须在 0 到 2 之间")
    if not 0.0 <= args.top_p <= 1.0:
        parser.error("--top_p 必须在 0 到 1 之间")
    if args.max_tokens <= 0:
        parser.error("--max_tokens 必须大于 0")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    print("请求参数（不含 API Key）：")
    print("  model       = deepseek-chat")
    print(f"  prompt      = {args.prompt}")
    print(f"  temperature = {args.temp}")
    print(f"  top_p       = {args.top_p}")
    print(f"  max_tokens  = {args.max_tokens}")
    print("-" * 48)

    try:
        content, usage = ask(
            prompt=args.prompt,
            temperature=args.temp,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
        )
    except Exception as exc:
        print(f"API 调用失败：{exc}")
        print("排查顺序：API Key 是否正确 → 网络/代理 → base_url → 账户余额。")
        sys.exit(1)

    print("模型回复：")
    print(content)
    print("-" * 48)

    if usage:
        print(
            "token 用量："
            f"prompt={usage.prompt_tokens}, "
            f"completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}"
        )
    else:
        print("token 用量：接口未返回")


if __name__ == "__main__":
    main()
