# Copyright Allen Institute for Artificial Intelligence 2017
import atexit
from collections import deque, defaultdict
from itertools import product
import io
import json
import logging
import math
import random
import shlex
import signal
import subprocess
import threading
import os
import platform
from queue import Queue
import zipfile

import numpy as np

import ai2thor.downloader
import ai2thor.server
from ai2thor.server import queue_get

logger = logging.getLogger(__name__)

BUILDS = dict(
    Linux={
        'url':'https://s3-us-west-2.amazonaws.com/ai2-thor/builds/thor-201711131440-Linux64.zip',
        'sha256':'c9b69cdc68ab22320680b58b016649b0cda9f995d69af6d9fc60981afdb56c85'
    },
    Darwin={
        'url':'https://s3-us-west-2.amazonaws.com/ai2-thor/builds/thor-201711131440-OSXIntel64.zip',
        'sha256':'fdb31d8fdefea43883ce77f0b516727e849525f46a8cf625eb77f224f7233869'
    },
)

RECEPTACLE_OBJECTS = {
    'Box': {'Candle',
            'CellPhone',
            'Cloth',
            'CreditCard',
            'Dirt',
            'KeyChain',
            'Newspaper',
            'ScrubBrush',
            'SoapBar',
            'SoapBottle',
            'ToiletPaper'},
    'Cabinet': {'Bowl',
                'BowlDirty',
                'Box',
                'Bread',
                'BreadSliced',
                'ButterKnife',
                'Candle',
                'CellPhone',
                'CoffeeMachine',
                'Container',
                'ContainerFull',
                'CreditCard',
                'Cup',
                'Fork',
                'KeyChain',
                'Knife',
                'Laptop',
                'Mug',
                'Newspaper',
                'Pan',
                'Plate',
                'Plunger',
                'Pot',
                'Potato',
                'Sandwich',
                'ScrubBrush',
                'SoapBar',
                'SoapBottle',
                'Spoon',
                'SprayBottle',
                'Statue',
                'TissueBox',
                'Toaster',
                'ToiletPaper',
                'WateringCan'},
    'CoffeeMachine': {'MugFilled', 'Mug'},
    'CounterTop': {'Apple',
                   'AppleSlice',
                   'Bowl',
                   'BowlDirty',
                   'BowlFilled',
                   'Box',
                   'Bread',
                   'BreadSliced',
                   'ButterKnife',
                   'Candle',
                   'CellPhone',
                   'CoffeeMachine',
                   'Container',
                   'ContainerFull',
                   'CreditCard',
                   'Cup',
                   'Egg',
                   'EggFried',
                   'EggShell',
                   'Fork',
                   'HousePlant',
                   'KeyChain',
                   'Knife',
                   'Laptop',
                   'Lettuce',
                   'LettuceSliced',
                   'Microwave',
                   'Mug',
                   'MugFilled',
                   'Newspaper',
                   'Omelette',
                   'Pan',
                   'Plate',
                   'Plunger',
                   'Pot',
                   'Potato',
                   'PotatoSliced',
                   'RemoteControl',
                   'Sandwich',
                   'ScrubBrush',
                   'SoapBar',
                   'SoapBottle',
                   'Spoon',
                   'SprayBottle',
                   'Statue',
                   'Television',
                   'TissueBox',
                   'Toaster',
                   'ToiletPaper',
                   'Tomato',
                   'TomatoSliced',
                   'WateringCan'},
    'Fridge': {'Apple',
               'AppleSlice',
               'Bowl',
               'BowlDirty',
               'BowlFilled',
               'Bread',
               'BreadSliced',
               'Container',
               'ContainerFull',
               'Cup',
               'Egg',
               'EggFried',
               'EggShell',
               'Lettuce',
               'LettuceSliced',
               'Mug',
               'MugFilled',
               'Omelette',
               'Pan',
               'Plate',
               'Pot',
               'Potato',
               'PotatoSliced',
               'Sandwich',
               'Tomato',
               'TomatoSliced'},
    'GarbageCan': {'Apple',
                   'AppleSlice',
                   'Box',
                   'Bread',
                   'BreadSliced',
                   'Candle',
                   'CellPhone',
                   'CreditCard',
                   'Egg',
                   'EggFried',
                   'EggShell',
                   'LettuceSliced',
                   'Newspaper',
                   'Omelette',
                   'Plunger',
                   'Potato',
                   'PotatoSliced',
                   'Sandwich',
                   'ScrubBrush',
                   'SoapBar',
                   'SoapBottle',
                   'SprayBottle',
                   'Statue',
                   'ToiletPaper',
                   'Tomato',
                   'TomatoSliced'},
    'Microwave': {'Bowl',
                  'BowlDirty',
                  'BowlFilled',
                  'Bread',
                  'BreadSliced',
                  'Container',
                  'ContainerFull',
                  'Cup',
                  'Egg',
                  'EggFried',
                  'Mug',
                  'MugFilled',
                  'Omelette',
                  'Plate',
                  'Potato',
                  'PotatoSliced',
                  'Sandwich'},
    'PaintingHanger': {'Painting'},
    'Pan': {'Apple',
            'AppleSlice',
            'EggFried',
            'Lettuce',
            'LettuceSliced',
            'Omelette',
            'Potato',
            'PotatoSliced',
            'Tomato',
            'TomatoSliced'},
    'Pot': {'Apple',
            'AppleSlice',
            'EggFried',
            'Lettuce',
            'LettuceSliced',
            'Omelette',
            'Potato',
            'PotatoSliced',
            'Tomato',
            'TomatoSliced'},
    'Sink': {'Apple',
             'AppleSlice',
             'Bowl',
             'BowlDirty',
             'BowlFilled',
             'ButterKnife',
             'Container',
             'ContainerFull',
             'Cup',
             'Egg',
             'EggFried',
             'EggShell',
             'Fork',
             'Knife',
             'Lettuce',
             'LettuceSliced',
             'Mug',
             'MugFilled',
             'Omelette',
             'Pan',
             'Plate',
             'Pot',
             'Potato',
             'PotatoSliced',
             'Sandwich',
             'ScrubBrush',
             'SoapBottle',
             'Spoon',
             'Tomato',
             'TomatoSliced',
             'WateringCan'},
    'StoveBurner': {'Omelette', 'Pot', 'Pan', 'EggFried'},
    'TableTop': {'Apple',
                 'AppleSlice',
                 'Bowl',
                 'BowlDirty',
                 'BowlFilled',
                 'Box',
                 'Bread',
                 'BreadSliced',
                 'ButterKnife',
                 'Candle',
                 'CellPhone',
                 'CoffeeMachine',
                 'Container',
                 'ContainerFull',
                 'CreditCard',
                 'Cup',
                 'Egg',
                 'EggFried',
                 'EggShell',
                 'Fork',
                 'HousePlant',
                 'KeyChain',
                 'Knife',
                 'Laptop',
                 'Lettuce',
                 'LettuceSliced',
                 'Microwave',
                 'Mug',
                 'MugFilled',
                 'Newspaper',
                 'Omelette',
                 'Pan',
                 'Plate',
                 'Plunger',
                 'Pot',
                 'Potato',
                 'PotatoSliced',
                 'RemoteControl',
                 'Sandwich',
                 'ScrubBrush',
                 'SoapBar',
                 'SoapBottle',
                 'Spoon',
                 'SprayBottle',
                 'Statue',
                 'Television',
                 'TissueBox',
                 'Toaster',
                 'ToiletPaper',
                 'Tomato',
                 'TomatoSliced',
                 'WateringCan'},
    'ToiletPaperHanger': {'ToiletPaper'},
    'TowelHolder': {'Cloth'}}

