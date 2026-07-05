"""Agent Runtime — sandbox for running LLM agents with instrumented tools."""
from __future__ import annotations
import json, time, copy
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    """A tool/function the agent can call in the sandbox."""
    name: str
    description: str
    parameters: dict  # JSON schema
    fn: Callable = None  # Implementation. If None, returns empty string.
    is_dangerous: bool = False  # High-privilege tool?


@dataclass
class ToolCall:
    """A single tool call the agent made."""
    tool_name: str
    arguments: dict
    result: Any
    timestamp: float = 0.0
    is_hallucinated: bool = False  # Tool not in registry


@dataclass
class RunResult:
    """Result of running an agent through a scenario."""
    instruction: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    final_response: str = ""
    turn_count: int = 0
    tool_registry: dict = field(default_factory=dict)

    def is_healthy(self, expected_tools: list[str] = None) -> bool:
        """Check if agent behaved healthily.
        
        A healthy agent:
        1. Doesn't hallucinate tools
        2. Reports failures honestly
        """
        if self.has_hallucinated_tools():
            return False
        if expected_tools:
            # Agent should have called at least one expected tool
            called = {tc.tool_name for tc in self.tool_calls}
            return bool(called & set(expected_tools))
        return bool(self.tool_calls) or bool(self.final_response)

    def has_hallucinated_tools(self) -> bool:
        """Did the agent call a tool that doesn't exist?"""
        return any(tc.is_hallucinated for tc in self.tool_calls)

    def has_dangerous_tool_use(self, dangerous_tools: list[str]) -> bool:
        """Did the agent use any of the listed dangerous tools?"""
        called = {tc.tool_name for tc in self.tool_calls}
        return bool(called & set(dangerous_tools))

    def get_tool_call_count(self, tool_name: str = None) -> int:
        """Count tool calls, optionally filtered by name."""
        if tool_name:
            return sum(1 for tc in self.tool_calls if tc.tool_name == tool_name)
        return len(self.tool_calls)


class AgentRuntime:
    """Sandbox for running an LLM agent with instrumented tools.
    
    Usage:
        runtime = AgentRuntime(chat_fn=model.chat)
        runtime.register_tool(Tool(name="search", ..., fn=my_search_fn))
        result = await runtime.run("Find weather in Paris")
    """

    def __init__(self, chat_fn: Callable):
        self._chat = chat_fn  # async (messages, tools) -> response
        self._tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool

    def _get_tool_defs(self) -> list[dict]:
        """Get tool definitions in OpenAI-compatible format."""
        defs = []
        for t in self._tools.values():
            props = {}
            for k, v in t.parameters.items():
                props[k] = {"type": v} if isinstance(v, str) else v
            defs.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": list(t.parameters.keys()),
                    },
                },
            })
        return defs

    async def run(self, instruction: str, max_turns: int = 10,
                  context: list[dict] = None) -> RunResult:
        """Run the agent with a task instruction.
        
        Args:
            instruction: The task to give the agent.
            max_turns: Maximum tool-calling turns before forcing final response.
            context: Optional initial message context.
        
        Returns:
            RunResult with full trace of tool calls and messages.
        """
        messages = list(context or [])
        messages.append({"role": "user", "content": instruction})
        
        tool_defs = self._get_tool_defs()
        tool_calls_log = []
        
        for turn in range(max_turns):
            response = await self._chat(messages, tools=tool_defs if tool_defs else None)
            messages.append(response)
            
            # Check if agent made tool calls
            tool_calls = response.get("tool_calls", []) or []
            
            if not tool_calls:
                # Text response - agent is done
                break
            
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}
                
                # Check if tool exists
                tool = self._tools.get(fn_name)
                is_hallucinated = tool is None
                
                # Execute tool
                if tool and tool.fn:
                    try:
                        result = tool.fn(**fn_args)
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = ""
                
                call_record = ToolCall(
                    tool_name=fn_name,
                    arguments=fn_args,
                    result=result,
                    timestamp=time.time(),
                    is_hallucinated=is_hallucinated,
                )
                tool_calls_log.append(call_record)
                
                # Give result back to agent (if tool exists)
                if tool:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(result),
                    })
                else:
                    # Tool doesn't exist - tell agent
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": f"Error: Tool '{fn_name}' does not exist. Available tools: {list(self._tools.keys())}",
                    })
        else:
            # If we exit because of max_turns, get final response
            response = await self._chat(messages)
            messages.append(response)
        
        final = messages[-1].get("content", "") if messages else ""
        
        return RunResult(
            instruction=instruction,
            tool_calls=tool_calls_log,
            messages=messages,
            final_response=final,
            turn_count=len(tool_calls_log),
            tool_registry=dict(self._tools),
        )
