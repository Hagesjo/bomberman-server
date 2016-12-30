from coordinate import Coordinate
from directions import Direction
from random import shuffle
from bomb import Bomb
from box import Box
from fire import Fire
from random import sample
import config
import json
import logging

class WorldMap:
    def __init__(self, width, height, players):
        self.width = width
        self.height = height
        self.players = players
        self.walls = self.gen_walls()
        for player, spawn_point in zip(self.players, self.gen_spawn_points()):
            player.coord = spawn_point
            player.alive = True
        self.boxes = self.gen_boxes()
        self.bombs = {}
        self.fires = {}
        self.types = {
            Bomb : self.bombs,
            Fire : self.fires,
            Box : self.boxes
        } # Need better variable name

    def gen_spawn_points(self):
        possible_spawns = [
            Coordinate(0,0),
            Coordinate(self.width - 1, 0),
            Coordinate(0, self.height - 1),
            Coordinate(self.width - 1, self.height - 1)
        ]
        # Comment out shuffle while developing
        # shuffle(possible_spawns)
        return possible_spawns

    def gen_walls(self):
        ret = []
        for x in range(1, self.width, 2):
            for y in range(1, self.height, 2):
                ret.append(Coordinate(x,y))
        return ret

    def gen_boxes(self):
        possible_box_coords = set()
        for x in range(self.width):
            for y in range(self.height):
                possible_box_coords.add(Coordinate(x,y))
        possible_box_coords -= set(self.walls)

        for player in self.players:
            for d in Direction.all():
                try:
                    possible_box_coords.remove(player.coord - (d.x, d.y))
                    possible_box_coords.remove(player.coord - (2 * d.x, 2 * d.y))
                except KeyError:
                    pass
        box_coords = sample(
            possible_box_coords,
            round(len(possible_box_coords) * config.BOX_DENSITY))
        return list(map(lambda coord: Box(coord), box_coords))

    def get_new_id(self, objtype):
        if self.types[objtype]:
            return max(self.types[objtype]) + 1
        else:
            return 0

    def add_new_fire(self, player, coord):
        new_id = self.get_new_id(Fire)
        fire_tiles = self.get_fire_tiles(coord, player.power)
        new_fire = Fire(new_id, player, fire_tiles)
        self.fires[new_id] = new_fire
        return new_fire

    def add_new_bomb(self, player):
        player.num_bombs -= 1
        new_id = self.get_new_id(Bomb)
        self.bombs[new_id] = Bomb(new_id, player)

    def remove_fire(self, fire):
        fire.owner.num_bombs += 1
        del(self.fires[fire.fire_id])

    def explode_bomb(self, bomb):
        fire = self.add_new_fire(bomb.owner, bomb.coord)
        del(self.bombs[bomb.bomb_id])
        return fire

    def get_fire_tiles(self, coord, power):
        fire_tiles = {coord}
        for d in [Direction.LEFT, Direction.RIGHT, Direction.UP, Direction.DOWN]:
            for i in range(1, power):
                current_coord = coord + (d.x * i, d.y * i)
                tile_type = self.get_tile_at(current_coord)
                if tile_type in ["empty", "player"]:
                    fire_tiles.add(current_coord)
                else:
                    break
        return fire_tiles

    def to_json(self):
        ret = {}
        ret["map"] = {}
        ret["map"]["width"] = self.width
        ret["map"]["height"] = self.height
        ret["map"]["walls"] = list(map(lambda c: self.coord_to_pos(c), self.walls))
        ret["players"] = []
        for player in self.players:
            ret["players"].append({
                "id" : player.p_id,
                "pos" : self.coord_to_pos(player.coord),
                "alive" : player.alive
                }
            )
        ret["fires"] = []
        for fire in self.fires.values():
            for coord in fire.coords:
                ret["fires"].append(self.coord_to_pos(coord))
        ret["bombs"] = []
        for bomb in self.bombs.values():
            ret["bombs"].append(self.coord_to_pos(bomb.coord))
        ret["boxes"] = []
        for box in self.boxes:
            ret["boxes"].append(self.coord_to_pos(box.coord))
        logging.info(ret)

        return json.dumps(ret)

    def to_ascii(self):
        asc_map = [[" " for x in range(self.width)] for y in range(self.height)] 
        # Walls
        for w_coord in self.walls:
            asc_map[w_coord.y][w_coord.x] = "|"
        # Players
        for i, p in enumerate(self.players):
            asc_map[p.coord.y][p.coord.x] = str(i)
        # Bombs
        for b in self.bombs.values():
            asc_map[b.coord.y][b.coord.x] = "b"
        # Fires
        for f in self.fires.values():
            for coord in f.coords:
                asc_map[coord.y][coord.x] = "f"
        # Boxes
        for b in self.boxes:
            asc_map[b.coord.y][b.coord.x] = "X"

        # Frame
        for row in asc_map:
            row.insert(0, "|")
            row.append("|")
        asc_map.insert(0, ["-"] * (self.width + 2))
        asc_map.append(["-"] * (self.width + 2))
        return '\n'.join([''.join(row) for row in asc_map])
            
    def pos_to_coord(self, pos):
        y = pos // self.width
        x = pos % self.width
        return Coordinate(x, y)

    def coord_to_pos(self, coord):
        return coord.y * self.width + coord.x

    def inside_map(self, coord):
        return 0 <= coord.x <= self.width - 1 and 0 <= coord.y <= self.height - 1

    def get_tile_at(self, coord):
        for p in self.players:
            if coord == p.coord:
                return "player"
        if coord in self.walls:
            return "wall"
        if coord in self.boxes:
            return "box"
        if self.inside_map(coord):
            return "empty"    
        else:
            return "wall"

    def can_move_to(self, coord, direction):
        return self.get_tile_at(coord) == "empty"
