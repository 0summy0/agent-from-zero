import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

CHAPTER_ID = "2.5-mcp"
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "agent-from-zero-add-server"
SERVER_VERSION = "1.0.0"

ADD_TOOL = {
    "name": "add",
    "description": "Add two finite numbers and return their sum.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
        "additionalProperties": False,
    },
}


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def error_response(request_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def is_finite_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def call_add(arguments):
    if not isinstance(arguments, dict):
        raise RpcError(-32602, "tools/call arguments must be an object")
    if set(arguments) != {"a", "b"}:
        raise RpcError(-32602, "add requires exactly the arguments a and b")
    if not all(is_finite_number(arguments[key]) for key in ("a", "b")):
        raise RpcError(-32602, "add arguments must be finite numbers")
    total = arguments["a"] + arguments["b"]
    if isinstance(total, float) and not math.isfinite(total):
        raise RpcError(-32602, "add result must be finite")
    return {
        "content": [{"type": "text", "text": str(total)}],
        "isError": False,
    }


def handle_request(request):
    if not isinstance(request, dict):
        return error_response(None, -32600, "Invalid Request")
    request_id = request.get("id")
    is_notification = "id" not in request
    method = request.get("method")
    if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
        if is_notification:
            return None
        return error_response(request_id, -32600, "Invalid Request")

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            result = {"tools": [ADD_TOOL]}
        elif method == "tools/call":
            params = request.get("params")
            if not isinstance(params, dict) or params.get("name") != "add":
                raise RpcError(-32602, "This server only provides the add tool")
            result = call_add(params.get("arguments"))
        else:
            raise RpcError(-32601, "Method not found")
    except RpcError as exc:
        if is_notification:
            return None
        return error_response(request_id, exc.code, exc.message)

    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def reject_non_json_number(value):
    raise ValueError(f"non-JSON numeric constant: {value}")


def serve_stdio():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line, parse_constant=reject_non_json_number)
        except (json.JSONDecodeError, ValueError):
            response = error_response(None, -32700, "Parse error")
        else:
            response = handle_request(request)
        if response is not None:
            encoded = json.dumps(response, ensure_ascii=False, allow_nan=False)
            sys.stdout.write(encoded + "\n")
            sys.stdout.flush()
    return 0


class MCPClient:
    def __init__(self, script_path=None):
        self.script_path = Path(script_path or Path(__file__).resolve())
        self.process = None
        self._next_id = 1
        self.returncode = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def start(self):
        if self.process is not None:
            raise RuntimeError("client has already been started")
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(self.script_path), "--server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        return self

    def _write(self, message):
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("client is not running")
        self.process.stdin.write(json.dumps(message, allow_nan=False) + "\n")
        self.process.stdin.flush()

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def request(self, method, params=None):
        request_id = self._next_id
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("client is not running")
        for line in self.process.stdout:
            response = json.loads(line)
            if response.get("id") == request_id:
                return response
        raise RuntimeError("server closed stdout before replying")

    def close(self):
        if self.process is None:
            return None
        if self.returncode is None:
            if self.process.stdin is not None:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.returncode = self.process.returncode
            if self.process.stdout is not None:
                self.process.stdout.close()
        return self.returncode


def run_minimal_path():
    with MCPClient() as client:
        initialize = client.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agent-from-zero-learner", "version": "1.0.0"},
            },
        )
        client.notify("notifications/initialized")
        tools = client.request("tools/list")
        add_call = client.request(
            "tools/call",
            {"name": "add", "arguments": {"a": 17, "b": 25}},
        )
        exit_code = client.close()
    return {
        "chapter": CHAPTER_ID,
        "transport": "stdio-newline-json",
        "initialize": initialize,
        "tools": tools,
        "add_call": add_call,
        "closed_normally": exit_code == 0,
        "server_exit_code": exit_code,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="store_true", help="run the stdio JSON-RPC server")
    args = parser.parse_args()
    if args.server:
        return serve_stdio()
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
