"""
MiroFish 代码改进前后对比演示
=====================================
本脚本模拟四个关键改进点的 "改进前 vs 改进后" 行为，
无需真实的 LLM / Zep 凭证，可独立运行。

运行方式:
    python comparison_demo.py
"""

import json
import time
import traceback
import textwrap
from pathlib import Path
import tempfile
import os

# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────

def section(title: str):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)

def label(tag: str, text: str, *, indent: int = 2):
    pad = " " * indent
    print(f"{pad}[{tag}]  {text}")

def show_json(obj: dict, *, indent: int = 4):
    lines = json.dumps(obj, ensure_ascii=False, indent=2).splitlines()
    for line in lines:
        print(" " * indent + line)

# ─────────────────────────────────────────
# 1. 内部堆栈暴露 (Traceback Exposure)
# ─────────────────────────────────────────

section("改进 1 — 移除 HTTP 响应中的堆栈信息 (Traceback Exposure)")

def simulate_api_call_before():
    """改进前：把完整堆栈返回给客户端"""
    try:
        raise ValueError("ZEP_API_KEY 未配置")
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()   # ← 直接暴露内部堆栈
        }, 500

def simulate_api_call_after():
    """改进后：堆栈只写服务端日志，客户端只收到 error 摘要"""
    try:
        raise ValueError("ZEP_API_KEY 未配置")
    except Exception as e:
        # 服务端日志（含完整 traceback）
        # logger.error(f"操作失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)                        # ← 仅暴露安全摘要
        }, 500

resp_before, _ = simulate_api_call_before()
resp_after,  _ = simulate_api_call_after()

label("改进前", "客户端收到的 JSON 响应:")
show_json(resp_before)

print()
label("改进后", "客户端收到的 JSON 响应:")
show_json(resp_after)

tb_lines = resp_before.get("traceback", "").strip().splitlines()
print(f"\n  ⚠  改进前泄漏了 {len(tb_lines)} 行堆栈信息（含文件路径、行号、变量名）")
print( "  ✓  改进后堆栈信息仅写入服务端日志，攻击者无法通过响应体推断内部结构")

# ─────────────────────────────────────────
# 2. CORS 配置 (Wildcard vs. Allowlist)
# ─────────────────────────────────────────

section("改进 2 — CORS 来源限制（通配符 → 白名单）")

CORS_BEFORE = {"origins": "*"}
CORS_AFTER  = {"origins": ["http://localhost:5173", "http://localhost:5001"]}

# 模拟浏览器跨域请求
def check_cors(config: dict, request_origin: str) -> bool:
    allowed = config["origins"]
    if allowed == "*":
        return True
    return request_origin in allowed

test_origins = [
    ("http://localhost:5173",      "合法来源（前端开发服务器）"),
    ("http://localhost:5001",      "合法来源（后端自测）"),
    ("https://attacker.example",   "恶意第三方网站"),
    ("https://phishing-mirofish.io", "仿冒域名"),
]

label("改进前", f"CORS 配置: origins = \"{CORS_BEFORE['origins']}\"")
for origin, desc in test_origins:
    ok = check_cors(CORS_BEFORE, origin)
    status = "✓ 允许" if ok else "✗ 拒绝"
    print(f"    {status}  {origin:<42} ({desc})")

print()
label("改进后", f"CORS 配置: origins = {CORS_AFTER['origins']}")
for origin, desc in test_origins:
    ok = check_cors(CORS_AFTER, origin)
    status = "✓ 允许" if ok else "✗ 拒绝"
    print(f"    {status}  {origin:<42} ({desc})")

print("\n  ✓  现在可通过 CORS_ORIGINS 环境变量按部署环境配置允许来源")

# ─────────────────────────────────────────
# 3. LLM 客户端重试逻辑 (Retry Logic)
# ─────────────────────────────────────────

section("改进 3 — LLMClient 指数退避重试 & 精确异常类型")

class FakeRateLimitError(Exception):
    """模拟 openai.RateLimitError"""

class FakeAPIStatusError(Exception):
    """模拟 openai.APIStatusError (4xx)"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

_RETRYABLE = (FakeRateLimitError,)

# ── 改进前 ──
def llm_chat_before(call_fn):
    """改进前：catch-all Exception，无重试，失败即抛"""
    try:
        return call_fn()
    except Exception as e:
        raise RuntimeError(f"LLM调用失败: {e}") from e

# ── 改进后 ──
def llm_chat_after(call_fn, max_retries: int = 3, retry_delay: float = 0.05):
    """改进后：可重试错误指数退避，不可重试错误立即抛出"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return call_fn()
        except _RETRYABLE as e:
            last_error = e
            wait = retry_delay * (2 ** attempt)
            print(f"    ↻  第 {attempt+1}/{max_retries} 次重试（等待 {wait*1000:.0f}ms）: {type(e).__name__}")
            time.sleep(wait)
        except FakeAPIStatusError as e:
            print(f"    ✗  不可重试的 API 错误 [{e.status_code}]: {e.message}")
            raise
    raise RuntimeError(f"重试耗尽: {last_error}")

