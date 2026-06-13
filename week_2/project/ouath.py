import os
import json
import sys
import asyncio
import webbrowser
from urllib.parse import parse_qs, urlparse

import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

ALPHAXIV_MCP_URL = "https://api.alphaxiv.org/mcp/v1"
REDIRECT_URI = "http://localhost:8765/callback"
TOKEN_FILE = ".alphaxiv_tokens.json"

class FileTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens = None
        self.client_info = None

    def _save(self):
        data = {}
        if self.tokens:
            data["tokens"] = self.tokens.model_dump(mode="json")
        if self.client_info:
            data["client_info"] = self.client_info.model_dump(mode="json")
        with open(TOKEN_FILE, "w") as f:
            f.write(json.dumps(data, indent=2))
        print(f"Token successfully saved to disk at: {os.path.abspath(TOKEN_FILE)}")

    async def get_tokens(self) -> OAuthToken | None: return self.tokens
    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens
        self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None: return self.client_info
    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info
        self._save()

async def open_browser(auth_url: str) -> None:
    print(f"Opening browser for login...\nIf it doesn't open, visit: {auth_url}\n")
    webbrowser.open(auth_url)

async def wait_for_callback() -> tuple[str, str | None]:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    code = state = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal code, state
            params = parse_qs(urlparse(self.path).query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorized. You can close this tab and return to the terminal.</h1>")
        def log_message(self, *args): pass

    print(f"Waiting for callback on {REDIRECT_URI} ...")
    server = HTTPServer(("localhost", 8765), Handler)
    server.timeout = 120
    server.handle_request()
    server.server_close()

    if not code:
        raise RuntimeError("OAuth callback received no authorization code.")
    return code, state

async def run_auth():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        
    storage = FileTokenStorage()
    auth = OAuthClientProvider(
        server_url=ALPHAXIV_MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name="AlphaXiv Search TUI Client",
            redirect_uris=[REDIRECT_URI],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="read",
        ),
        storage=storage,
        redirect_handler=open_browser,
        callback_handler=wait_for_callback,
    )

    print("Initializing connection to complete initial token generation...")
    try:
        async with httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=60) as http:
            async with streamable_http_client(ALPHAXIV_MCP_URL, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("AlphaXiv Session initialized cleanly.")
        
        print("\nAuthorization finished successfully!")
    except Exception as e:
        print(f"\nAuthentication Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(run_auth())