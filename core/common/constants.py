"""
Constants and data structures for Advanced Cloners addon.
"""

# Определяем типы клонеров
CLONER_TYPES = [
    ("GRID", "Grid Cloner", "Create a 3D grid of clones", "MESH_GRID"),
    ("LINEAR", "Linear Cloner", "Create a linear array of clones", "SORTSIZE"),
    ("CIRCLE", "Circle Cloner", "Create a circular array of clones", "MESH_CIRCLE"),
]

# Определяем типы эффекторов
EFFECTOR_TYPES = [
    ("RANDOM", "Random", "Apply random transformations to clones", "RNDCURVE"),
    ("NOISE", "Noise", "Apply noise-based transformations to clones", "FORCE_TURBULENCE"),
]

# Константы для типов эффекторов и их идентификации
EFFECTOR_TYPE_RANDOM = "RandomEffector"
EFFECTOR_TYPE_NOISE = "NoiseEffector"

# Константы для идентификации сокетов
SOCKET_INSTANCE_SCALE = "Socket_5"  # instance_scale
SOCKET_GLOBAL_POSITION = "Socket_8"  # global_position
SOCKET_GLOBAL_ROTATION = "Socket_9"  # global_rotation
SOCKET_RANDOM_SEED = "Socket_10"     # random_seed
SOCKET_RANDOM_POSITION = "Socket_6"  # random_position
SOCKET_RANDOM_ROTATION = "Socket_7"  # random_rotation
SOCKET_RANDOM_SCALE = "Socket_11"    # random_scale

# Импортируем необходимые классы для создания нод-групп
from ...models.cloners.grid_cloner import GridCloner
from ...models.cloners.linear_cloner import LinearCloner
from ...models.cloners.circle_cloner import CircleCloner
from ...models.effectors.random_effector import RandomEffector
from ...models.effectors.noise_effector import NoiseEffector
from ...models.fields.sphere_field import SphereField

# Определяем функции создания нод-групп
def gridcloner3d_node_group():
    return GridCloner.create_node_group()

def advancedlinearcloner_node_group():
    return LinearCloner.create_node_group()

def circlecloner_node_group():
    return CircleCloner.create_node_group()

def randomeffector_node_group():
    return RandomEffector.create_node_group()

def noiseeffector_node_group():
    return NoiseEffector.create_node_group()

def spherefield_node_group():
    return SphereField.create_node_group()

# Функции создания для каждого типа эффектора
EFFECTOR_CREATORS = {
    "RANDOM": randomeffector_node_group,
    "NOISE": noiseeffector_node_group,
}

# Функции создания для каждого типа поля
FIELD_CREATORS = {
    "SPHERE": spherefield_node_group,
}

# Имена групп узлов для эффекторов
EFFECTOR_GROUP_NAMES = {
    "RANDOM": "RandomEffector",
    "NOISE": "NoiseEffector",
}

# Имена модификаторов для эффекторов
EFFECTOR_MOD_NAMES = {
    "RANDOM": "Random Effector",
    "NOISE": "Noise Effector",
}

# Импортируем имена групп узлов для клонеров
from ...models.cloners import CLONER_GROUP_NAMES, CLONER_MOD_NAMES
from ...models.fields import FIELD_GROUP_NAMES, FIELD_MOD_NAMES, FIELD_TYPES

# Префиксы для распознавания типов модификаторов
CLONER_NODE_GROUP_PREFIXES = list(CLONER_GROUP_NAMES.values())
EFFECTOR_NODE_GROUP_PREFIXES = list(EFFECTOR_GROUP_NAMES.values())
FIELD_NODE_GROUP_PREFIXES = list(FIELD_GROUP_NAMES.values())