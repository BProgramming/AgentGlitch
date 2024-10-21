from Block import Block, BreakableBlock, MovingBlock, MovableBlock, Hazard, MovingHazard
from Player import Player
from Enemy import Enemy
from Trigger import Trigger, TriggerType


def build_level(level, sprite_master, image_master, objects_dict, player_audios, enemy_audios, win, controller, block_size=96):
    width = len(level[-1]) * block_size
    height = len(level) * block_size
    level_bounds = [(0, 0), (width, height)]
    player_start = (0, 0)

    blocks = []
    triggers = []
    enemies = []
    hazards = []
    for i in range(len(level)):
        for j in range(len(level[i])):
            element = str(level[i][j])
            if len(element) > 0 and objects_dict.get(element) is not None:
                entry = objects_dict[element]
                data = entry["data"]
                match entry["type"].upper():
                    case "PLAYER":
                        player_start = ((j * block_size), (i * block_size))
                    case "BLOCK":
                        if i > 0 and len(str(level[i - 1][j])) > 0 and objects_dict.get(str(level[i - 1][j])) is not None and objects_dict[str(level[i - 1][j])]["type"] in ["Block"]:
                            is_stacked = True
                        else:
                            is_stacked = False
                        blocks.append(Block(j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "BREAKABLEBLOCK":
                        if i > 0 and len(str(level[i - 1][j])) > 0 and objects_dict.get(str(level[i - 1][j])) is not None and objects_dict[str(level[i - 1][j])]["type"] in ["Block"]:
                            is_stacked = True
                        else:
                            is_stacked = False
                        blocks.append(BreakableBlock(j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVINGBLOCK":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        blocks.append(MovingBlock(j * block_size, i * block_size, level_bounds, block_size, block_size, image_master, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVABLEBLOCK":
                        is_stacked = False
                        blocks.append(MovableBlock(j * block_size, i * block_size, level_bounds, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "HAZARD":
                        hazards.append(Hazard(j * block_size, i * block_size, block_size, data["height"], image_master, controller.difficulty, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVINGHAZARD":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        blocks.append(MovingHazard(j * block_size, i * block_size, level_bounds, block_size, data["height"], image_master, controller.difficulty, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "ENEMY":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        enemies.append(Enemy(j * block_size, i * block_size, level_bounds, sprite_master, enemy_audios, controller.difficulty, path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"])))
                    case "TRIGGER":
                        triggers.append(Trigger(j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, win, controller, objects_dict, level_bounds, sprite_master, enemy_audios, image_master, block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=element))
                    case _:
                        pass

    player = Player(player_start[0], player_start[1], level_bounds, sprite_master, player_audios, controller.difficulty, sprite=controller.player_sprite_selected)

    for trigger in triggers:
        trigger.player = player
        trigger.triggers = triggers
        trigger.enemies = enemies
        trigger.blocks = blocks
        trigger.hazards = hazards

    return level_bounds, player, blocks, triggers, hazards, enemies

