import json
from across_edge.rpc import JsonRpcClient


def test_json_rpc_client_sends_stable_user_agent(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return json.dumps({"jsonrpc":"2.0","id":1,"result":"0xa4b1"}).encode()

    def fake_urlopen(req, timeout):
        captured["user_agent"] = req.headers.get("User-agent")
        captured["content_type"] = req.headers.get("Content-type")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = JsonRpcClient("https://example.invalid").call("eth_chainId")
    assert result.result == "0xa4b1"
    assert captured["user_agent"] == "Across-Edge-shadow/1.0"
    assert captured["content_type"] == "application/json"
