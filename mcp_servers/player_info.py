import json
import sdv_utils as validate
from save_file import get_location

ns = "{http://www.w3.org/2001/XMLSchema-instance}"

animal_habitable_buildings = ["Coop", "Barn", "SlimeHutch"]

playerTags = [
    "name",
    "UniqueMultiplayerID",
    "isMale",
    "farmName",
    "favoriteThing",
    "catPerson",
    "deepestMineLevel",
    "farmingLevel",
    "miningLevel",
    "combatLevel",
    "foragingLevel",
    "fishingLevel",
    "professions",
    "maxHealth",
    "maxStamina",
    "maxItems",
    "money",
    "totalMoneyEarned",
    "millisecondsPlayed",
    "friendships",
    "shirt",
    "hair",
    "skin",
    "accessory",
    "facialHair",
    "hairstyleColor",
    "pantsColor",
    "newEyeColor",
    "dayOfMonthForSaveGame",
    "seasonForSaveGame",
    "yearForSaveGame",
]

professions = [
    "Rancher", "Tiller", "Coopmaster", "Shepherd", "Artisan", "Agriculturist",
    "Fisher", "Trapper", "Angler", "Pirate", "Mariner", "Luremaster",
    "Forester", "Gatherer", "Lumberjack", "Tapper", "Botanist", "Tracker",
    "Miner", "Geologist", "Blacksmith", "Prospector", "Excavator", "Gemologist",
    "Fighter", "Scout", "Brute", "Defender", "Acrobat", "Desperado",
]

petTypes = ["Cat", "Dog"]
petLocations = ["Farm", "FarmHouse"]
childType = ["Child"]
childLocation = ["Farm", "FarmHouse"]


def str_to_bool(x):
    return x.lower() == "true"


def get_animals(farm, get_npcs):
    animals = {}
    buildings = farm.find("buildings")
    if buildings is None:
        return animals
    for building in buildings.iter("Building"):
        buildingtype = building.get(ns + "type")
        name_node = building.find("buildingType")
        if name_node is None:
            continue
        name = name_node.text
        if buildingtype in animal_habitable_buildings:
            indoors = building.find("indoors")
            if indoors is None: continue
            animals_node = indoors.find("animals")
            if animals_node is None: continue
            for animal_item in animals_node.iter("item"):
                animal_val = animal_item.find("value").find("FarmAnimal")
                if animal_val is None: continue
                an = animal_val.find("name").text
                aa = int(animal_val.find("age").text)
                at = animal_val.find("type").text
                ah = int(animal_val.find("happiness").text)
                ahx = int(animal_val.find("homeLocation").find("X").text)
                ahy = int(animal_val.find("homeLocation").find("Y").text)
                animaltuple = (an, aa, ah, ahx, ahy, name)
                if at not in animals:
                    animals[at] = []
                animals[at].append(animaltuple)
    horse = get_npcs(["Farm"], ["Horse"])
    if horse:
        animals["horse"] = horse[0].find("name").text
    return animals


