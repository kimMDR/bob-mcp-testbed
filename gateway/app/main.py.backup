import time
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="MCP Security Gateway",
    version="0.1.0",
)


class ToolCallRequest(BaseModel):
    request_id: str
    session_id: str
    user_id: str
    agent_id: str
    server_id: str
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    request_id: str
    tool_call_id: str
    decision: Literal["allow", "deny"]
    policy_id: str
    reason: str
    execution_status: Literal["not_executed", "blocked"]
    latency_ms: float


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "gateway",
    }


@app.post("/tool-call", response_model=DecisionResponse)
async def evaluate_tool_call(
    request: ToolCallRequest,
) -> DecisionResponse:
    started_at = time.perf_counter()

    decision = "deny"
    reason = "정책에서 허용하지 않은 요청"

    path = request.arguments.get("path")

    if (
        request.server_id == "file-mcp"
        and request.tool_name == "read_file"
        and isinstance(path, str)
        and path.startswith("/data/public/")
    ):
        decision = "allow"
        reason = "공개 디렉터리의 파일 읽기 허용"

    execution_status = (
        "not_executed"
        if decision == "allow"
        else "blocked"
    )

    latency_ms = round(
        (time.perf_counter() - started_at) * 1000,
        3,
    )

    print(
        {
            "event": "policy_decision",
            "request_id": request.request_id,
            "tool_call_id": request.tool_call_id,
            "user_id": request.user_id,
            "agent_id": request.agent_id,
            "server_id": request.server_id,
            "tool_name": request.tool_name,
            "decision": decision,
            "reason": reason,
        },
        flush=True,
    )

    return DecisionResponse(
        request_id=request.request_id,
        tool_call_id=request.tool_call_id,
        decision=decision,
        policy_id="temporary-file-policy-v1",
        reason=reason,
        execution_status=execution_status,
        latency_ms=latency_ms,
    )
