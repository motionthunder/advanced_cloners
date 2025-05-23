"""
Утилиты для работы с нод-группами, сокетами, именами и структурами узлов.
"""

import bpy
import json
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, Collection

#region РАБОТА С ИМЕНАМИ УЗЛОВ

def create_unique_name(base_name: str, existing_collection: Collection, counter_format: str = "{}.{:03d}") -> str:
    """
    Создает уникальное имя в коллекции, добавляя инкрементальный суффикс при необходимости.
    
    Args:
        base_name: Базовое имя
        existing_collection: Коллекция, в которой имя должно быть уникальным
        counter_format: Формат для добавления счетчика к имени
        
    Returns:
        Уникальное имя в заданной коллекции
    """
    unique_name = base_name
    counter = 1
    while unique_name in existing_collection:
        unique_name = counter_format.format(base_name, counter)
        counter += 1
    return unique_name

# Алиас для обратной совместимости
def generate_unique_name(base_name: str, existing_collection: Collection, counter_format: str = "{}.{:03d}") -> str:
    """
    Алиас для функции create_unique_name для обратной совместимости.
    
    Args:
        base_name: Базовое имя
        existing_collection: Коллекция, в которой имя должно быть уникальным
        counter_format: Формат для добавления счетчика к имени
        
    Returns:
        Уникальное имя в заданной коллекции
    """
    return create_unique_name(base_name, existing_collection, counter_format)

#endregion

#region СОЗДАНИЕ И КОПИРОВАНИЕ ГРУПП УЗЛОВ

def create_independent_node_group(template_creator_func: Callable, base_node_name: str) -> Optional[bpy.types.NodeGroup]:
    """
    Создает независимую копию группы узлов
    
    Args:
        template_creator_func: Функция, создающая шаблонную группу узлов
        base_node_name: Базовое имя для новой группы узлов
        
    Returns:
        Созданная независимая группа узлов или None, если создание не удалось
    """
    # Создаем базовую группу узлов
    template_node_group = template_creator_func()
    if template_node_group is None:
        return None
    
    # Создаем независимую копию
    try:
        independent_node_group = template_node_group.copy()
    except Exception as e:
        print(f"Failed to copy node group: {e}")
        if template_node_group.users == 0:
            try:
                bpy.data.node_groups.remove(template_node_group, do_unlink=True)
            except Exception as remove_e:
                print(f"Warning: Could not remove template node group: {remove_e}")
        return None
    
    # Удаляем шаблон или переименовываем его
    if template_node_group.users == 0:
        try:
            bpy.data.node_groups.remove(template_node_group, do_unlink=True)
        except Exception as e:
            print(f"Warning: Could not remove template node group: {e}")
    else:
        template_node_group.name += ".template"
    
    # Создаем уникальное имя для копии
    independent_node_group.name = create_unique_name(base_node_name, bpy.data.node_groups)
    
    return independent_node_group

#endregion

#region РАБОТА С СОКЕТАМИ

def find_socket_by_name(modifier, socket_name):
    """
    Находит сокет в интерфейсе модификатора по имени.
    
    Args:
        modifier: Модификатор с нод-группой
        socket_name: Имя сокета для поиска
        
    Returns:
        Идентификатор сокета или None, если не найден
    """
    if not modifier or not modifier.node_group:
        return None
    
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == socket_name:
            return socket.identifier
    
    return None

def display_socket_prop(layout, modifier, socket_name, text=None, **kwargs):
    """
    Безопасно отображает свойство сокета модификатора.
    
    Args:
        layout: Объект layout Blender для отображения UI
        modifier: Модификатор с нод-группой
        socket_name: Имя сокета для отображения
        text: Текст для отображения (если None, используется имя сокета)
        **kwargs: Дополнительные параметры для передачи в layout.prop
        
    Returns:
        True если сокет был найден и отображен, иначе False
    """
    socket_id = find_socket_by_name(modifier, socket_name)
    if socket_id:
        if text is None:
            text = socket_name
            
        layout.prop(modifier, f'["{socket_id}"]', text=text, **kwargs)
        return True
    return False

