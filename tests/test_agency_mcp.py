from portable.agency_agent_capabilities import AllowlistedToolPolicy, ToolRegistry, ToolSpec
from portable.agency_mcp import MCPRequest, MCPToolEndpoint


def test_mcp_list_and_call():
    registry = ToolRegistry([ToolSpec("echo", "return text", "execution", handler=lambda text: text)])
    endpoint = MCPToolEndpoint(registry, AllowlistedToolPolicy(allowed_tools=frozenset({"echo"})))
    listed = endpoint.handle(MCPRequest(1, "tools/list", {})).as_dict()
    assert listed["result"]["tools"][0]["name"] == "echo"
    called = endpoint.handle(MCPRequest(2, "tools/call", {"name": "echo", "arguments": {"text": "ok"}})).as_dict()
    assert called["result"]["content"][0]["text"] == "ok"