# 场景 A：速率限制（应重试后成功）
attempts_a = {"count": 0}
def call_with_rate_limit():
    attempts_a["count"] += 1
    if attempts_a["count"] < 3:
        raise FakeRateLimitError("rate limit exceeded")
    return "模拟 LLM 回复: 这是一个关于气候变化的深度分析..."

label("改进前", "速率限制错误（无重试）:")
try:
    result = llm_chat_before(call_with_rate_limit)
except Exception as e:
    print(f"    → 直接抛出异常，请求永久失败: {e}")

print()
attempts_a["count"] = 0   # 重置计数
label("改进后", "速率限制错误（指数退避重试）:")
try:
    result = llm_chat_after(call_with_rate_limit)
    print(f"    ✓  第 {attempts_a['count']} 次尝试成功: {result[:40]}...")
except Exception as e:
    print(f"    ✗  {e}")

# 场景 B：认证错误（不应重试）
print()
attempts_b = {"count": 0}
def call_with_auth_error():
    attempts_b["count"] += 1
    raise FakeAPIStatusError(401, "Invalid API key")

label("改进后", "认证失败（401）— 不可重试，立即抛出:")
try:
    llm_chat_after(call_with_auth_error)
except FakeAPIStatusError as e:
    print(f"    ✓  正确地立即失败（不浪费 {attempts_b['count']-1} 次无效重试）")

# ─────────────────────────────────────────
# 4. 文件上传验证 (MIME-Type Validation)
# ─────────────────────────────────────────

section("改进 4 — 文件上传内容验证（扩展名欺骗防护）")

_PDF_MAGIC    = b'%PDF'
_BLOCKED      = (b'MZ', b'\x7fELF', b'PK\x03\x04')
_MAX_SIZE     = 50 * 1024 * 1024

# ── 改进前 ──
def validate_before(filename: str) -> bool:
    """仅检查扩展名"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in {'pdf', 'md', 'txt', 'markdown'}

# ── 改进后 ──
def validate_after(filename: str, file_bytes: bytes) -> bool:
    """同时验证扩展名 + 文件魔数"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in {'pdf', 'md', 'txt', 'markdown'}:
        return False
    header = file_bytes[:8]
    for magic in _BLOCKED:
        if header.startswith(magic):
            raise ValueError(f"检测到被拒绝的文件类型（魔数 {magic!r}）")
    if ext == 'pdf' and not header.startswith(_PDF_MAGIC):
        raise ValueError("文件内容与 .pdf 扩展名不符（缺少 %PDF 魔数）")
    return True

# 准备测试用例
test_cases = [
    ("report.pdf",     _PDF_MAGIC + b"-1.7 %\xe2\xe3",  "合法 PDF"),
    ("notes.md",       b"# Hello World\n",               "合法 Markdown"),
    ("malware.pdf",    b'MZ\x90\x00\x03\x00',            "Windows PE 改名为 .pdf"),
    ("archive.pdf",    b'PK\x03\x04\x14\x00',            "ZIP 改名为 .pdf"),
    ("script.txt",     b'\x7fELF\x02\x01',               "ELF 二进制改名为 .txt"),
    ("fake.pdf",       b'This is just text',              "纯文本改名为 .pdf"),
]

label("改进前", "仅验证扩展名（所有测试文件均通过）:")
for fname, fbytes, desc in test_cases:
    ok = validate_before(fname)
    status = "✓ 通过" if ok else "✗ 拒绝"
    print(f"    {status}  {fname:<20} ({desc})")

print()
label("改进后", "同时验证扩展名 + 文件魔数:")
for fname, fbytes, desc in test_cases:
    try:
        ok = validate_after(fname, fbytes)
        status = "✓ 通过" if ok else "✗ 拒绝"
        reason = ""
    except ValueError as e:
        status = "✗ 拒绝"
        reason = f"  ← {e}"
    print(f"    {status}  {fname:<20} ({desc}){reason}")

# ─────────────────────────────────────────
# 总结
# ─────────────────────────────────────────

section("改进总结")

improvements = [
    ("安全",   "移除 HTTP 响应中的内部堆栈信息",
               "51 处 traceback.format_exc() 从 API 响应中移除，改为 exc_info=True 写入服务端日志"),
    ("安全",   "CORS 来源白名单替代通配符",
               "origins='*' → 可配置白名单（CORS_ORIGINS 环境变量），默认限制为 localhost 开发端口"),
    ("可靠性", "LLMClient 指数退避重试",
               "新增 RateLimitError / APITimeoutError / APIConnectionError 的自动重试（最多 3 次，间隔 2/4/8s）"),
    ("安全",   "文件上传 MIME 魔数验证",
               "在扩展名检查之外增加文件头魔数校验，阻止 PE/ELF/ZIP 伪装为 pdf/txt 上传"),
    ("安全",   "DEBUG 模式默认关闭",
               "FLASK_DEBUG 默认值从 'True' 改为 'False'，防止生产环境意外暴露调试信息"),
]

for category, title, detail in improvements:
    print(f"\n  [{category}]  {title}")
    wrapped = textwrap.fill(detail, width=72, initial_indent="           ", subsequent_indent="           ")
    print(wrapped)

print("\n" + "=" * 60)
print("  所有改进均已应用到 branch: claude/code-review-improvements-WaDYG")
print("=" * 60 + "\n")
