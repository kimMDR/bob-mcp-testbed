from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Mock File MCP",
    version="0.1.0",
)

DATA_ROOT = Path("/data").resolve()


class ReadFileRequest(BaseModel):
    request_id: str
    tool_call_id: str
    path: str


class ReadFileResponse(BaseModel):
    request_id: str
    tool_call_id: str
    tool_name: str
    path: str
    content: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "mock-mcp",
    }


@app.post(
    "/tools/read-file",
    response_model=ReadFileResponse,
)
async def read_file(
    request: ReadFileRequest,
) -> ReadFileResponse:
    requested_path = Path(request.path)

    if not requested_path.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="파일 경로는 절대 경로여야 합니다.",
        )

    resolved_path = requested_path.resolve()

    if not resolved_path.is_relative_to(DATA_ROOT):
        raise HTTPException(
            status_code=403,
            detail="허용된 테스트 데이터 경로가 아닙니다.",
        )

    if not resolved_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="파일을 찾을 수 없습니다.",
        )

    try:
        content = resolved_path.read_text(
            encoding="utf-8",
        )
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="UTF-8 텍스트 파일만 읽을 수 있습니다.",
        ) from error

    print(
        {
            "event": "tool_executed",
            "request_id": request.request_id,
            "tool_call_id": request.tool_call_id,
            "tool_name": "read_file",
            "path": request.path,
        },
        flush=True,
    )

    return ReadFileResponse(
        request_id=request.request_id,
        tool_call_id=request.tool_call_id,
        tool_name="read_file",
        path=request.path,
        content=content,
    )
