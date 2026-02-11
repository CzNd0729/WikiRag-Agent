import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def test_mcp_server():
    # 配置启动 MCP 服务器的参数
    # 使用模块方式运行我们编写的服务器，模拟真实使用场景
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_servers.stardew_mcp"],
    )

    print("正在连接到 Stardew Valley MCP Server...\n")
    
    # 建立 stdio 连接和 ClientSession
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()

            # 1. 获取并打印所有可用的 Tools
            tools = await session.list_tools()
            print("--- 可用的 MCP Tools ---")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
            print()

            # 2. 测试 get_player_status 工具
            print("--- 调用 get_player_status ---")
            result = await session.call_tool("get_player_status", arguments={})
            # 结果通常在 content 的第一项的 text 属性中 (JSON 字符串)
            status_text = result.content[0].text
            print(json.dumps(json.loads(status_text), indent=2, ensure_ascii=False))
            print()

            # 3. 测试 get_social_info 工具 (截断显示)
            print("--- 调用 get_social_info (Sample) ---")
            result = await session.call_tool("get_social_info", arguments={})
            social_text = result.content[0].text
            social_data = json.loads(social_text)
            sample_social = {k: social_data[k] for k in list(social_data.keys())[:5]}
            print(json.dumps(sample_social, indent=2, ensure_ascii=False))
            print()
            
            # 4. 测试 get_inventory 工具 (截断显示)
            print("--- 调用 get_inventory (Sample) ---")
            result = await session.call_tool("get_inventory", arguments={})
            # 对于返回列表的工具，FastMCP 会将列表的每个元素转换为一个 TextContent
            inventory_data = []
            for item in result.content:
                if item.type == "text":
                    inventory_data.append(json.loads(item.text))
            print(json.dumps(inventory_data[:5], indent=2, ensure_ascii=False))
            print()
            
            # 5. 测试 get_farm_map 工具 (截断显示)
            print("--- 调用 get_farm_map (Summary) ---")
            result = await session.call_tool("get_farm_map", arguments={})
            farm_map_text = result.content[0].text
            farm_map_data = json.loads(farm_map_text)
            print(f"Farm Type: {farm_map_data.get('type')}")
            print(f"Buildings: {len(farm_map_data.get('data', {}).get('buildings', []))}")
            print(f"Objects: {len(farm_map_data.get('data', {}).get('objects', []))}")
            print()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
