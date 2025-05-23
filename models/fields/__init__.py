"""
Field models for Advanced Cloners addon.
"""

from .sphere_field import SphereField

# Константы для типов полей и их названий
FIELD_TYPES = [
    ("SPHERE", "Sphere Field", "Creates a spherical influence area", "SPHERECURVE"),
]

# Словарь классов полей
AVAILABLE_FIELDS = {
    "SPHERE": SphereField,
}

# Словарь функций для создания групп узлов
FIELD_CREATORS = {
    "SPHERE": SphereField.create_node_group,
}

# Словарь имен групп узлов
FIELD_GROUP_NAMES = {
    "SPHERE": "SphereField",
}

# Имена модификаторов для полей
FIELD_MOD_NAMES = {
    "SPHERE": "Sphere Field",
}

# Префиксы имен групп узлов
FIELD_NODE_GROUP_PREFIXES = [
    "SphereField",
]
