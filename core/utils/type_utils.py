"""
Утилиты для работы с типами клонирования.
"""

import bpy
from typing import Dict, List, Any, Optional
from ...models.cloners import CLONER_TYPES, CLONER_NODE_GROUP_PREFIXES

def handle_clone_type_switch(obj: bpy.types.Object, modifier: bpy.types.Modifier, old_type: str, new_type: str) -> bool:
    """
    Обрабатывает переключение между типами клонирования (объект/коллекция).
    
    Args:
        obj: Объект с модификатором клонера
        modifier: Модификатор клонера
        old_type: Предыдущий тип клонирования ('OBJECT' или 'COLLECTION')
        new_type: Новый тип клонирования ('OBJECT' или 'COLLECTION')
    
    Returns:
        True если переключение успешно, False в случае ошибки
    """
    if old_type == new_type:
        return True  # Нет необходимости что-либо делать
    
    if not modifier or not modifier.node_group:
        return False
    
    # Сохраняем текущие настройки для старого типа
    save_cloner_settings(modifier, old_type)
    
    # Восстанавливаем настройки для нового типа, если они существуют
    load_cloner_settings(modifier, new_type)
    
    # Восстанавливаем видимость объектов
    restore_visibility_for_type_switch(obj, old_type, new_type)
    
    # Обновляем интерфейс узла с новыми параметрами
    update_node_interface_for_type(modifier, new_type)
    
    return True

def save_cloner_settings(modifier: bpy.types.Modifier, clone_type: str) -> None:
    """
    Сохраняет текущие параметры клонера для указанного типа клонирования.
    
    Args:
        modifier: Модификатор клонера
        clone_type: Тип клонирования ('OBJECT' или 'COLLECTION')
    """
    if not modifier or not modifier.node_group:
        return
    
    node_group = modifier.node_group
    settings = {}
    
    # Получаем все текущие значения сокетов из интерфейса
    for socket in node_group.interface.items_tree:
        if socket.in_out == 'INPUT':  # Только входные сокеты
            socket_id = socket.identifier
            
            # Сохраняем значение, если оно есть в модификаторе
            if socket_id in modifier:
                settings[socket_id] = modifier[socket_id]
    
    # Сохраняем настройки в кастомное свойство группы узлов
    if clone_type == 'OBJECT':
        node_group["object_clone_settings"] = settings
    else:
        node_group["collection_clone_settings"] = settings

def load_cloner_settings(modifier: bpy.types.Modifier, clone_type: str) -> None:
    """
    Загружает параметры клонера для указанного типа клонирования.
    
    Args:
        modifier: Модификатор клонера
        clone_type: Тип клонирования ('OBJECT' или 'COLLECTION')
    """
    if not modifier or not modifier.node_group:
        return
    
    node_group = modifier.node_group
    settings_key = "object_clone_settings" if clone_type == 'OBJECT' else "collection_clone_settings"
    
    # Загружаем сохраненные настройки, если они существуют
    if settings_key in node_group:
        settings = node_group[settings_key]
        
        # Применяем настройки к модификатору
        for socket_id, value in settings.items():
            if socket_id in modifier:
                modifier[socket_id] = value

def restore_visibility_for_type_switch(obj: bpy.types.Object, old_type: str, new_type: str) -> None:
    """
    Восстанавливает видимость объектов при переключении между типами клонирования.
    
    Args:
        obj: Объект с модификатором клонера
        old_type: Предыдущий тип клонирования ('OBJECT' или 'COLLECTION')
        new_type: Новый тип клонирования ('OBJECT' или 'COLLECTION')
    """
    scene = bpy.context.scene
    
    # Если переключаемся с коллекции на объект
    if old_type == 'COLLECTION' and new_type == 'OBJECT':
        # 1. Восстанавливаем видимость основного объекта
        obj.hide_viewport = False
        obj.hide_render = False
        
        # 2. Если был выбран объект для клонирования, убедимся что он видим
        if hasattr(scene, "object_to_clone") and scene.object_to_clone:
            scene.object_to_clone.hide_viewport = False
            scene.object_to_clone.hide_render = False
        
        # 3. Убедимся что вся цепочка модификаторов активна
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                mod.show_viewport = True
                mod.show_render = True
    
    # Если переключаемся с объекта на коллекцию
    elif old_type == 'OBJECT' and new_type == 'COLLECTION':
        # 1. Восстанавливаем видимость основного объекта
        obj.hide_viewport = False
        obj.hide_render = False
        
        # 2. Делаем видимыми все объекты в коллекции
        if hasattr(scene, "collection_to_clone") and scene.collection_to_clone:
            for collection_obj in scene.collection_to_clone.objects:
                collection_obj.hide_viewport = False
                collection_obj.hide_render = False
        
        # 3. Проверяем все модификаторы клонирования
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                mod.show_viewport = True
                mod.show_render = True
    
    # Принудительное обновление сцены, чтобы изменения отобразились
    bpy.context.view_layer.update()
    
    # Дополнительно обновим интерфейс
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def update_node_interface_for_type(modifier: bpy.types.Modifier, clone_type: str) -> None:
    """
    Обновляет интерфейс узла в соответствии с типом клонирования.
    
    Args:
        modifier: Модификатор клонера
        clone_type: Тип клонирования ('OBJECT' или 'COLLECTION')
    """
    if not modifier or not modifier.node_group:
        return
    
    node_group = modifier.node_group
    
    # Получаем тип клонера из группы узлов
    cloner_type = None
    for group_type, prefix in CLONER_NODE_GROUP_PREFIXES.items():
        if prefix in node_group.name:
            cloner_type = group_type
            break
    
    if not cloner_type:
        return
    
    # Обновляем сокеты в зависимости от типа клонирования
    # Это может включать включение/отключение определенных сокетов или изменение значений по умолчанию
    
    # Здесь может быть специфическая логика для различных типов клонеров
    # Например, для Grid клонера, Linear клонера и т.д.
    
    # Принудительное обновление для перерисовки геометрии
    bpy.context.view_layer.update()
