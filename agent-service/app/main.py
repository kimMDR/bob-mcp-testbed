import os
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Agent Service",
    version="0.1.0",
)

GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "http://gateway:8080",
)

TEST_USER_TOKEN = os.getenv(
    "TEST_USER_TOKEN",
    "test-user-token",
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    request_id: str
    session_id: str
    status: str
    message: str
    tool_call: dict
    gateway_result: dict


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "agent-service",
    }


def authenticate(authorization: str | None) -> str:
    expected = f"Bearer {TEST_USER_TOKEN}"

    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 인증 Token",
        )

    return "user-test-001"


def create_temporary_tool_call(message: str) -> dict:
    """
    LLM을 연결하기 전 사용하는 임시 변환 로직이다.
    실제 보안 판정 로직이 아니다.
    """

    sensitive_keywords = [
        "민감",
        "비밀",
        "인증정보",
        "비밀번호",
        "password",
        "secret",
    ]

    is_sensitive = any(
        keyword.lower() in message.lower()
        for keyword in sensitive_keywords
    )

    if is_sensitive:
        path = "/data/sensitive/secret.txt"
    else:
        path = "/data/public/notice.txt"

    return {
        "server_id": "file-mcp",
        "tool_name": "read_file",
        "arguments": {
            "path": path,
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    user_id = authenticate(authorization)

    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    tool_call_id = str(uuid.uuid4())

    tool_call = create_temporary_tool_call(request.message)

    gateway_request = {
        "request_id": request_id,
        "session_id": session_id,
        "user_id": user_id,
        "agent_id": "document-agent-test",
        "server_id": tool_call["server_id"],
        "tool_call_id": tool_call_id,
        "tool_name": tool_call["tool_name"],
        "arguments": tool_call["arguments"],
    }

    print(
        {
            "event": "request_received",
            "request_id": request_id,
            "session_id": session_id,
            "user_id": user_id,
            "message": request.message,
        },
        flush=True,
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/tool-call",
                json=gateway_request,
            )
            response.raise_for_status()

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gateway 연결 실패: {error}",
        ) from error

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Gateway가 오류 상태를 반환함: "
                f"{error.response.status_code}"
            ),
        ) from error

    gateway_result = response.json()
    decision = gateway_result["decision"]

    if decision == "allow":
        status = "allowed"
        response_message = (
            "Gateway가 Tool Call을 허용했습니다. "
            "아직 실제 MCP Tool은 연결하지 않았습니다."
        )
    else:
        status = "blocked"
        response_message = (
            "Gateway가 Tool Call을 차단했습니다."
        )

    return ChatResponse(
        request_id=request_id,
        session_id=session_id,
        status=status,
        message=response_message,
        tool_call={
            "tool_call_id": tool_call_id,
            **tool_call,
        },
        gateway_result=gateway_result,
    )
