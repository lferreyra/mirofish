"""
错误响应处理工具
"""

import json
from typing import Any

from flask import Response


def sanitize_error_payload(payload: Any, status_code: int, debug_mode: bool = False) -> Any:
    """在非调试模式下移除 5xx JSON 响应中的 traceback 详情"""
    if debug_mode or status_code < 500 or not isinstance(payload, dict) or 'traceback' not in payload:
        return payload

    sanitized_payload = dict(payload)
    sanitized_payload.pop('traceback', None)
    return sanitized_payload


def sanitize_json_error_response(response: Response, debug_mode: bool = False) -> Response:
    """对 Flask JSON 响应做统一脱敏，避免向客户端泄露内部栈信息"""
    if not response.is_json:
        return response

    payload = response.get_json(silent=True)
    sanitized_payload = sanitize_error_payload(
        payload,
        status_code=response.status_code,
        debug_mode=debug_mode
    )

    if sanitized_payload is payload:
        return response

    response.set_data(json.dumps(sanitized_payload, ensure_ascii=False))
    return response
