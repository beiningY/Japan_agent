from __future__ import annotations
import dotenv
dotenv.load_dotenv()
import json
import os
from typing import Any, Dict, List, Optional
import time
from ToolOrchestrator.core.config import settings
from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError
from ToolOrchestrator.core.registry import ToolRegistry
from utils.global_tool_manager import global_tool_manager
from .react_agent import ReActAgent
from .core_schema import AgentState, Message
from utils.logger import get_logger
logger = get_logger(__name__)

class ToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = type("Fn", (), {"name": name, "arguments": arguments})


class MCPToolCallAgent(ReActAgent):
    """使用 ReAct 架构 + OpenAI tools + MCP 网关，统一数据获取。

    - think(): 使用 Chat Completions 的 tools 模式，让 LLM 自动选择 MCP 工具
    - act(): 通过 ToolRegistry 调用 MCP 工具，写入 tool 消息
    """

    name: str = "mcp-toolcall-agent"
    description: Optional[str] = "Agent with MCP toolcalls"

    model: str = "gpt-5"
    max_retries: int = 3  # 最大重试次数（含首次共 1+max_retries 次尝试）
    request_timeout_seconds: float = 120.0  # 单次请求超时时间
    initial_retry_backoff_seconds: float = 0.8  # 指数退避初始等待
    max_tool_calls: int = 6  # 最大工具调用次数，避免过度检索
    info_sufficient_threshold: int = 3  # 判断信息充足的工具调用次数阈值
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GPT_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY/GPT_API_KEY 未配置")
        self._client = OpenAI(api_key=api_key)
        self._registry = None 
        self._tools_param_cache: Optional[List[Dict[str, Any]]] = None
        self.tool_calls: List[ToolCall] = []
        self._log = logger

    def _has_data_tool_result(self, content: str) -> bool:
        """检测是否是数据获取工具的结果"""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                # 检测各种类型的数据工具结果
                return ("chunks" in parsed or
                       "status" in parsed or
                       "result" in parsed or
                       "tables" in parsed or
                       "rows" in parsed)
        except:
            pass
        return False

    async def _ensure_tools_ready(self):
        if self._tools_param_cache is not None:
            return
            
        # 使用全局工具管理器获取已初始化的工具注册器
        if not global_tool_manager.is_initialized:
            self._log.warning("全局工具管理器未初始化，尝试后备初始化...")
            # 后备方案：如果全局工具管理器未初始化，使用原有方式
            self._registry = ToolRegistry(settings.MCP_CLIENT_CONFIG)
            await self._registry.initialize_connections()
            self._registry.load_from_json(settings.TOOLS_CONFIG_PATH)
        else:
            self._log.info("使用全局工具管理器的已初始化注册器")
            self._registry = global_tool_manager.registry

        if not self._registry or not self._registry._tools:
            self._log.error("无法获取工具注册器或工具列表为空")
            self._tools_param_cache = []
            return

        tools_param: List[Dict[str, Any]] = []
        for name, cfg in self._registry._tools.items():
            parameters = cfg.get("parameters")
            description = cfg.get("description", name)
            function_def: Dict[str, Any] = {
                "name": name,
                "description": description,
            }
            if parameters:
                function_def["parameters"] = parameters
            tools_param.append({"type": "function", "function": function_def})

        self._tools_param_cache = tools_param
        self._log.info(f"已准备 {len(tools_param)} 个工具供LLM调用")

    def _to_chat_messages(self) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = []
        for m in self.messages:
            if m.role == "tool":
                # 为满足 OpenAI 对 tool 消息的约束：必须紧随带有 tool_calls 的 assistant 消息之后
                # 若历史消息中没有保存带 tool_calls 的 assistant，则根据最近一次 self.tool_calls 构造一条虚拟的 assistant 消息
                need_insert_tool_calls = True
                if msgs:
                    last = msgs[-1]
                    if last.get("role") == "assistant" and last.get("tool_calls"):
                        need_insert_tool_calls = False

                if need_insert_tool_calls and self.tool_calls:
                    tool_calls_payload: List[Dict[str, Any]] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in self.tool_calls
                    ]
                    msgs.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_payload,
                    })

                msgs.append({
                    "role": "tool",
                    "content": m.content or "",
                    "tool_call_id": m.tool_call_id,
                })
            elif m.role == "assistant":
                # 保留 assistant 消息上的 tool_calls，确保后续 tool 消息的 tool_call_id 能被正确匹配
                payload: Dict[str, Any] = {"role": "assistant", "content": m.content or ""}
                if m.tool_calls:
                    payload["tool_calls"] = m.tool_calls
                msgs.append(payload)
            elif m.role in ("user", "system"):
                msgs.append({"role": m.role, "content": m.content or ""})
        return msgs

    async def think(self) -> bool:
        # 如果已经完成，不再思考
        if self.state == AgentState.FINISHED:
            return False
            
        # 检查是否已经进行了太多轮工具调用
        tool_call_count = len([m for m in self.messages if m.role == "tool"])

        # 检查是否已经有总结请求在最近的消息中
        recent_user_messages = [m for m in self.messages[-3:] if m.role == "user"]
        has_summary_request = any("请根据上述检索到的信息" in (m.content or "") for m in recent_user_messages)

        if tool_call_count >= self.max_tool_calls:  # 使用可配置的最大工具调用次数
            self._log.info(f"已达到最大工具调用次数({tool_call_count}/{self.max_tool_calls})，停止思考并生成最终回答")

            if has_summary_request:
                # 如果已经有总结请求，不再检查工具调用限制，直接让LLM处理
                self._log.info("已有总结请求，跳过工具调用限制检查，让LLM生成最终回答")
                # 不要设置FINISHED，让LLM先处理总结请求，生成回答后再设置FINISHED
                return True  # 让LLM处理总结请求
            elif any(self._has_data_tool_result(m.content or "") for m in self.messages[-3:] if m.role == "tool"):
                self._log.info("检测到数据获取工具调用，强制生成最终回答")
                self.memory.add(Message.user("请根据上述检索到的信息，用中文给出专业的最终回答。不要返回JSON格式，直接给出自然语言回答。"))
                return True
            else:
                self.state = AgentState.FINISHED
                return False
            
        if self.next_step_prompt:
            self.messages += [Message.user(self.next_step_prompt)]

        await self._ensure_tools_ready()

        # 构造对话
        chat_messages = self._to_chat_messages()
        if self.system_prompt and (not chat_messages or chat_messages[0].get("role") != "system"):
            chat_messages = [{"role": "system", "content": self.system_prompt}] + chat_messages

        # 让 LLM 决定是否要调用工具（带超时与指数退避重试）
        attempt_index: int = 0
        last_error: Optional[Exception] = None
        while attempt_index <= self.max_retries:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=chat_messages,
                    tools=self._tools_param_cache,  # type: ignore
                    tool_choice="auto",
                    timeout=self.request_timeout_seconds,
                )
                break
            except (APITimeoutError,) as e:
                last_error = e
                self._log.warning("OpenAI 请求超时，last_error: %s，第 %s 次尝试", last_error, attempt_index + 1)
            except (RateLimitError,) as e:
                last_error = e
                self._log.warning("OpenAI 触发限流，last_error: %s，第 %s 次尝试", last_error, attempt_index + 1)
            except (APIError,) as e:
                last_error = e
                # 对于可重试的 5xx 错误继续重试
                if getattr(e, "status_code", 500) >= 500:
                    self._log.warning("OpenAI 服务端错误(%s)，第 %s 次尝试", getattr(e, "status_code", None), attempt_index + 1)
                else:
                    # 4xx 多为不可恢复，直接终止重试
                    self._log.error("OpenAI API 错误：%s，停止重试", e)
                    raise
            except Exception as e:
                # 未知异常不重试，向上抛出
                self._log.error("调用 OpenAI 未知异常：%s", e)
                raise

            attempt_index += 1
            if attempt_index > self.max_retries:
                # 重试用尽，进行降级，并终止循环
                fallback = "抱歉，当前大模型接口暂时不可用，请稍后重试或缩小问题范围。"
                self.memory.add(Message.assistant(fallback))
                self.state = AgentState.FINISHED
                return False
            # 指数退避
            sleep_seconds = self.initial_retry_backoff_seconds * (2 ** (attempt_index - 1))
            time.sleep(sleep_seconds)

        choice = resp.choices[0]
        msg = choice.message

        content = msg.content or ""
        tool_calls = msg.tool_calls or []

        # 记录 assistant 输出
        if tool_calls:
            # 保存工具调用以便 act() 执行
            self.tool_calls = [
                ToolCall(tc.id, tc.function.name, tc.function.arguments or "{}")
                for tc in tool_calls
            ]
            # 将带工具调用的assistant消息写入记忆（包含 tool_calls，满足 OpenAI 约束）
            tool_calls_payload: List[Dict[str, Any]] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in self.tool_calls
            ]
            self.memory.add(Message(role="assistant", content=content or "[tools] executing", tool_calls=tool_calls_payload))
            return True
        else:
            # 没有工具调用
            if content:
                # 有明确回答内容，记忆并结束
                self.memory.add(Message.assistant(content))
                self.state = AgentState.FINISHED
                return False
            else:
                # 无内容且无工具调用，检查是否需要生成最终答案
                tool_call_count = len([m for m in self.messages if m.role == "tool"])

                # 检查是否刚完成了检索工具调用
                recent_tool_calls = [m for m in self.messages[-5:] if m.role == "tool"]
                has_recent_retrieve = any("chunks" in (m.content or "") for m in recent_tool_calls)

                if tool_call_count > 0 and has_recent_retrieve:
                    # 如果刚完成检索工具调用，强制生成基于检索结果的最终答案
                    self._log.info("检测到检索工具调用完成，强制生成基于检索内容的最终回答")

                    # 提取检索到的内容进行总结
                    retrieved_content = ""
                    try:
                        for m in reversed(self.messages):
                            if m.role == "tool" and "chunks" in (m.content or ""):
                                import json
                                tool_result = json.loads(m.content)
                                if "result" in tool_result and "chunks" in tool_result["result"]:
                                    chunks = tool_result["result"]["chunks"]
                                    retrieved_content = "\n".join([chunk.get("text", "") for chunk in chunks[:3]])  # 只取前3个chunk
                                    break
                    except Exception as e:
                        self._log.debug(f"提取检索内容时出错: {e}")

                    if retrieved_content:
                        summary_prompt = f"请根据以下检索到的信息回答用户的问题。请用中文给出专业、简洁的回答，不要返回JSON格式：\n\n{retrieved_content}"
                    else:
                        summary_prompt = "请根据上述检索到的信息，用中文给出专业的最终回答。不要返回JSON格式，直接给出自然语言回答。"

                    self.memory.add(Message.user(summary_prompt))
                    return True
                elif tool_call_count > 0:
                    # 其他工具调用情况
                    self._log.info("已进行工具调用但无明确答案，生成最终回答")
                    self.memory.add(Message.user("请根据上述信息，用中文给出专业的最终回答。不要返回JSON格式，直接给出自然语言回答。"))
                    return True
                else:
                    # 无内容且无工具调用，认为没有进一步动作，直接结束，避免死循环
                    self.state = AgentState.FINISHED
                    return False

    async def act(self) -> str:
        if not self.tool_calls:
            # 检查是否有最近的总结请求
            recent_user_messages = [m for m in self.messages[-3:] if m.role == "user"]
            has_summary_request = any("请根据上述检索到的信息" in (m.content or "") for m in recent_user_messages)


            if has_summary_request:
                # 如果有总结请求，调用LLM生成回答
                self._log.info("检测到总结请求，调用LLM生成最终回答")
                try:
                    # 构建精简的上下文，包含原始查询、检索结果摘要和总结请求
                    filtered_messages = []

                    # 1. 获取原始用户查询
                    user_messages = [m for m in self.messages if m.role == "user"]
                    original_query = user_messages[0] if user_messages else None

                    # 2. 获取最近的工具结果（知识库检索和数据库查询）
                    recent_tool_results = []
                    kb_results_found = False
                    db_results_found = False

                    for m in reversed(self.messages[-10:]):  # 查看最近10条消息
                        if m.role == "tool" and m.content:
                            try:
                                result = json.loads(m.content)

                                # 处理知识库检索结果
                                if "chunks" in result and not kb_results_found:
                                    recent_tool_results.append("=== 知识库信息 ===")
                                    for chunk in result["chunks"][:2]:  # 只取前2个最相关的chunk
                                        text = chunk.get("text", "")[:300]  # 每个chunk限制300字符
                                        recent_tool_results.append(text)
                                    kb_results_found = True

                                # 处理数据库查询结果
                                elif "result" in result and isinstance(result["result"], dict) and not db_results_found:
                                    db_result = result["result"]
                                    if "results" in db_result:
                                        recent_tool_results.append("=== 数据库信息 ===")
                                        # 处理SQL查询结果
                                        for query_result in db_result["results"][:2]:  # 最多2个查询结果
                                            if "rows" in query_result and query_result["rows"]:
                                                # 有数据行
                                                row_count = len(query_result["rows"])
                                                recent_tool_results.append(f"查询返回{row_count}行数据")
                                                # 添加前几行数据的概要
                                                for row in query_result["rows"][:2]:  # 减少到2行避免过长
                                                    row_summary = str(row)[:150]  # 减少字符限制
                                                    recent_tool_results.append(f"数据: {row_summary}")
                                            elif "error" in query_result:
                                                recent_tool_results.append(f"查询错误: {query_result['error']}")
                                            else:
                                                recent_tool_results.append("查询成功但无数据返回")
                                        db_results_found = True

                                # 如果两种数据源都找到了，就停止搜索
                                if kb_results_found and db_results_found:
                                    break

                            except:
                                continue

                    # 3. 构建精简上下文
                    if original_query:
                        filtered_messages.append({"role": "user", "content": original_query.content})

                    # 添加检索结果摘要
                    if recent_tool_results:
                        context_summary = "检索到的相关信息：\n" + "\n".join(recent_tool_results[:3])  # 最多3个片段
                        filtered_messages.append({"role": "assistant", "content": context_summary})

                    # 添加总结请求
                    filtered_messages.append({
                        "role": "user",
                        "content": "根据上述信息回答问题，用中文给出简洁专业的回答。"
                    })

                    total_chars = sum(len(m["content"]) for m in filtered_messages)
                    self._log.info(f"构建的精简上下文: {len(filtered_messages)}条消息, 总字符数: {total_chars}")

                    completion = self._client.chat.completions.create(
                        model=self.model,
                        messages=filtered_messages,
                        max_completion_tokens=4096
                    )
                    response_content = completion.choices[0].message.content.strip()

                    # 添加到消息历史
                    self.memory.add(Message.assistant(response_content))
                    self._log.info(f"LLM生成的最终回答: {response_content[:100]}...")

                    # 设置为完成状态
                    self.state = AgentState.FINISHED
                    return response_content

                except Exception as e:
                    self._log.exception("调用LLM生成最终回答失败")
                    return f"生成最终回答时出错: {e}"

            # 检查是否有最近的assistant回答
            last_assistant = next((m for m in reversed(self.messages) if m.role == "assistant"), None)
            if last_assistant and last_assistant.content:
                content = last_assistant.content.strip()
                # 如果是真正的自然语言回答（不是工具调用结果或标记），返回它
                if content not in ("[tools] executing", "Thinking complete - no action needed", "[tools_executed]"):
                    try:
                        # 检查是否是JSON工具结果
                        json.loads(content)  # 如果是JSON，继续下面的逻辑
                    except (json.JSONDecodeError, TypeError):
                        # 不是JSON，是真正的自然语言回答
                        return content

            # 如果没有合适的回答，返回提示信息，让orchestrator处理
            return "No content or commands to execute"

        results: List[str] = []
        has_retrieve_calls = False

        for tc in self.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}

            handler = self._registry.get_tool_handler(name)
            if not handler:
                observation = f"Error: Unknown tool '{name}'"
                self.memory.add(Message.tool(observation, tool_call_id=tc.id, name=name))
                results.append(observation)
                continue

            # 透传少量上下文给安全/审计层
            args = {**args, "agent_name": self.name, "user_clearance": "MEDIUM"}

            # 为检索工具添加默认集合名称
            if name == "retrieve" and "collection_name" not in args:
                args["collection_name"] = "japan_shrimp"

            try:
                result = await handler(**args)
                observation = json.dumps(result, ensure_ascii=False)

                # 检查是否是需要后续处理的工具（检索或数据库查询）
                if name in ["retrieve", "read_sql_query", "list_sql_tables", "get_tables_schema"]:
                    has_retrieve_calls = True
                    self._log.info(f"检测到数据获取工具调用({name})，将在后续生成自然语言回答")

            except Exception as e:
                observation = f"Error: {e}"

            self.memory.add(Message.tool(observation, tool_call_id=tc.id, name=name))
            results.append(observation)

            # 智能完成判定：仅当显式终止或工具明确返回 finish 时结束
            try:
                # 1. 明确的终止工具
                if name.lower().find("terminate") >= 0:
                    self.state = AgentState.FINISHED
                    self._log.info("检测到终止工具调用，设置Agent状态为FINISHED")
                else:
                    # 2. 工具返回明确完成状态
                    if isinstance(observation, str):
                        data = json.loads(observation)
                        if isinstance(data, dict) and data.get("status") == "finish":
                            self.state = AgentState.FINISHED
                            self._log.info("工具返回完成状态，设置Agent状态为FINISHED")
            except Exception as e:
                self._log.debug(f"完成判定检查出错: {e}")
                pass

        # 如果执行了检索工具，清空工具调用列表并标记需要继续生成回答
        if has_retrieve_calls:
            self._log.info("检索工具执行完成，返回标记以继续生成自然语言回答")
            self.tool_calls = []  # 清空工具调用列表，避免OpenAI API错误
            return "[tools_executed]"  # 返回一个特殊标记

        return "\n\n".join(results)

    def _has_sufficient_information(self) -> bool:
        """检查是否已经获得足够的信息来回答问题"""
        try:
            # 检查是否已经有明确的assistant回答（不是工具调用）
            recent_assistant_messages = [m for m in self.messages[-3:] if m.role == "assistant" and m.content]
            for msg in recent_assistant_messages:
                if (msg.content and 
                    msg.content.strip() not in ("[tools] executing", "Thinking complete - no action needed") and
                    not msg.tool_calls):  # 确保不是工具调用消息
                    self._log.info("检测到明确的assistant回答，认为信息充足")
                    return True
            
            # 检查是否已经进行了多轮工具调用（防止无限循环）
            tool_call_count = len([m for m in self.messages if m.role == "tool"])
            if tool_call_count >= self.info_sufficient_threshold:  # 使用可配置的信息充足阈值
                self._log.info(f"已进行{tool_call_count}次工具调用（阈值={self.info_sufficient_threshold}），认为信息充足")
                return True
                
            return False
        except Exception as e:
            self._log.debug(f"检查信息充足性时出错: {e}")
            return False

    async def cleanup(self):
        try:
            # 只有当使用独立registry时才需要关闭连接
            # 全局工具管理器的连接由服务生命周期管理，不在这里关闭
            if (self._registry and 
                self._registry != global_tool_manager.registry and 
                hasattr(self._registry, 'mcp_client')):
                await self._registry.mcp_client.close()
        except Exception:
            pass


