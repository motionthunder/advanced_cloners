"""
Утилиты для работы с конфигурационными файлами.
Позволяет загружать и применять конфигурации из JSON файлов для клонеров, эффекторов и филдов.
"""

import bpy
import json
import os
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Пути к конфигурационным файлам
CONFIG_DIR = "config"
CLONERS_CONFIG_DIR = os.path.join(CONFIG_DIR, "cloners")
EFFECTORS_CONFIG_DIR = os.path.join(CONFIG_DIR, "effectors")
FIELDS_CONFIG_DIR = os.path.join(CONFIG_DIR, "fields")

# Словари для кэширования загруженных конфигураций
_cloner_configs = {}
_effector_configs = {}
_field_configs = {}

def get_addon_path() -> str:
    """
    Получает путь к директории аддона.

    Returns:
        str: Путь к директории аддона
    """
    # Получаем путь к текущему файлу
    current_file = os.path.abspath(__file__)

    # Поднимаемся на три уровня вверх (core/utils/config_utils.py -> core/utils -> core -> addon_root)
    addon_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    return addon_path

def ensure_config_dirs() -> bool:
    """
    Проверяет наличие директорий для конфигурационных файлов и создает их при необходимости.

    Returns:
        bool: True, если директории существуют или были успешно созданы
    """
    addon_path = get_addon_path()

    # Создаем пути к директориям
    config_path = os.path.join(addon_path, CONFIG_DIR)
    cloners_path = os.path.join(addon_path, CLONERS_CONFIG_DIR)
    effectors_path = os.path.join(addon_path, EFFECTORS_CONFIG_DIR)
    fields_path = os.path.join(addon_path, FIELDS_CONFIG_DIR)

    # Создаем директории, если они не существуют
    try:
        os.makedirs(config_path, exist_ok=True)
        os.makedirs(cloners_path, exist_ok=True)
        os.makedirs(effectors_path, exist_ok=True)
        os.makedirs(fields_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating config directories: {e}")
        return False

def load_config(config_type: str, component_type: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Загружает конфигурацию для указанного типа компонента.

    Args:
        config_type: Тип конфигурации ('cloners', 'effectors', 'fields')
        component_type: Тип компонента (например, 'GRID', 'RANDOM', 'SPHERE')
        use_cache: Использовать ли кэш (True) или загружать заново из файла (False)

    Returns:
        dict: Словарь с параметрами компонента или пустой словарь в случае ошибки
    """
    # Определяем путь к файлу конфигурации
    addon_path = get_addon_path()

    if config_type == 'cloners':
        config_dir = os.path.join(addon_path, CLONERS_CONFIG_DIR)
        cache = _cloner_configs
    elif config_type == 'effectors':
        config_dir = os.path.join(addon_path, EFFECTORS_CONFIG_DIR)
        cache = _effector_configs
    elif config_type == 'fields':
        config_dir = os.path.join(addon_path, FIELDS_CONFIG_DIR)
        cache = _field_configs
    else:
        print(f"Unknown config type: {config_type}")
        return {}

    # Проверяем, есть ли конфигурация в кэше и нужно ли использовать кэш
    cache_key = f"{config_type}_{component_type}"
    if use_cache and cache_key in cache:
        print(f"Using cached config for {component_type}")
        return cache[cache_key]

    # Формируем имя файла
    filename = f"{component_type.lower()}.json"
    config_file = os.path.join(config_dir, filename)

    # Проверяем существование файла
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        return {}

    # Загружаем конфигурацию из файла
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Кэшируем конфигурацию
        cache[cache_key] = config
        print(f"Loaded config from {config_file}")

        return config
    except Exception as e:
        print(f"Error loading config from {config_file}: {e}")
        return {}

def save_config(config_type: str, component_type: str, config: Dict[str, Any]) -> bool:
    """
    Сохраняет конфигурацию для указанного типа компонента.

    Args:
        config_type: Тип конфигурации ('cloners', 'effectors', 'fields')
        component_type: Тип компонента (например, 'GRID', 'RANDOM', 'SPHERE')
        config: Словарь с параметрами компонента

    Returns:
        bool: True, если конфигурация была успешно сохранена
    """
    # Проверяем наличие директорий
    if not ensure_config_dirs():
        return False

    # Определяем путь к файлу конфигурации
    addon_path = get_addon_path()

    if config_type == 'cloners':
        config_dir = os.path.join(addon_path, CLONERS_CONFIG_DIR)
        cache = _cloner_configs
    elif config_type == 'effectors':
        config_dir = os.path.join(addon_path, EFFECTORS_CONFIG_DIR)
        cache = _effector_configs
    elif config_type == 'fields':
        config_dir = os.path.join(addon_path, FIELDS_CONFIG_DIR)
        cache = _field_configs
    else:
        print(f"Unknown config type: {config_type}")
        return False

    # Формируем имя файла
    filename = f"{component_type.lower()}.json"
    config_file = os.path.join(config_dir, filename)

    # Сохраняем конфигурацию в файл
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        # Обновляем кэш
        cache_key = f"{config_type}_{component_type}"
        cache[cache_key] = config

        print(f"Config saved to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving config to {config_file}: {e}")
        return False

def apply_cloner_config(modifier, cloner_type: str, force_reload: bool = True) -> bool:
    """
    Применяет конфигурацию к модификатору клонера.

    Args:
        modifier: Модификатор клонера
        cloner_type: Тип клонера ('GRID', 'LINEAR', 'CIRCLE')
        force_reload: Принудительно перезагрузить конфигурацию из файла

    Returns:
        bool: True, если конфигурация была успешно применена
    """
    # Загружаем конфигурацию
    if force_reload:
        config = reload_config('cloners', cloner_type)
    else:
        config = load_config('cloners', cloner_type)

    if not config:
        print(f"No config found for cloner type: {cloner_type}")
        return False

    # Определяем тип клонера (объектный/коллекционный/стековый) - для логирования
    is_collection_cloner = False
    is_stacked_cloner = False

    if modifier.node_group:
        # Проверяем имя группы узлов
        if "CollectionCloner" in modifier.node_group.name or "original_collection" in modifier:
            is_collection_cloner = True

        # Проверяем метаданные для стековых клонеров
        if modifier.node_group.get("is_stacked_cloner", False):
            is_stacked_cloner = True

    # Применяем параметры из конфигурации
    try:
        for param_name, param_value in config.items():
            # Ищем сокет по имени
            socket_id = find_socket_by_name(modifier, param_name)
            if socket_id:
                # Проверяем тип текущего значения сокета
                current_value = modifier[socket_id]

                # Обрабатываем различные типы данных
                if isinstance(current_value, float) and isinstance(param_value, list):
                    # Если сокет ожидает float, а в конфиге список, берем первый элемент
                    modifier[socket_id] = param_value[0]

                    # Логирование для отладки
                    cloner_type_str = "collection" if is_collection_cloner else "stacked" if is_stacked_cloner else "standard"
                    print(f"Applied {param_name} = {param_value[0]} (converted from list) to {cloner_type_str} {cloner_type} cloner")

                elif isinstance(current_value, tuple) and isinstance(param_value, list):
                    # Если сокет ожидает tuple, а в конфиге список, преобразуем список в tuple
                    modifier[socket_id] = tuple(param_value)

                    # Логирование для отладки
                    cloner_type_str = "collection" if is_collection_cloner else "stacked" if is_stacked_cloner else "standard"
                    print(f"Applied {param_name} = {tuple(param_value)} (converted from list) to {cloner_type_str} {cloner_type} cloner")

                else:
                    # Стандартное присваивание для других типов данных
                    modifier[socket_id] = param_value

                    # Логирование для отладки
                    cloner_type_str = "collection" if is_collection_cloner else "stacked" if is_stacked_cloner else "standard"
                    print(f"Applied {param_name} = {param_value} to {cloner_type_str} {cloner_type} cloner")

        return True
    except Exception as e:
        print(f"Error applying cloner config: {e}")
        return False

def apply_effector_config(modifier, effector_type: str, force_reload: bool = True) -> bool:
    """
    Применяет конфигурацию к модификатору эффектора.

    Args:
        modifier: Модификатор эффектора
        effector_type: Тип эффектора ('RANDOM', 'NOISE')
        force_reload: Принудительно перезагрузить конфигурацию из файла

    Returns:
        bool: True, если конфигурация была успешно применена
    """
    # Загружаем конфигурацию
    if force_reload:
        config = reload_config('effectors', effector_type)
    else:
        config = load_config('effectors', effector_type)

    if not config:
        print(f"No config found for effector type: {effector_type}")
        return False

    # Применяем параметры из конфигурации
    try:
        for param_name, param_value in config.items():
            socket_id = find_socket_by_name(modifier, param_name)
            if socket_id:
                # Проверяем тип текущего значения сокета
                current_value = modifier[socket_id]

                # Обрабатываем различные типы данных
                if isinstance(current_value, float) and isinstance(param_value, list):
                    # Если сокет ожидает float, а в конфиге список, берем первый элемент
                    modifier[socket_id] = param_value[0]
                    print(f"Applied {param_name} = {param_value[0]} (converted from list) to {effector_type} effector")
                elif isinstance(current_value, tuple) and isinstance(param_value, list):
                    # Если сокет ожидает tuple, а в конфиге список, преобразуем список в tuple
                    modifier[socket_id] = tuple(param_value)
                    print(f"Applied {param_name} = {tuple(param_value)} (converted from list) to {effector_type} effector")
                else:
                    # Стандартное присваивание
                    modifier[socket_id] = param_value
                    print(f"Applied {param_name} = {param_value} to {effector_type} effector")
        return True
    except Exception as e:
        print(f"Error applying effector config: {e}")
        return False

def apply_field_config(modifier, field_type: str, force_reload: bool = True) -> bool:
    """
    Применяет конфигурацию к модификатору поля.

    Args:
        modifier: Модификатор поля
        field_type: Тип поля ('SPHERE')
        force_reload: Принудительно перезагрузить конфигурацию из файла

    Returns:
        bool: True, если конфигурация была успешно применена
    """
    # Загружаем конфигурацию
    if force_reload:
        config = reload_config('fields', field_type)
    else:
        config = load_config('fields', field_type)

    if not config:
        print(f"No config found for field type: {field_type}")
        return False

    # Применяем параметры из конфигурации
    try:
        for param_name, param_value in config.items():
            socket_id = find_socket_by_name(modifier, param_name)
            if socket_id:
                # Проверяем тип текущего значения сокета
                current_value = modifier[socket_id]

                # Обрабатываем различные типы данных
                if isinstance(current_value, float) and isinstance(param_value, list):
                    # Если сокет ожидает float, а в конфиге список, берем первый элемент
                    modifier[socket_id] = param_value[0]
                    print(f"Applied {param_name} = {param_value[0]} (converted from list) to {field_type} field")
                elif isinstance(current_value, tuple) and isinstance(param_value, list):
                    # Если сокет ожидает tuple, а в конфиге список, преобразуем список в tuple
                    modifier[socket_id] = tuple(param_value)
                    print(f"Applied {param_name} = {tuple(param_value)} (converted from list) to {field_type} field")
                else:
                    # Стандартное присваивание
                    modifier[socket_id] = param_value
                    print(f"Applied {param_name} = {param_value} to {field_type} field")
        return True
    except Exception as e:
        print(f"Error applying field config: {e}")
        return False

# Функции для управления кэшем
def clear_cache(config_type: str = None, component_type: str = None):
    """
    Очищает кэш конфигураций.

    Args:
        config_type: Тип конфигурации ('cloners', 'effectors', 'fields') или None для всех типов
        component_type: Тип компонента или None для всех компонентов указанного типа
    """
    global _cloner_configs, _effector_configs, _field_configs

    if config_type is None:
        # Очищаем весь кэш
        _cloner_configs.clear()
        _effector_configs.clear()
        _field_configs.clear()
        print("Cleared all configuration caches")
        return

    # Выбираем нужный кэш
    if config_type == 'cloners':
        cache = _cloner_configs
    elif config_type == 'effectors':
        cache = _effector_configs
    elif config_type == 'fields':
        cache = _field_configs
    else:
        print(f"Unknown config type: {config_type}")
        return

    if component_type is None:
        # Очищаем кэш для всех компонентов указанного типа
        cache.clear()
        print(f"Cleared cache for all {config_type}")
    else:
        # Очищаем кэш только для указанного компонента
        cache_key = f"{config_type}_{component_type}"
        if cache_key in cache:
            del cache[cache_key]
            print(f"Cleared cache for {component_type} {config_type}")

def reload_config(config_type: str, component_type: str) -> Dict[str, Any]:
    """
    Перезагружает конфигурацию из файла, игнорируя кэш.

    Args:
        config_type: Тип конфигурации ('cloners', 'effectors', 'fields')
        component_type: Тип компонента (например, 'GRID', 'RANDOM', 'SPHERE')

    Returns:
        dict: Словарь с параметрами компонента или пустой словарь в случае ошибки
    """
    # Очищаем кэш для указанного компонента
    clear_cache(config_type, component_type)

    # Загружаем конфигурацию заново
    return load_config(config_type, component_type, use_cache=False)

# Импортируем функцию для поиска сокета по имени
from ..utils.node_utils import find_socket_by_name
