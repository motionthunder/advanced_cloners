"""
Cloner models for Advanced Cloners addon.
"""

from .grid_cloner import GridCloner
from .linear_cloner import LinearCloner
from .circle_cloner import CircleCloner

# Константы для типов клонеров и их названий
CLONER_TYPES = [
    ("GRID", "Grid Cloner", "Create a grid of instances", "MESH_GRID"),
    ("LINEAR", "Linear Cloner", "Create a line of instances", "SORTSIZE"),
    ("CIRCLE", "Circle Cloner", "Create a circle of instances", "MESH_CIRCLE"),
]

# Словарь классов клонеров
AVAILABLE_CLONERS = {
    "GRID": GridCloner,
    "LINEAR": LinearCloner,
    "CIRCLE": CircleCloner,
}

# Словарь функций для создания групп узлов
NODE_GROUP_CREATORS = {
    "GRID": GridCloner.create_node_group,
    "LINEAR": LinearCloner.create_node_group,
    "CIRCLE": CircleCloner.create_node_group,
}

# Словарь имен групп узлов
CLONER_GROUP_NAMES = {
    "GRID": "AdvancedGridCloner",
    "LINEAR": "AdvancedLinearCloner",
    "CIRCLE": "AdvancedCircleCloner",
}

# Имена модификаторов для клонеров
CLONER_MOD_NAMES = {
    "GRID": "Grid Cloner",
    "LINEAR": "Linear Cloner",
    "CIRCLE": "Circle Cloner",
}

# Префиксы имен групп узлов
CLONER_NODE_GROUP_PREFIXES = [
    "AdvancedGridCloner",
    "AdvancedLinearCloner",
    "AdvancedCircleCloner",
] 