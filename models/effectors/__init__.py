"""
Effector models for Advanced Cloners addon.
"""

from .random_effector import RandomEffector
from .noise_effector import NoiseEffector

# Константы для типов эффекторов и их названий
EFFECTOR_TYPES = [
    ("RANDOM", "Random Effector", "Apply random transformations to instances", "RNDCURVE"),
    ("NOISE", "Noise Effector", "Apply noise-based transformations to instances", "FORCE_TURBULENCE"),
]

# Словарь классов эффекторов
AVAILABLE_EFFECTORS = {
    "RANDOM": RandomEffector,
    "NOISE": NoiseEffector,
}

# Словарь функций для создания групп узлов
EFFECTOR_CREATORS = {
    "RANDOM": RandomEffector.create_node_group,
    "NOISE": NoiseEffector.create_node_group,
}

# Словарь имен групп узлов
EFFECTOR_GROUP_NAMES = {
    "RANDOM": "RandomEffector",
    "NOISE": "NoiseEffector",
}

# Имена модификаторов для эффекторов
EFFECTOR_MOD_NAMES = {
    "RANDOM": "Random Effector",
    "NOISE": "Noise Effector",
}

# Префиксы имен групп узлов
EFFECTOR_NODE_GROUP_PREFIXES = [
    "RandomEffector",
    "NoiseEffector",
] 