#!/usr/bin/env python3
import argparse
import json
import sys
import uuid
from typing import Any, Dict, Optional

import requests
import sseclient
from urllib.parse import urlencode


def load_config_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_config_arg(config_json: str) -> Dict[str, Any]:
    try:
        return json.loads(config_json)
    except json.JSONDecodeError as e:
        raise SystemExit(f"--config JSON 解析失败: {e}")


def build_default_config(
    collection_name: str,
    mode: str,
    topk_single: int,
    topk_multi: int,
    temperature: float,
    max_tokens: int,
    system_prompt: Optional[str],
) -> Dict[str, Any]:
    default_prompt = (
        "你是数据获取与分析助手。"
        "你可以使用 retrieve 工具从知识库检索南美白对虾养殖的专业知识，"
        "你也可以使用list_sql_tables，get_tables_schema对于数据库的表进行了解，"
        "然后再调用执行查询命令的工具read_sql_query。最后根据检索到的真实数据来回答用户的问题。"
        "不要直接使用你自己的知识回答，必须基于知识库返回的专业知识和数据。回答中请明确引用来源（文件名/表名），并避免臆断。"
    )
    return {
        "rag": {
            "collection_name": collection_name,
            "topk_single": topk_single,
            "topk_multi": topk_multi,
        },
        "mode": mode,
        "single": {
            "temperature": temperature,
            "system_prompt": system_prompt or default_prompt,
            "max_tokens": max_tokens,
        },
    }


def stream_qa(
    base_url: str,
    session_id: str,
    agent_type: str,
    query: str,
    config: Dict[str, Any],
    timeout: Optional[float] = None,
) -> int:
    url = f"{base_url.rstrip('/')}/sse/stream_qa"
    params = {
        "session_id": session_id,
        "agent_type": agent_type,
        "query": query,
        "config": json.dumps(config, ensure_ascii=False),
    }
    url = f"{url}?{urlencode(params)}"

    # 仅打印发送与最终回答
    print(f"已经发送问题：{query}")

    try:
        response = requests.get(url, stream=True, timeout=timeout)
        client = sseclient.SSEClient(response)
        answer_text = ""
        for event in client.events():

            try:
                data = json.loads(event.data)
            except json.JSONDecodeError:
                continue

            # 正常答案增量在 data.data.answer 中（如果有）
            status = None
            if isinstance(data, dict):
                inner = data.get("data")
                if isinstance(inner, dict):
                    status = inner.get("status")
                    if inner.get("answer"):
                        answer_text += inner.get("answer", "")

            if status == "completed":
                print(f"回答：{answer_text}")
                return 0

            if "error" in data:
                err = data.get("error", "未知错误")
                print(f"回答：{err}")
                return 2

    except requests.exceptions.ConnectionError as e:
        print(f"回答：连接失败: {e}")
        return 3
    except requests.exceptions.ReadTimeout:
        print("回答：请求超时（读取 SSE 超时）")
        return 4
    except Exception as e:
        print(f"回答：SSE连接出错: {e}")
        return 5

    # 未显式完成，但自然结束
    print(f"回答：{''}")
    return 0


def interactive_loop(
    base_url: str,
    session_id: str,
    agent_type: str,
    config: Dict[str, Any],
    timeout: Optional[float],
) -> int:
    print("您好，我是南美白对虾问答助手，输入问题后回车发送，输入 /exit 退出。")
    print(f"会话ID: {session_id}")
    last_exit_code = 0
    while True:
        try:
            user_input = input("问题> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出")
            return 0

        if not user_input:
            continue
        if user_input in {"/exit", "exit", "quit", ":q"}:
            break

        # 为避免后端对已完成会话的拒绝，这里为每个问题生成新的会话ID
        new_session_id = str(uuid.uuid4())
        exit_code = stream_qa(
            base_url=base_url,
            session_id=new_session_id,
            agent_type=agent_type,
            query=user_input,
            config=config,
            timeout=timeout,
        )
        last_exit_code = exit_code

    return last_exit_code


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="命令行交互发送问题并通过 SSE 接收答案的客户端"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:5001",
        help="后端服务基础地址（默认: http://127.0.0.1:5001）",
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        default="japan",
        help="agent 类型（默认: japan）",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="自定义会话ID（默认: 自动生成UUID）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="请求超时时间（秒），SSE连接读取超时可选",
    )

    # 配置相关（三选一优先级：--config-file > --config > 默认参数）
    parser.add_argument(
        "--config-file",
        type=str,
        help="从 JSON 文件加载完整 config",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="直接传入 JSON 字符串作为 config",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="japan_shrimp",
        help="向量库集合名（默认: japan_shrimp）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="single",
        choices=["single", "multi"],
        help="工作模式（默认: single）",
    )
    parser.add_argument(
        "--topk-single",
        type=int,
        default=5,
        help="单轮检索 topk（默认: 5）",
    )
    parser.add_argument(
        "--topk-multi",
        type=int,
        default=5,
        help="多轮检索 topk（默认: 5）",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="采样温度（默认: 0.4）",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=10000,
        help="最大 tokens（默认: 10000）",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="覆盖默认 system prompt（可选）",
    )

    args = parser.parse_args(argv)

    session_id = args.session_id or str(uuid.uuid4())

    if args.config_file:
        config = load_config_from_file(args.config_file)
    elif args.config:
        config = parse_config_arg(args.config)
    else:
        config = build_default_config(
            collection_name=args.collection_name,
            mode=args.mode,
            topk_single=args.topk_single,
            topk_multi=args.topk_multi,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            system_prompt=args.system_prompt,
        )

    return interactive_loop(
        base_url=args.base_url,
        session_id=session_id,
        agent_type=args.agent_type,
        config=config,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())