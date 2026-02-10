from collections import namedtuple
import sdv_utils as validate
from save_file import get_location

ns = "{http://www.w3.org/2001/XMLSchema-instance}"

map_types = [
    "Default", "Fishing", "Foraging", "Mining", "Combat", "FourCorners", "Island",
]

sprite = namedtuple(
    "Sprite",
    ["name", "x", "y", "w", "h", "index", "type", "growth", "flipped", "orientation"],
)


def get_partner(node):
    try:
        spouse_node = node.find("spouse")
        if spouse_node is not None and spouse_node.text:
            partner = spouse_node.text
            if partner in validate.marriage_candidates:
                return partner
    except AttributeError:
        pass
    return None


def get_farm_info(save_file_obj):
    farm = {}
    root = save_file_obj.getRoot()

    # Farm Objects
    s = []
    try:
        farm_location = get_location(root, "Farm")
    except AttributeError:
        return {"type": "Unknown", "data": {}, "spouse": None}

    objects_node = farm_location.find("objects")
    if objects_node is not None:
        for item in objects_node.iter("item"):
            try:
                obj = item.find("value").find("Object")
                name = obj.find("name").text
                x = int(item.find("key").find("Vector2").find("X").text)
                y = int(item.find("key").find("Vector2").find("Y").text)
                i = int(obj.find("parentSheetIndex").text)
                t = obj.find("type").text if obj.find("type") is not None else ""
                
                f = obj.find("flipped").text == "true" if obj.find("flipped") is not None else False
                
                if "Fence" in name or name == "Gate":
                    t = int(obj.find("whichType").text)
                    growth = (name == "Gate")
                    name = "Fence"
                else:
                    growth = False
                
                s.append(sprite(name, x, y, 0, 0, i, t, growth, f, None))
            except:
                continue

    farm["objects"] = s

    # Terrain Features
    tf = []
    crops = []
    terrain_node = farm_location.find("terrainFeatures")
    if terrain_node is not None:
        for item in terrain_node.iter("item"):
            try:
                name = item.find("value").find("TerrainFeature").get(ns + "type")
                x = int(item.find("key").find("Vector2").find("X").text)
                y = int(item.find("key").find("Vector2").find("Y").text)
                
                # Simplified extraction for demo
                tf.append(sprite(name, x, y, 1, 1, None, None, None, False, None))
                
                # Check for crops in HoeDirt
                if name == "HoeDirt":
                    crop = item.find("value").find("TerrainFeature").find("crop")
                    if crop is not None:
                        phase = int(crop.find("currentPhase").text)
                        tf.append(sprite("Crop", x, y, 1, 1, None, None, phase, False, None))
            except:
                continue

    farm["terrainFeatures"] = tf

    # Buildings
    buildings = []
    buildings_node = farm_location.find("buildings")
    if buildings_node is not None:
        for item in buildings_node.iter("Building"):
            try:
                x = int(item.find("tileX").text)
                y = int(item.find("tileY").text)
                w = int(item.find("tilesWide").text)
                h = int(item.find("tilesHigh").text)
                t = item.find("buildingType").text
                buildings.append(sprite("Building", x, y, w, h, None, t, None, False, None))
            except:
                continue
    farm["buildings"] = buildings

    try:
        map_type_idx = int(root.find("whichFarm").text)
    except:
        map_type_idx = 0

    player_node = root.find("player")
    spouse = get_partner(player_node) if player_node is not None else None
    
    return {
        "type": map_types[map_type_idx] if map_type_idx < len(map_types) else "Unknown",
        "data": farm,
        "spouse": spouse
    }