def add_effector_sockets(node_group: bpy.types.NodeGroup) -> Dict[str, Any]:
    """
    Добавляет стандартные входные сокеты эффектора в группу узлов.
    
    Args:
        node_group: Группа узлов, в которую добавляются сокеты
        
    Returns:
        Словарь с созданными сокетами
    """
    # Position influence
    position_influence = node_group.interface.new_socket(
        name="Position Influence", 
        in_out='INPUT', 
        socket_type='NodeSocketVector'
    )
    position_influence.default_value = (0.0, 0.0, 0.0)
    
    # Rotation influence
    rotation_influence = node_group.interface.new_socket(
        name="Rotation Influence", 
        in_out='INPUT', 
        socket_type='NodeSocketVector'
    )
    rotation_influence.default_value = (0.0, 0.0, 0.0)
    rotation_influence.subtype = 'EULER'
    
    # Scale influence
    scale_influence = node_group.interface.new_socket(
        name="Scale Influence", 
        in_out='INPUT', 
        socket_type='NodeSocketVector'
    )
    scale_influence.default_value = (1.0, 1.0, 1.0)
    
    return {
        "position": position_influence,
        "rotation": rotation_influence,
        "scale": scale_influence
    }

#endregion

#region СИСТЕМА РАСШИРЕНИЯ ГРУПП УЗЛОВ

