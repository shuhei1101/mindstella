"""ワークスペースと MindStella のセッションの作成・一覧・停止・クローズと、フックの出来事の受け取りの HTTP の経路。"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

import sessions
import workspaces
from errors import ApiError

logger = logging.getLogger("mindstella.api")

# problem+json の media type
PROBLEM_MEDIA_TYPE = "application/problem+json"

# 端末の中とみなすホスト名
LOCAL_HOSTS = ("127.0.0.1", "localhost")

# DELETE の force を真とみなす値
TRUE_VALUES = ("1", "true", "yes")


def build_routes(ctx: Any) -> list[Route]:
    """MindStella の API の経路を返す。"""

    async def create_workspace(request: Request) -> Response:
        """ワークスペースを作る。"""
        body = await _json_body(request, required=True)
        status, result = await run_in_threadpool(workspaces.create_workspace, body, ctx)
        return JSONResponse(result, status_code=status)

    async def create_session(request: Request) -> Response:
        """MindStella のセッションを作る。"""
        body = await _json_body(request, required=False)
        config_dir = body.get("claude_config_dir")
        if config_dir is not None and not isinstance(config_dir, str):
            raise ApiError(400, "body", "claude_config_dir は文字列にしてください")
        status, result = await run_in_threadpool(
            sessions.create_session, request.path_params["id"], config_dir, ctx
        )
        return JSONResponse(result, status_code=status)

    async def list_sessions(request: Request) -> Response:
        """MindStella のセッションの一覧を返す。"""
        result = await run_in_threadpool(sessions.list_sessions, request.path_params["id"], ctx)
        return JSONResponse(result)

    async def stop_session(request: Request) -> Response:
        """MindStella のセッションを止める。"""
        force = request.query_params.get("force", "").lower() in TRUE_VALUES
        status, result = await run_in_threadpool(
            sessions.stop_session,
            request.path_params["id"],
            request.path_params["session"],
            force,
            ctx,
        )
        return JSONResponse(result, status_code=status)

    async def close_workspace(request: Request) -> Response:
        """ワークスペースをクローズにする。"""
        result = await run_in_threadpool(workspaces.close_workspace, request.path_params["id"], ctx)
        return JSONResponse(result)

    async def record_event(request: Request) -> Response:
        """フックが送った出来事を記録する。"""
        body = await _json_body(request, required=True)
        recorded = await run_in_threadpool(
            sessions.record_event, request.path_params["session"], body, ctx
        )
        return JSONResponse({"recorded": recorded})

    def guarded(
        handler: Callable[[Request], Awaitable[Response]],
    ) -> Callable[[Request], Awaitable[Response]]:
        """Host を確かめてから呼び、ApiError を problem+json にする。"""

        async def endpoint(request: Request) -> Response:
            """経路の入口。"""
            try:
                check_host(request, ctx.port)
                return await handler(request)
            except ApiError as error:
                return problem_response(error)
            except Exception:
                logger.exception(
                    "mindstella.api.unexpected_error",
                    extra={"method": request.method, "path": request.url.path},
                )
                return problem_response(
                    ApiError(
                        500,
                        "internal",
                        "常駐サーバーの中でエラーが起きました（server.log を見てください）",
                    )
                )

        return endpoint

    return [
        Route("/workspaces", guarded(create_workspace), methods=["POST"]),
        Route("/workspaces/{id}/sessions", guarded(create_session), methods=["POST"]),
        Route("/workspaces/{id}/sessions", guarded(list_sessions), methods=["GET"]),
        Route("/workspaces/{id}/sessions/{session}", guarded(stop_session), methods=["DELETE"]),
        Route("/workspaces/{id}/close", guarded(close_workspace), methods=["POST"]),
        Route("/_admin/sessions/{session}/events", guarded(record_event), methods=["POST"]),
    ]


def check_host(request: Request, port: int) -> None:
    """Host が端末の中の値で、Origin があるときも同じ値かを確かめる。"""
    hosts = {f"{name}:{port}" for name in LOCAL_HOSTS}
    origins = {f"http://{host}" for host in hosts}
    host = request.headers.get("host")
    origin = request.headers.get("origin")
    if host not in hosts or (origin is not None and origin not in origins):
        logger.warning("mindstella.api.host_rejected", extra={"host": host, "origin": origin})
        raise ApiError(403, "host", "端末の中（127.0.0.1・localhost）からの要求だけを受けます")


def problem_response(error: ApiError) -> JSONResponse:
    """ApiError を application/problem+json の応答にする。"""
    content: dict[str, Any] = {
        "type": "about:blank",
        "title": HTTPStatus(error.status).phrase,
        "status": error.status,
        "detail": error.detail,
        "stage": error.stage,
        **error.extra,
    }
    return JSONResponse(content, status_code=error.status, media_type=PROBLEM_MEDIA_TYPE)


async def _json_body(request: Request, *, required: bool) -> dict[str, Any]:
    """本文を JSON のオブジェクトとして読む。空の本文は required でなければ空のオブジェクト。"""
    raw = await request.body()
    if not raw and not required:
        return {}
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise ApiError(400, "body", f"本文を JSON として読めません: {error}") from error
    if not isinstance(value, dict):
        raise ApiError(400, "body", "本文は JSON のオブジェクトにしてください")
    return value
