import os
import glob

from mcp.server.fastmcp import FastMCP
from mcp_servers.parser_utils import StardewSaveParser
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Stardew-Valley-Server")

# Helper to find the save file
def find_save_file():
    # 使用 .env 中的 STARDEW_SAVE_PATH，如果不存在则回退到本地 saves 目录
    save_dir = os.getenv("STARDEW_SAVE_PATH")
    # Looking for files that don't have an extension, which are typically the save files in SDV folders
    save_files = glob.glob(os.path.join(save_dir, "*"))
    # Filter out common non-save files if any
    save_files = [f for f in save_files if os.path.isfile(f) and not f.endswith(".xml")]
    if not save_files:
        # Try to find any file in saves/
        save_files = glob.glob(os.path.join(save_dir, "*"))
        if not save_files:
             raise FileNotFoundError("No save file found in saves/ directory")
    return save_files[0]

CACHED_SAVE_PATH = find_save_file()

@mcp.tool()
def get_player_status() -> dict:
    """Get the player's basic status, including name, money, and current date."""
    save_path = CACHED_SAVE_PATH
    parser = StardewSaveParser(save_path)
    return parser.get_player_status()

@mcp.tool()
def get_inventory() -> list:
    """Get a detailed list of items in the player's inventory and farm chests."""
    save_path = CACHED_SAVE_PATH
    parser = StardewSaveParser(save_path)
    return parser.get_inventory()

@mcp.tool()
def get_social_info() -> dict:
    """Get the player's friendship levels with NPCs."""
    save_path = CACHED_SAVE_PATH
    parser = StardewSaveParser(save_path)
    return parser.get_social_info()

@mcp.tool()
def get_farm_map() -> dict:
    """Get information about the farm layout, including buildings and crops."""
    save_path = CACHED_SAVE_PATH
    parser = StardewSaveParser(save_path)
    # The farm map can be large, returning it as a dict
    return parser.get_farm_map()

if __name__ == "__main__":
    mcp.run()