class GroupExtender:
    """
    Система для модульного расширения существующих групп узлов без нарушения их базовой структуры.
    Использует точки расширения для безопасного добавления новой функциональности.
    """
    
    # Константы для точек расширения
    EXTENSION_POINT_PRE = "EXTENSION_POINT_PRE"
    EXTENSION_POINT_POST = "EXTENSION_POINT_POST"
    EXTENSION_POINT_PARAMS = "EXTENSION_POINT_PARAMS"
    
    # Словарь обновлений для разных типов узлов
    _updates_registry = {}
    
    @classmethod
    def register_update(cls, node_type: str, version: str, update_func):
        """
        Регистрирует функцию обновления для определенного типа узла и версии.
        
        Args:
            node_type: Тип группы узлов (например, 'GridCloner', 'RandomEffector')
            version: Версия обновления
            update_func: Функция, которая будет применять обновление к группе узлов
        """
        if node_type not in cls._updates_registry:
            cls._updates_registry[node_type] = {}
        
        cls._updates_registry[node_type][version] = update_func
        print(f"Registered update for {node_type} version {version}")
    
    @classmethod
    def prepare_node_group_for_extensions(cls, node_group, node_type=None):
        """
        Подготавливает группу узлов для расширений, добавляя точки расширения.
        
        Args:
            node_group: Группа узлов для подготовки
            node_type: Тип группы узлов
        
        Returns:
            bool: True, если группа была подготовлена успешно
        """
        # Если группа уже имеет метаданные о расширениях, выходим
        if node_group.get("has_extension_points", False):
            return True
        
        try:
            # Инициализируем хранение метаданных
            if "metadata" not in node_group:
                node_group["metadata"] = json.dumps({
                    "version": "1.0",
                    "extensions": [],
                    "type": node_type or "unknown"
                })
            
            # Добавляем узлы точек расширения, если их еще нет
            input_points = [n for n in node_group.nodes if n.name.startswith(cls.EXTENSION_POINT_PRE)]
            output_points = [n for n in node_group.nodes if n.name.startswith(cls.EXTENSION_POINT_POST)]
            param_points = [n for n in node_group.nodes if n.name.startswith(cls.EXTENSION_POINT_PARAMS)]
            
            # Создаем предварительную точку расширения (для обработки до основной логики)
            if not input_points:
                pre_node = node_group.nodes.new('NodeGroupInput')
                pre_node.name = f"{cls.EXTENSION_POINT_PRE}.001"
                pre_node.location = (-300, 200)
                
                # Настраиваем так, чтобы по умолчанию точка не влияла на работу
                # (пропускает геометрию без изменений)
                
            # Создаем точку расширения после (для обработки после основной логики)
            if not output_points:
                post_node = node_group.nodes.new('NodeGroupOutput')
                post_node.name = f"{cls.EXTENSION_POINT_POST}.001"
                post_node.location = (300, 200)
                
            # Создаем точку для расширения параметров
            if not param_points:
                param_node = node_group.nodes.new('NodeFrame')
                param_node.name = f"{cls.EXTENSION_POINT_PARAMS}.001"
                param_node.label = "Extension Parameters"
                param_node.location = (0, -200)
            
            # Отмечаем группу как подготовленную
            node_group["has_extension_points"] = True
            return True
            
        except Exception as e:
            print(f"Error preparing node group for extensions: {e}")
            return False
    
    @classmethod
    def extend_node_group(cls, node_group, extension_info: Dict[str, Any]):
        """
        Расширяет группу узлов, добавляя новую функциональность.
        
        Args:
            node_group: Группа узлов для расширения
            extension_info: Информация о расширении (тип, id, параметры)
        
        Returns:
            bool: True, если расширение прошло успешно
        """
        # Получаем метаданные
        metadata = cls._get_metadata(node_group)
        if not metadata:
            print(f"Cannot extend node group: no metadata found")
            return False
        
        # Проверяем, не установлено ли уже это расширение
        extension_id = extension_info.get("id", "unknown")
        if extension_id in [ext.get("id") for ext in metadata.get("extensions", [])]:
            print(f"Extension {extension_id} already installed")
            return True
        
        # Убеждаемся, что группа подготовлена для расширений
        if not cls.prepare_node_group_for_extensions(node_group, metadata.get("type")):
            print(f"Failed to prepare node group for extensions")
            return False
        
        try:
            # Выполняем фактическое добавление узлов расширения
            extension_func = extension_info.get("extension_func")
            if extension_func and callable(extension_func):
                # Вызываем функцию расширения
                success = extension_func(node_group)
                if not success:
                    return False
            
            # Обновляем метаданные
            metadata["extensions"].append({
                "id": extension_id,
                "name": extension_info.get("name", "Unnamed Extension"),
                "version": extension_info.get("version", "1.0")
            })
            node_group["metadata"] = json.dumps(metadata)
            return True
            
        except Exception as e:
            print(f"Error extending node group: {e}")
            return False
    
    @classmethod
    def check_and_update_node_group(cls, node_group, force=False):
        """
        Проверяет, нужно ли обновить группу узлов, и применяет необходимые обновления.
        
        Args:
            node_group: Группа узлов для проверки
            force: Принудительно применить все обновления
        
        Returns:
            bool: True, если группа была обновлена
        """
        # Получаем метаданные
        metadata = cls._get_metadata(node_group)
        if not metadata:
            print(f"Cannot update node group: no metadata found")
            return False
        
        node_type = metadata.get("type", "unknown")
        current_version = metadata.get("version", "1.0")
        
        # Проверяем, есть ли доступные обновления для этого типа узла
        if node_type not in cls._updates_registry:
            return False
        
        updated = False
        
        # Сортируем версии обновлений для правильного порядка применения
        versions = sorted(cls._updates_registry[node_type].keys(), 
                           key=lambda v: [int(n) for n in v.split('.')])
        
        # Применяем все обновления, начиная с текущей версии
        for version in versions:
            # Применяем обновление только если оно новее текущей версии или принудительное
            if force or cls._compare_versions(version, current_version) > 0:
                update_func = cls._updates_registry[node_type][version]
                
                try:
                    # Применяем обновление
                    success = update_func(node_group)
                    if success:
                        # Обновляем версию в метаданных
                        metadata["version"] = version
                        node_group["metadata"] = json.dumps(metadata)
                        updated = True
                        print(f"Updated {node_type} to version {version}")
                except Exception as e:
                    print(f"Error updating {node_type} to version {version}: {e}")
        
        return updated
    
    @classmethod
    def _get_metadata(cls, node_group) -> Dict[str, Any]:
        """
        Получает метаданные группы узлов.
        
        Args:
            node_group: Группа узлов
        
        Returns:
            dict: Метаданные группы или пустой словарь
        """
        try:
            metadata_str = node_group.get("metadata", "{}")
            return json.loads(metadata_str)
        except (json.JSONDecodeError, AttributeError):
            return {}
    
    @classmethod
    def _compare_versions(cls, version1, version2):
        """
        Сравнивает две версии.
        
        Args:
            version1: Первая версия
            version2: Вторая версия
        
        Returns:
            int: -1 если version1 < version2, 0 если равны, 1 если version1 > version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 < v2:
                return -1
            if v1 > v2:
                return 1
        
        return 0

#endregion
