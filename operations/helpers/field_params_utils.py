"""
Утилиты для установки параметров полей.
"""

import bpy
from ...core.utils.node_utils import find_socket_by_name
from ...core.utils.config_utils import apply_field_config, load_config

def setup_sphere_field_params(modifier):
    """
    Устанавливает параметры для Sphere поля.
    
    Args:
        modifier: Модификатор поля
    """
    # Пытаемся применить конфигурацию из JSON файла
    if apply_field_config(modifier, "SPHERE"):
        print("Applied SPHERE field config from JSON file")
        return
    
    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default SPHERE field parameters")
    
    # Устанавливаем базовые параметры
    falloff_id = find_socket_by_name(modifier, "Falloff")
    inner_strength_id = find_socket_by_name(modifier, "Inner Strength")
    outer_strength_id = find_socket_by_name(modifier, "Outer Strength")
    mode_id = find_socket_by_name(modifier, "Mode")
    strength_id = find_socket_by_name(modifier, "Strength")
    
    # Устанавливаем значения
    if falloff_id:
        modifier[falloff_id] = 0.5
    
    if inner_strength_id:
        modifier[inner_strength_id] = 1.0
    
    if outer_strength_id:
        modifier[outer_strength_id] = 0.0
    
    if mode_id:
        modifier[mode_id] = 'S-Curve'
    
    if strength_id:
        modifier[strength_id] = 0.3

def setup_field_params(modifier, field_type):
    """
    Устанавливает параметры для поля указанного типа.
    
    Args:
        modifier: Модификатор поля
        field_type: Тип поля ('SPHERE')
    """
    if field_type == "SPHERE":
        setup_sphere_field_params(modifier)
    else:
        print(f"Unknown field type: {field_type}")
