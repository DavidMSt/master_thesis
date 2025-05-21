import numpy as np

from scioi_py_core.core.world import WorldObject, World, WorldObjectGroup
from scioi_py_core.core.obstacles import CuboidObstacle_3D
import scioi_py_core.core as core


class Floor(WorldObject):
    name = 'floor'
    object_type = 'floor'
    physics: core.physics.CuboidPhysics
    height = 0.10

    def __init__(self, world: World = None, size: list = None, position: list = None, *args, **kwargs):
        super().__init__(world=world, *args, **kwargs)

        self.collision.settings.collidable = False

        self.physics = core.physics.CuboidPhysics(size_x=size[0], size_y=size[1], size_z=self.height,
                                                  position=[position[0], position[1], -self.height / 2],
                                                  orientation=np.eye(3))

        self.configuration['x'] = position[0]
        self.configuration['y'] = position[1]
        self.configuration['z'] = -self.height / 2
        self.configuration['rot'] = np.eye(3)

    def _getParameters(self):
        params = {'dim_x': self.physics.bounding_objects['cuboid'].dimensions[0],
                  'dim_y': self.physics.bounding_objects['cuboid'].dimensions[1],
                  'dim_z': self.height,
                  'position': self.physics.bounding_objects['cuboid'].position
                  }
        return params

    def _updatePhysics(self, config, *args, **kwargs):
        pass


def generateFloor(world: World, size: list = None):
    # Case 1: World Size given
    if size is None:
        limits_x = world.spaces.configuration_space['x'].limits
        limits_y = world.spaces.configuration_space['y'].limits

        assert (limits_x is not None and limits_y is not None)
        size_x = limits_x[1] - limits_x[0]
        size_y = limits_y[1] - limits_y[0]
        position_x = (limits_x[1] + limits_x[0]) / 2
        position_y = (limits_y[1] + limits_y[0]) / 2
        floor = Floor(world=world, size=[size_x, size_y], position=[position_x, position_y])
        return
    elif size is not None:
        ...


class FloorTile(CuboidObstacle_3D):
    height = 0.01
    object_type = 'floor_tile'

    def __init__(self, position, size, *args, **kwargs):
        super().__init__(size_x=size[0], size_y=size[1], size_z=self.height,
                         position=[position[0], position[1], -self.height / 2], *args, **kwargs)

        self.configuration['pos']['x'] = position[0]
        self.configuration['pos']['y'] = position[1]
        self.configuration['pos']['z'] = -self.height / 2
        self.configuration['ori'] = np.eye(3)

        self.collision.settings.collidable = False


class TiledFloor(WorldObjectGroup):
    tiles: list
    tile_size: list

    def __init__(self, world, dimensions, tile_size, tile_number, *args, **kwargs):
        super().__init__(world=world, local_space=core.spaces.Space3D(), *args, **kwargs)

        min_x = dimensions['x'][0]
        min_y = dimensions['y'][0]
        max_x = dimensions['x'][1]
        max_y = dimensions['y'][1]

        x = self.local_space.hasMapping(self.world.space)

        pass

        self.tile_size = tile_size
        # Generate the tiles
        self.tiles = [[None] * tile_number[1] for _ in range(tile_number[0])]
        for x in range(0, tile_number[0]):
            for y in range(0, tile_number[1]):
                position_x = min_x + x * tile_size[0] + tile_size[0] / 2
                position_y = min_y + y * tile_size[0] + tile_size[0] / 2
                self.tiles[x][y] = FloorTile(group=self, position=[position_x, position_y], size=tile_size,
                                             name=f"FloorTile_{x}_{y}", )

        pass

    def getSample(self):
        sample = super().getSample()
        return sample

    # def _getParameters(self):
    #     params = {'tiles_x': len(self.tiles),
    #               'tiles_y': len(self.tiles[0]),
    #               'tile_size': self.tile_size}
    #     params['tiles'] = {}
    #
    #     for loop over the tiles to write them into the params
    #
    #     return params

    def _updatePhysics(self, config, *args, **kwargs):
        pass


def generateTileFloor(world: World, tiles=None, tile_size=None, origin: str = 'center'):
    '''
    Generates a tiled floor
    :param world:
    :param tiles:
    :param tile_size:
    :param origin:
    :return:
    '''
    # Case 1: World Size + Number of Tiles given
    if tile_size is None and tiles is not None and world.width is not None:
        size_x = world.width['pos']['x']
        size_y = world.width['pos']['y']

        tile_size_x = (size_x[1] - size_x[0]) / tiles[0]
        tile_size_y = (size_y[1] - size_y[0]) / tiles[1]

        floor = TiledFloor(world=world, dimensions={'x': size_x, 'y': size_y}, tile_size=[tile_size_x, tile_size_y],
                           tile_number=tiles)
        return floor

    # Case 2: Number of Tiles + Tile Size given
    elif tile_size is not None and tiles is not None:
        if isinstance(tile_size, (float, int)):
            tile_size = [tile_size, tile_size]

        length_x = tiles[0] * tile_size[0]
        length_y = tiles[1] * tile_size[1]

        if origin == 'center':
            dimension_x = [-length_x / 2, length_x / 2]
            dimension_y = [-length_y / 2, length_y / 2]
        elif origin == 'corner':
            dimension_x = [0, length_x]
            dimension_y = [0, length_y]
        else:
            raise Exception()

        world.setSize(x=dimension_x, y=dimension_y)
        floor = TiledFloor(world=world, dimensions={'x': dimension_x, 'y': dimension_y},
                           tile_size=[tile_size[0], tile_size[1]],
                           tile_number=tiles)
        return floor

    elif tile_size is not None and world.width is not None:
        if isinstance(tile_size, (float, int)):
            tile_size = [tile_size, tile_size]

        # # Check if the number of tiles is a whole number
        # assert ((world.size['pos']['x'][1] - world.size['pos']['x'][0]) % tile_size[0] == 0)
        # assert ((world.size['pos']['y'][1] - world.size['pos']['y'][0]) % tile_size[1] == 0)

        # Calculate the number of tiles
        tiles_x = int((world.width['pos']['x'][1] - world.width['pos']['x'][0]) / tile_size[0])
        tiles_y = int((world.width['pos']['y'][1] - world.width['pos']['y'][0]) / tile_size[1])

        # Generate the floor
        floor = TiledFloor(world=world, dimensions={'x': world.width['pos']['x'], 'y': world.width['pos']['y']},
                           tile_size=[tile_size[0], tile_size[1]], tile_number=[tiles_x, tiles_y])

        return floor

    else:
        raise Exception("Invalid Combination of Arguments")
