import os
from mcp_servers.save_file import SaveFile
from mcp_servers.player_info import GameInfo
from mcp_servers.farm_info import get_farm_info

class StardewSaveParser:
    def __init__(self, save_path):
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save file not found at {save_path}")
        self.save_file = SaveFile(save_path)
        self.game_info = GameInfo(self.save_file)

    def get_player_status(self):
        info = self.game_info.get_info()
        return {
            "name": info.get("name"),
            "farmName": info.get("farmName"),
            "money": info.get("money"),
            "currentSeason": info.get("currentSeason"),
            "dayOfMonth": info.get("dayOfMonthForSaveGame"),
            "year": info.get("yearForSaveGame"),
            "farmingLevel": info.get("farmingLevel"),
            "miningLevel": info.get("miningLevel"),
            "combatLevel": info.get("combatLevel"),
            "foragingLevel": info.get("foragingLevel"),
            "fishingLevel": info.get("fishingLevel"),
        }

    def get_inventory(self):
        # Scan player inventory and chests
        player_node = self.save_file.getRoot().find("player")
        items = []

        # Player inventory
        items_node = player_node.find("items")
        if items_node is not None:
            for item in items_node.findall("Item"):
                name_node = item.find("name")
                if name_node is not None and name_node.text:
                    name = name_node.text
                    stack_node = item.find("Stack")
                    if stack_node is None:
                        stack_node = item.find("stack")
                    stack = int(stack_node.text) if stack_node is not None and stack_node.text else 1
                    items.append({"location": "Inventory", "name": name, "stack": stack})

        # Chests on Farm
        from mcp_servers.save_file import get_location
        try:
            farm = get_location(self.save_file.getRoot(), "Farm")
            objects_node = farm.find("objects")
            if objects_node is not None:
                for item in objects_node.iter("item"):
                    val = item.find("value").find("Object")
                    if val is not None and val.find("name").text == "Chest":
                        # This is a chest
                        chest_items = val.find("items")
                        if chest_items is not None:
                            for c_item in chest_items.iter("item"):
                                c_obj = c_item.find("Object")
                                if c_obj is not None:
                                    c_name = c_obj.find("name").text
                                    c_stack = int(c_obj.find("stack").text) if c_obj.find("stack") is not None else 1
                                    items.append({"location": "Farm Chest", "name": c_name, "stack": c_stack})
        except Exception:
            pass

        return items

    def get_social_info(self):
        info = self.game_info.get_info()
        return info.get("friendships", {})

    def get_farm_map(self):
        return get_farm_info(self.save_file)
