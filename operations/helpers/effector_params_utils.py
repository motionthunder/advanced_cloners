"""
Утилиты для установки параметров эффекторов.
"""

import bpy
from ...core.utils.node_utils import find_socket_by_name
from ...core.utils.config_utils import apply_effector_config, load_config

def setup_random_effector_params(modifier):
    """
    Устанавливает параметры для Random эффектора.
    
    Args:
        modifier: Модификатор эффектора
    """
    # Пытаемся применить конфигурацию из JSON файла
    if apply_effector_config(modifier, "RANDOM"):
        print("Applied RANDOM effector config from JSON file")
        return
    
    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default RANDOM effector parameters")
    
    # Устанавливаем базовые параметры
    enable_id = find_socket_by_name(modifier, "Enable")
    strength_id = find_socket_by_name(modifier, "Strength")
    position_id = find_socket_by_name(modifier, "Position")
    rotation_id = find_socket_by_name(modifier, "Rotation")
    scale_id = find_socket_by_name(modifier, "Scale")
    uniform_scale_id = find_socket_by_name(modifier, "Uniform Scale")
    seed_id = find_socket_by_name(modifier, "Seed")
    
    # Устанавливаем значения
    if enable_id:
        modifier[enable_id] = True
    
    if strength_id:
        modifier[strength_id] = 1.0
    
    if position_id:
        modifier[position_id] = (0.5, 0.5, 0.5)
    
    if rotation_id:
        modifier[rotation_id] = (15.0, 15.0, 15.0)
    
    if scale_id:
        modifier[scale_id] = (0.2, 0.2, 0.2)
    
    if uniform_scale_id:
        modifier[uniform_scale_id] = True
    
    if seed_id:
        modifier[seed_id] = 0
    
    # Параметры поля
    field_id = find_socket_by_name(modifier, "Field")
    use_field_id = find_socket_by_name(modifier, "Use Field")
    
    if field_id:
        modifier[field_id] = 1.0
    
    if use_field_id:
        modifier[use_field_id] = False

def setup_noise_effector_params(modifier):
    """
    Устанавливает параметры для Noise эффектора.
    
    Args:
        modifier: Модификатор эффектора
    """
    # Пытаемся применить конфигурацию из JSON файла
    if apply_effector_config(modifier, "NOISE"):
        print("Applied NOISE effector config from JSON file")
        return
    
    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default NOISE effector parameters")
    
    # Устанавливаем базовые параметры
    enable_id = find_socket_by_name(modifier, "Enable")
    strength_id = find_socket_by_name(modifier, "Strength")
    position_id = find_socket_by_name(modifier, "Position")
    symmetric_translation_id = find_socket_by_name(modifier, "Symmetric Translation")
    rotation_id = find_socket_by_name(modifier, "Rotation")
    symmetric_rotation_id = find_socket_by_name(modifier, "Symmetric Rotation")
    scale_id = find_socket_by_name(modifier, "Scale")
    uniform_scale_id = find_socket_by_name(modifier, "Uniform Scale")
    
    # Параметры шума
    noise_scale_id = find_socket_by_name(modifier, "Noise Scale")
    noise_detail_id = find_socket_by_name(modifier, "Noise Detail")
    noise_roughness_id = find_socket_by_name(modifier, "Noise Roughness")
    noise_lacunarity_id = find_socket_by_name(modifier, "Noise Lacunarity")
    noise_distortion_id = find_socket_by_name(modifier, "Noise Distortion")
    noise_position_id = find_socket_by_name(modifier, "Noise Position")
    noise_xyz_scale_id = find_socket_by_name(modifier, "Noise XYZ Scale")
    speed_id = find_socket_by_name(modifier, "Speed")
    seed_id = find_socket_by_name(modifier, "Seed")
    
    # Устанавливаем значения
    if enable_id:
        modifier[enable_id] = True
    
    if strength_id:
        modifier[strength_id] = 1.0
    
    if position_id:
        modifier[position_id] = (0.5, 0.5, 0.5)
    
    if symmetric_translation_id:
        modifier[symmetric_translation_id] = False
    
    if rotation_id:
        modifier[rotation_id] = (15.0, 15.0, 15.0)
    
    if symmetric_rotation_id:
        modifier[symmetric_rotation_id] = False
    
    if scale_id:
        modifier[scale_id] = (0.2, 0.2, 0.2)
    
    if uniform_scale_id:
        modifier[uniform_scale_id] = True
    
    # Параметры шума
    if noise_scale_id:
        modifier[noise_scale_id] = 0.5
    
    if noise_detail_id:
        modifier[noise_detail_id] = 2.0
    
    if noise_roughness_id:
        modifier[noise_roughness_id] = 0.5
    
    if noise_lacunarity_id:
        modifier[noise_lacunarity_id] = 2.0
    
    if noise_distortion_id:
        modifier[noise_distortion_id] = 0.0
    
    if noise_position_id:
        modifier[noise_position_id] = (0.0, 0.0, 0.0)
    
    if noise_xyz_scale_id:
        modifier[noise_xyz_scale_id] = (1.0, 1.0, 1.0)
    
    if speed_id:
        modifier[speed_id] = 0.0
    
    if seed_id:
        modifier[seed_id] = 0
    
    # Параметры поля
    field_id = find_socket_by_name(modifier, "Field")
    use_field_id = find_socket_by_name(modifier, "Use Field")
    
    if field_id:
        modifier[field_id] = 1.0
    
    if use_field_id:
        modifier[use_field_id] = False

def setup_effector_params(modifier, effector_type):
    """
    Устанавливает параметры для эффектора указанного типа.
    
    Args:
        modifier: Модификатор эффектора
        effector_type: Тип эффектора ('RANDOM', 'NOISE')
    """
    if effector_type == "RANDOM":
        setup_random_effector_params(modifier)
    elif effector_type == "NOISE":
        setup_noise_effector_params(modifier)
    else:
        print(f"Unknown effector type: {effector_type}")