def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError as e:
        return False
    return True

# python2.7 compatible makedirs
def makedirs(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def distance(point1, point2):
    x_diff = (point1['x'] - point2['x']) ** 2
    z_diff = (point1['z'] - point2['z']) ** 2
    return math.sqrt(x_diff + z_diff)


def key_for_point(x, z):
    return "%0.1f %0.1f" % (x, z)

class Controller(object):

    def __init__(self):
        self.request_queue = Queue(maxsize=1)
        self.response_queue = Queue(maxsize=1)
        self.receptacle_nearest_pivot_points = {}
        self.server = None
        self.unity_pid = None

    def reset(self, scene_name=None):
        self.response_queue.put_nowait(dict(action='Reset', sceneName=scene_name, sequenceId=0))
        self.last_event = queue_get(self.request_queue)

        return self.last_event

    def random_initialize(
            self,
            random_seed=None,
            randomize_open=False,
            unique_object_types=False,
            exclude_receptacle_object_pairs=[]):

        receptacle_objects = []

        for r, object_types in RECEPTACLE_OBJECTS:
            receptacle_objects.append(
                dict(receptacleObjectType=r, itemObjectTypes=list(object_types))
            )
        if random_seed is None:
            random_seed = random.randint(0, 2**32)

        exclude_object_ids = []

        for o in self.last_event.metadata['objects']:
            pp = self.receptacle_nearest_pivot_points
            # don't put things in pot or pan currently
            if (pp and o['receptacle'] \
                and pp[o['objectId']].keys()) \
                or o['objectType'] in ['Pot', 'Pan']:

                #print("no visible pivots for receptacle %s" % o['objectId'])
                exclude_object_ids.append(o['objectId'])

        return self.step(dict(
            action='RandomInitialize',
            receptacleObjects=receptacle_objects,
            randomizeOpen=randomize_open,
            uniquePickupableObjectTypes=unique_object_types,
            excludeObjectIds=exclude_object_ids,
            excludeReceptacleObjectPairs=exclude_receptacle_object_pairs,
            randomSeed=random_seed))

    def step(self, action, raise_for_failure=False):
        if not self._check_action(action):
            new_event = ai2thor.server.Event(
                json.loads(json.dumps(self.last_event.metadata)),
                self.last_event.frame_id,
                self.last_event.frame)

            new_event.metadata['lastActionSuccess'] = False
            self.last_event = new_event
            return new_event
        assert self.request_queue.empty()

        self.response_queue.put_nowait(action)
        self.last_event = queue_get(self.request_queue)
        print(self.last_event.metadata['errorMessage'])
        if raise_for_failure:
            assert self.last_event.metadata['lastActionSuccess']

        return self.last_event

    def unity_command(self, width, height):

        command = self.executable_path()
        command += (" -screen-width %s -screen-height %s" % (width, height))
        return shlex.split(command)

    def _start_thread(self, env, width, height, port=0, start_unity=True):
        # get environment variables

        if not start_unity:
            self.server.client_token = None

        _, port = self.server.wsgi_server.socket.getsockname()
        env['AI2THOR_PORT'] = str(port)
        env['AI2THOR_CLIENT_TOKEN'] = self.server.client_token
        env['AI2THOR_CLIENT_TOKEN'] = self.server.client_token
        # env['AI2THOR_SERVER_SIDE_SCREENSHOT'] = 'True'

        # print("Viewer: http://%s:%s/viewer" % (host, port))

        # launch simulator
        if start_unity:
            proc = subprocess.Popen(self.unity_command(width, height), env=env)
            self.unity_pid = proc.pid

            print("launched pid %s" % self.unity_pid)
            atexit.register(lambda: os.kill(self.unity_pid, signal.SIGKILL))

        self.server.start()

    def base_dir(self):
        return os.path.join(os.path.expanduser('~'), '.ai2thor')

    def build_name(self):
        return os.path.splitext(os.path.basename(BUILDS[platform.system()]['url']))[0]

    def executable_path(self):

        target_arch = platform.system()

        if target_arch == 'Linux':
            return os.path.join(self.base_dir(), 'releases', self.build_name(), self.build_name())
        elif target_arch == 'Darwin':
            return os.path.join(self.base_dir(), 'releases', self.build_name(),  self.build_name() + ".app", "Contents/MacOS", self.build_name())
            # we can lose the executable permission when unzipping a build
        else:
            raise Exception('unable to handle target arch %s' % target_arch)

    def download_binary(self):

        if platform.architecture()[0] != '64bit':
            raise Exception("Only 64bit currently supported")

        url = BUILDS[platform.system()]['url']
        releases_dir = os.path.join(self.base_dir(), 'releases')
        tmp_dir = os.path.join(self.base_dir(), 'tmp')
        makedirs(releases_dir)
        makedirs(tmp_dir)

        if not os.path.isfile(self.executable_path()):
            zip_data = ai2thor.downloader.download(url, self.build_name(), BUILDS[platform.system()]['sha256'])
            z = zipfile.ZipFile(io.BytesIO(zip_data))
            # use tmpdir instead or a random number
            extract_dir = os.path.join(tmp_dir, self.build_name())
            logger.debug("Extracting zipfile %s" % os.path.basename(url))
            z.extractall(extract_dir)
            os.rename(extract_dir, os.path.join(releases_dir, self.build_name()))
            os.chmod(self.executable_path(), 0o755)
        else:
            logger.debug("%s exists - skipping download" % self.executable_path())

    def start(
            self,
            port=0,
            start_unity=True,
            player_screen_width=300,
            player_screen_height=300,
            x_display="0.0"):

        env = os.environ.copy()

        if platform.system() == 'Linux':
            env['DISPLAY'] = ':' + x_display

        self.download_binary()

        self.server = ai2thor.server.Server(
            self.request_queue,
            self.response_queue,
            port)

        self.server_thread = threading.Thread(
            target=self._start_thread,
            args=(env, player_screen_width, player_screen_height, port, start_unity))
        self.server_thread.daemon = True
        self.server_thread.start()

        # receive the first request
        self.last_event = queue_get(self.request_queue)

        return self.last_event

    def stop(self):
        self.stop_unity()
        self.server.wsgi_server.shutdown()

    def stop_unity(self):
        if self.unity_pid and process_alive(self.unity_pid):
            os.kill(self.unity_pid, signal.SIGKILL)

    def _check_action(self, action):
        return True

class BFSSearchPoint:
    def __init__(self, start_position, move_vector, heading_angle=0.0, horizon_angle=0.0):
        self.start_position = start_position
        self.move_vector = defaultdict(lambda: 0.0)
        self.move_vector.update(move_vector)
        self.heading_angle = heading_angle
        self.horizon_angle = horizon_angle

    def target_point(self):
        x = self.start_position['x'] + self.move_vector['x']
        z = self.start_position['z'] + self.move_vector['z']
        return dict(x=x, z=z)

class BFSController(Controller):

    def __init__(self):
        super(BFSController, self).__init__()
        self.rotations = [0, 90, 180, 270]
        self.horizons = [330, 0, 30]
        self.move_magnitude = 0.25
        self.allow_enqueue = True
        self.queue = deque()
        self.seen_points = []
        self.grid_points = []

    def visualize_points(self, scene_name, wait_key=10):
        import cv2
        points = set()
        xs = []
        zs = []

            # Follow the file as it grows
        for point in self.grid_points:
            xs.append(point['x'])
            zs.append(point['z'])
            points.add(str(point['x']) + "," + str(point['z']))

        image_width = 470
        image_height = 530
        image = np.zeros((image_height, image_width, 3), np.uint8)
        if not xs:
            return

        min_x = min(xs)  - 1
        max_x = max(xs) + 1
        min_z = min(zs)  - 1
        max_z = max(zs) + 1

        for p in list(points):
            x, z = map(float, p.split(','))
            circle_x = round(((x - min_x)/float(max_x - min_x)) * image_width)
            z = (max_z - z) + min_z
            circle_y = round(((z - min_z)/float(max_z - min_z)) * image_height)
            cv2.circle(image, (circle_x, circle_y), 5, (0, 255, 0), -1)

        cv2.imshow(scene_name, image)
        cv2.waitKey(wait_key)


    def has_islands(self):
        queue = []
        seen_points = set()
        mag = self.move_magnitude
        def enqueue_island_points(p):
            if json.dumps(p) in seen_points:
                return
            queue.append(dict(z=p['z'] + mag, x=p['x']))
            queue.append(dict(z=p['z'] - mag, x=p['x']))
            queue.append(dict(z=p['z'], x=p['x'] + mag))
            queue.append(dict(z=p['z'], x=p['x'] - mag))
            seen_points.add(json.dumps(p))


        enqueue_island_points(self.grid_points[0])

        while queue:
            point_to_find = queue.pop()
            for p in self.grid_points:
                dist = math.sqrt(
                    ((point_to_find['x'] - p['x']) ** 2) + \
                    ((point_to_find['z'] - p['z']) ** 2))

                if dist < 0.05:
                    enqueue_island_points(p)

        return len(seen_points) != len(self.grid_points)


    def enqueue_point(self, point):

        # ensure there are no points near the new point
        threshold = self.move_magnitude/5.0
        if not any(map(lambda p: distance(p, point.target_point()) < threshold, self.seen_points)):
            self.seen_points.append(point.target_point())
            self.queue.append(point)

    def enqueue_points(self, agent_position):
        if not self.allow_enqueue:
            return
        self.enqueue_point(BFSSearchPoint(agent_position, dict(x=-1 * self.move_magnitude)))
        self.enqueue_point(BFSSearchPoint(agent_position, dict(x=self.move_magnitude)))
        self.enqueue_point(BFSSearchPoint(agent_position, dict(z=-1 * self.move_magnitude)))
        self.enqueue_point(BFSSearchPoint(agent_position, dict(z=1 * self.move_magnitude)))

    def search_all_closed(self, scene_name):
        self.allow_enqueue = True
        self.queue = deque()
        self.seen_points = []
        self.grid_points = []
        event = self.reset(scene_name)
        event = self.step(dict(action='Initialize', gridSize=0.25))
        self.enqueue_points(event.metadata['agent']['position'])
        while self.queue:
            self.queue_step()
            self.visualize_points(scene_name)

    def start_search(
            self,
            scene_name,
            random_seed,
            full_grid,
            current_receptacle_object_pairs,
            randomize=True):

        self.seen_points = []
        self.queue = deque()
        self.grid_points = []

        # we only search a pre-defined grid with all the cabinets/fridges closed
        # then keep the points that can still be reached
        self.allow_enqueue = True

        for gp in full_grid:
            self.enqueue_points(gp)

        self.allow_enqueue = False

        self.reset(scene_name)
        receptacle_object_pairs = []
        for op in current_receptacle_object_pairs:
            object_id, receptacle_object_id = op.split('||')
            receptacle_object_pairs.append(
                dict(receptacleObjectId=receptacle_object_id,
                     objectId=object_id))


        if randomize:
            self.random_initialize(
                random_seed=random_seed,
                unique_object_types=True,
                exclude_receptacle_object_pairs=receptacle_object_pairs)

        self.initialize_scene()
        while self.queue:
            self.queue_step()
            self.visualize_points(scene_name)

        self.prune_points()
        self.visualize_points(scene_name)

    # get rid of unreachable points
    def prune_points(self):
        final_grid_points = set()

        for gp in self.grid_points:
            final_grid_points.add(key_for_point(gp['x'], gp['z']))

        pruned_grid_points = []

        for gp in self.grid_points:
            found = False
            for x in [1, -1]:
                found |= key_for_point(gp['x'] +\
                    (self.move_magnitude * x), gp['z']) in final_grid_points

            for z in [1, -1]:
                found |= key_for_point(
                    gp['x'],
                    (self.move_magnitude * z) + gp['z']) in final_grid_points

            if found:
                pruned_grid_points.append(gp)

        self.grid_points = pruned_grid_points

    def is_object_visible(self, object_id):
        for o in self.last_event.metadata['objects']:
            if o['objectId'] == object_id and o['visible']:
                return True
        return False

    def find_visible_receptacles(self):
        receptacle_points = []
        receptacle_pivot_points = []

        # pickup all objects
        visibility_object_id = None
        visibility_object_types = ['Mug', 'CellPhone']
        for o in self.last_event.metadata['objects']:
            if o['pickupable']:
                self.step(action=dict(
                    action='PickupObject',
                    objectId=o['objectId'],
                    forceVisible=True))
            if visibility_object_id is None and o['objectType'] in visibility_object_types:
                visibility_object_id = o['objectId']

        for p in self.grid_points:
            self.step(dict(action='Teleport', x=p['x'], y=p['y'], z=p['z']), raise_for_failure=True)

            for r, h in product(self.rotations, self.horizons):
                event = self.step(
                    dict(action='RotateLook', rotation=r, horizon=h),
                    raise_for_failure=True)
                for j in event.metadata['objects']:
                    if j['receptacle'] and j['visible']:
                        receptacle_points.append(dict(
                            distance=j['distance'],
                            pivotId=0,
                            receptacleObjectId=j['objectId'],
                            searchNode=dict(
                                horizon=h,
                                rotation=r,
                                openReceptacle=False,
                                pivotId=0,
                                receptacleObjectId='',
                                x=p['x'],
                                y=p['y'],
                                z=p['z'])))

                        if j['openable']:
                            self.step(action=dict(
                                action='OpenObject',
                                forceVisible=True,
                                objectId=j['objectId']),
                                      raise_for_failure=True)
                        for pivot_id in range(j['receptacleCount']):
                            self.step(
                                action=dict(
                                    action='Replace',
                                    forceVisible=True,
                                    receptacleObjectId=j['objectId'],
                                    objectId=visibility_object_id,
                                    pivot=pivot_id, raise_for_failure=True))
                            if self.is_object_visible(visibility_object_id):
                                receptacle_pivot_points.append(dict(
                                    distance=o['distance'],
                                    pivotId=pivot_id,
                                    receptacleObjectId=j['objectId'],
                                    searchNode=dict(
                                        horizon=h,
                                        rotation=r,
                                        openReceptacle=j['openable'],
                                        pivotId=pivot_id,
                                        receptacleObjectId=j['objectId'],
                                        x=p['x'],
                                        y=p['y'],
                                        z=p['z'])))


                        if j['openable']:
                            self.step(action=dict(
                                action='CloseObject',
                                forceVisible=True,
                                objectId=j['objectId']),
                                      raise_for_failure=True)

        return receptacle_pivot_points, receptacle_points


    def find_visible_objects(self):
        seen_target_objects = {}
        for p in self.grid_points:
            self.step(dict(action='Teleport', x=p['x'], y=p['y'], z=p['z']), raise_for_failure=True)


            for r in [0, 90, 180, 270]:
                for h in [330, 0, 30, 60]:
                    event = self.step(dict(
                        action='RotateLook',
                        rotation=r,
                        horizon=h), raise_for_failure=True)

                    object_receptacle = dict()
                    for j in event.metadata['objects']:
                        if j['receptacle']:
                            for pso in j['pivotSimObjs']:
                                object_receptacle[pso['objectId']] = j
                    for o in filter(
                            lambda x: x['visible'] and x['pickupable'],
                            event.metadata['objects']):

                        if o['objectId'] in object_receptacle \
                            and object_receptacle[o['objectId']]['openable'] \
                            and not object_receptacle[o['objectId']]['isopen']:
                            continue

                        if o['objectId'] not in seen_target_objects \
                            or o['distance'] < seen_target_objects[o['objectId']]['distance']:
                            seen_target_objects[o['objectId']] = dict(
                                distance=o['distance'],
                                agent=event.metadata['agent'])

        #for o in filter(lambda x: x in seen_target_objects.keys(), self.target_objects):
        #    print("saw target object %s" % o)

        #print("saw total objects %s" % seen_target_objects.keys())
        return seen_target_objects

    def initialize_scene(self):
        self.target_objects = []
        self.object_receptacle = defaultdict(
            lambda: dict(objectId='StartupPosition', pivotSimObjs=[]))

        self.open_receptacles = []
        open_pickupable = {}
        pickupable = {}
        for o in filter(lambda x: x['receptacle'], self.last_event.metadata['objects']):
            for oid in o['receptacleObjectIds']:
                self.object_receptacle[oid] = o

        for o in filter(lambda x: x['receptacle'], self.last_event.metadata['objects']):
            for oid in o['receptacleObjectIds']:
                if o['openable'] or (o['objectId'] in self.object_receptacle \
                    and self.object_receptacle[o['objectId']]['openable']):

                    open_pickupable[oid] = o['objectId']
                else:
                    pickupable[oid] = o['objectId']

        if open_pickupable.keys():
            self.target_objects = random.sample(open_pickupable.keys(), k=1)
            shuffled_keys = list(open_pickupable.keys())
            random.shuffle(shuffled_keys)
            for oid in shuffled_keys:
                position_target = self.object_receptacle[self.target_objects[0]]['position']
                position_candidate = self.object_receptacle[oid]['position']
                dist = math.sqrt(
                    (position_target['x'] - position_candidate['x']) ** 2 + \
                    (position_target['y'] - position_candidate['y']) ** 2)
                # try to find something that is far to avoid having the doors collide
                if dist > 1.25:
                    self.target_objects.append(oid)
                    break

        for roid in set(map(lambda x: open_pickupable[x], self.target_objects)):
            self.open_receptacles.append(roid)
            self.step(dict(
                action='OpenObject',
                objectId=roid,
                forceVisible=True), raise_for_failure=True)

    def queue_step(self):
        search_point = self.queue.popleft()
        event = self.step(dict(
            action='Teleport',
            x=search_point.start_position['x'],
            y=search_point.start_position['y'],
            z=search_point.start_position['z']))

        print(event.metadata['errorMessage'])
        assert event.metadata['lastActionSuccess']
        mv = search_point.move_vector
        mv['moveMagnitude'] = self.move_magnitude
        event = self.step(dict(action='Move', **mv))

        if event.metadata['lastActionSuccess']:
            if event.metadata['agent']['position']['y'] > 1.3:
                #pprint(search_point.start_position)
                #pprint(search_point.move_vector)
                #pprint(event.metadata['agent']['position'])
                raise Exception("**** got big point ")

            self.enqueue_points(event.metadata['agent']['position'])
            self.grid_points.append(event.metadata['agent']['position'])


        return event