class GameInfo:
    def __init__(self, save_file_obj):
        self.save_file = save_file_obj
        self.root = self.save_file.getRoot()
        self.info = {}
        self.get_players()
        self.get_info()

    def get_info(self):
        if not self.info:
            self.info = self.player.get_info()
            self.info["uniqueIDForThisGame"] = int(self.root.find("uniqueIDForThisGame").text)
            self.current_season = self.root.find("currentSeason").text
            self.info["currentSeason"] = self.current_season

            try:
                npcs = self._get_npcs(petLocations, petTypes)
                if npcs:
                    self.info["petName"] = npcs[0].find("name").text
            except (IndexError, AttributeError):
                pass

            self.info["animals"] = self.get_animals_data()

            if len(self.farmhands) > 0:
                self.info["farmhands"] = [fh.get_info() for fh in self.farmhands]

        return self.info

    def get_children(self):
        if not hasattr(self, "children"):
            self.children = self._get_npcs(childLocation, childType)
        return self.children

    def get_animals_data(self):
        if not hasattr(self, "_animals"):
            try:
                farm = get_location(self.root, "Farm")
                self._animals = get_animals(farm, self._get_npcs)
            except AttributeError:
                self._animals = {}
        return self._animals

    def _get_npcs(self, loc, types):
        npcs = []
        locations = self.root.find("locations")
        if locations is None: return npcs
        for location in locations.iter("GameLocation"):
            if location.get(ns + "type") in loc:
                characters = location.find("characters")
                if characters is not None:
                    for npc in characters.iter("NPC"):
                        if npc.get(ns + "type") in types:
                            npcs.append(npc)
        return npcs

    def v1_3(self):
        if not hasattr(self, "_v1_3"):
            try:
                node = self.root.find("hasApplied1_3_UpdateChanges")
                self._v1_3 = str_to_bool(node.text) if node is not None else False
            except:
                self._v1_3 = False
        return self._v1_3

    def get_players(self):
        if not hasattr(self, "player"):
            self.farmhands = []
            if self.v1_3():
                player_node = self.root.find("player")
                friendships = self.root.find("farmerFriendships")
                self.player = Player(player_node, self.get_children(), True, friendships)
                for fh in self.root.iter("farmhand"):
                    if fh.find("name") is not None and fh.find("name").text:
                        self.farmhands.append(Player(fh, self.get_children(), True, friendships))
            else:
                self.player = Player(self.root, self.get_children(), False)
        return [self.player] + self.farmhands


class Player:
    def __init__(self, node, children, v1_3, farmer_friendships=None):
        self.node = node
        self.player_node = self.node if v1_3 else self.node.find("player")
        self.v1_3 = v1_3
        self.children = children
        self.farmer_friendships = farmer_friendships
        self.info = {}
        
        self.player_tags = list(playerTags)
        if self.v1_3:
            try:
                idx = self.player_tags.index("friendships")
                self.player_tags[idx] = "friendshipData"
            except ValueError:
                pass

    def get_info(self):
        if not self.info:
            for tag in self.player_tags:
                node = self.player_node.find(tag)
                if node is not None:
                    if node.text is not None:
                        self.info[tag] = node.text
                    else:
                        if tag == "professions":
                            self.info["professions"] = get_professions(self.player_node)
                        elif tag in ["friendships", "friendshipData"]:
                            self.info["friendships"] = get_friendships(self.player_node, self.v1_3)
                        elif tag in ["hairstyleColor", "pantsColor", "newEyeColor"]:
                            try:
                                self.info[tag] = [int(node.find(c).text) for c in "RGBA" if node.find(c) is not None]
                            except:
                                pass
            self.info["stats"] = get_stats(self.node)
        return self.info


def get_professions(node):
    profs_node = node.find("professions")
    if profs_node is None: return []
    res = []
    for p in profs_node.iter("int"):
        val = int(p.text)
        if val < len(professions):
            res.append(professions[val])
    return res


def get_friendships(node, v1_3):
    fship = node.find("friendshipData" if v1_3 else "friendships")
    if fship is None: return {}
    res = {}
    for item in fship:
        try:
            name = item.find("key").find("string").text
            if name in validate.giftable_npcs:
                if v1_3:
                    rating = int(item.find("value").find("Friendship").find("Points").text)
                else:
                    rating = int(item.find("value").find("ArrayOfInt").find("int").text)
                res[name] = rating
        except:
            continue
    return res


def get_stats(node):
    stats = {}
    stats_node = node.find("stats")
    if stats_node is None: return stats
    for stat in stats_node:
        tag = stat.tag[0].upper() + stat.tag[1:]
        if stat.text is not None:
            try:
                stats[tag] = int(stat.text)
            except:
                stats[tag] = stat.text
        elif tag == "SpecificMonstersKilled":
            monsters = {}
            for item in stat.iter("item"):
                try:
                    m_name = item.find("key").find("string").text
                    count = int(item.find("value").find("int").text)
                    monsters[m_name] = count
                except:
                    continue
            stats[tag] = monsters
    return stats
