"""LangGraph ReAct-style HR agent with tool calling and conversation memory."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.app.agent.llm import build_llm, resolve_llm_provider
from backend.app.agent.local_agent import run_local_hr_agent
from backend.app.agent.tools import HR_TOOLS

SYSTEM_PROMPT = """You are Acme Corp's HR Chat Agent — a helpful, accurate, and privacy-aware assistant for authenticated employees.

## Goals
1. Answer HR policy questions using the `search_hr_policies` tool (do not invent policy).
2. Answer personal/dynamic questions (leave balance, eligibility, calculations, recent requests) using the database tools.
3. Explain your reasoning briefly: which tool you used and what the result means for the employee.
4. Be concise, professional, and actionable.

## Rules
- Only discuss data for the currently authenticated employee. Never ask for or reveal another employee's private data.
- If a policy excerpt is used, cite the document/source name (e.g., leave_policy.md / HR-POL-LEAVE-2025).
- If information is insufficient, say what is missing and suggest contacting hr-support@acmecorp.example.
- For leave calculations, prefer `calculate_leave_days` rather than manual math.
- For eligibility questions, call `check_leave_eligibility` and, when useful, `get_leave_balance`.
- Do not fabricate balances or approval outcomes.

## Response style
- Start with a direct answer.
- Then add a short "Details" section with numbers, eligibility reasons, or policy citations.
- Optionally end with a next-step suggestion (e.g., submit leave request to manager).
"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_hr_agent():
    llm = build_llm()
    if llm is None:
        raise RuntimeError("No chat LLM configured; use local tool mode instead.")
    llm = llm.bind_tools(HR_TOOLS)
    tool_node = ToolNode(HR_TOOLS)

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_AGENT = None


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = build_hr_agent()
    return _AGENT


def run_hr_agent(user_message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Run one turn of the HR agent and return answer + tool trace for demo transparency."""
    provider = resolve_llm_provider()
    if provider == "local":
        return run_local_hr_agent(user_message)

    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))
    agent = get_agent()
    result = agent.invoke({"messages": messages})
    final_messages = result["messages"]

    tool_trace: list[dict[str, Any]] = []
    for msg in final_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                tool_trace.append(
                    {
                        "tool": call.get("name"),
                        "args": call.get("args", {}),
                        "type": "call",
                    }
                )
        if isinstance(msg, ToolMessage):
            content = msg.content
            if isinstance(content, str) and len(content) > 1200:
                content = content[:1200] + "…"
            tool_trace.append(
                {
                    "tool": msg.name,
                    "output": content,
                    "type": "result",
                }
            )

    answer = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            answer = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    return {
        "answer": answer or "I could not generate a response. Please try again.",
        "tool_trace": tool_trace,
        "llm_provider": provider,
    }
