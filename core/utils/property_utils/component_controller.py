"""
Система контроллеров для управления компонентами аддона.
Позволяет расширять функциональность существующих компонентов без изменения их базовой структуры.
"""

import bpy
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from mathutils import Vector


class ComponentController:
    """
    Контроллер, который позволяет безопасно расширять функциональность компонентов аддона
    без изменения их базовой структуры.
    """
    
    # Реестр зарегистрированных контроллеров
    _registered_controllers = {}
    
    @classmethod
    def register_controller(cls, controller_id: str, controller_class):
        """
        Регистрирует новый класс контроллера.
        
        Args:
            controller_id: Уникальный идентификатор контроллера
            controller_class: Класс контроллера
        """
        cls._registered_controllers[controller_id] = controller_class
        print(f"Registered controller: {controller_id}")
    
    @classmethod
    def create_controller(cls, obj, target_modifier, controller_id: str, **kwargs):
        """
        Создает контроллер для указанного модификатора.
        
        Args:
            obj: Объект с модификатором
            target_modifier: Целевой модификатор, к которому применяется контроллер
            controller_id: Идентификатор типа контроллера
            **kwargs: Дополнительные параметры для контроллера
        
        Returns:
            tuple: (bpy.types.Modifier, bpy.types.NodeGroup) созданный модификатор и его группа узлов,
                 или (None, None) в случае ошибки
        """
        if controller_id not in cls._registered_controllers:
            print(f"Unknown controller type: {controller_id}")
            return None, None
        
        try:
            # Получаем класс контроллера
            controller_class = cls._registered_controllers[controller_id]
            
            # Создаем контроллер
            mod, node_group = controller_class.create(obj, target_modifier, **kwargs)
            
            if mod and node_group:
                # Сохраняем информацию о контроллере в модификаторе
                mod["controller_type"] = controller_id
                mod["target_modifier"] = target_modifier.name
                
                # Свойства для определения отношений между компонентами
                node_group["is_controller"] = True
                node_group["controller_id"] = controller_id
                node_group["controller_version"] = controller_class.VERSION
                
                # Структурируем свойства для организации
                mod["controller_info"] = json.dumps({
                    "id": controller_id,
                    "version": controller_class.VERSION,
                    "target": target_modifier.name,
                    "params": kwargs
                })
                
                return mod, node_group
                
        except Exception as e:
            print(f"Error creating controller: {e}")
        
        return None, None
    
    @classmethod
    def get_controllers_for_modifier(cls, obj, modifier_name: str) -> List[bpy.types.Modifier]:
        """
        Получает все контроллеры, связанные с указанным модификатором.
        
        Args:
            obj: Объект с модификаторами
            modifier_name: Имя целевого модификатора
        
        Returns:
            list: Список модификаторов-контроллеров
        """
        controllers = []
        
        for mod in obj.modifiers:
            if hasattr(mod, "node_group") and mod.node_group:
                if mod.node_group.get("is_controller", False):
                    if mod.get("target_modifier", "") == modifier_name:
                        controllers.append(mod)
        
        return controllers
    
    @classmethod
    def update_all_controllers(cls, obj):
        """
        Обновляет все контроллеры на указанном объекте.
        
        Args:
            obj: Объект с контроллерами
        """
        for mod in obj.modifiers:
            if hasattr(mod, "node_group") and mod.node_group:
                if mod.node_group.get("is_controller", False):
                    controller_id = mod.node_group.get("controller_id", "")
                    target_mod_name = mod.get("target_modifier", "")
                    
                    if controller_id in cls._registered_controllers and target_mod_name in obj.modifiers:
                        controller_class = cls._registered_controllers[controller_id]
                        controller_class.update(obj, mod, obj.modifiers[target_mod_name])


# Базовый класс для всех контроллеров компонентов
class BaseComponentController:
    """
    Базовый класс для контроллеров компонентов.
    Определяет общий интерфейс и методы для всех типов контроллеров.
    """
    
    # Версия контроллера
    VERSION = "1.0"
    
    # Уникальный идентификатор типа контроллера
    CONTROLLER_ID = "base_controller"
    
    # Имя для отображения
    CONTROLLER_NAME = "Base Controller"
    
    @classmethod
    def create(cls, obj, target_modifier, **kwargs):
        """
        Создает новый контроллер для указанного модификатора.
        
        Args:
            obj: Объект с модификатором
            target_modifier: Целевой модификатор
            **kwargs: Дополнительные параметры
        
        Returns:
            tuple: (bpy.types.Modifier, bpy.types.NodeGroup) созданный модификатор и его группа узлов
        """
        # Создаем модификатор
        mod_name = f"{cls.CONTROLLER_NAME} for {target_modifier.name}"
        counter = 1
        while mod_name in obj.modifiers:
            mod_name = f"{cls.CONTROLLER_NAME} {counter} for {target_modifier.name}"
            counter += 1
        
        mod = obj.modifiers.new(name=mod_name, type='NODES')
        
        # Создаем группу узлов
        node_group = cls._create_node_group(obj, target_modifier, **kwargs)
        if not node_group:
            # Если не удалось создать группу, удаляем модификатор
            obj.modifiers.remove(mod)
            return None, None
        
        # Устанавливаем группу узлов для модификатора
        mod.node_group = node_group
        
        # Перемещаем модификатор в нужную позицию в стеке
        # (рядом с целевым модификатором)
        target_index = cls._get_modifier_index(obj, target_modifier)
        current_index = cls._get_modifier_index(obj, mod)
        
        # Перемещаем контроллер после целевого модификатора
        if current_index < target_index:
            # Контроллер находится выше целевого - перемещаем вниз
            steps = target_index - current_index
            for _ in range(steps):
                bpy.ops.object.modifier_move_down({"object": obj}, modifier=mod.name)
        
        return mod, node_group
    
    @classmethod
    def update(cls, obj, controller_modifier, target_modifier):
        """
        Обновляет контроллер.
        
        Args:
            obj: Объект с модификаторами
            controller_modifier: Модификатор-контроллер
            target_modifier: Целевой модификатор
        
        Returns:
            bool: True, если обновление прошло успешно
        """
        # Базовая реализация - просто возвращает True
        return True
    
    @classmethod
    def remove(cls, obj, controller_modifier):
        """
        Удаляет контроллер.
        
        Args:
            obj: Объект с модификатором
            controller_modifier: Модификатор-контроллер
        
        Returns:
            bool: True, если удаление прошло успешно
        """
        try:
            # Получаем группу узлов перед удалением модификатора
            node_group = controller_modifier.node_group
            
            # Удаляем модификатор
            obj.modifiers.remove(controller_modifier)
            
            # Если группа узлов больше не используется, удаляем её
            if node_group and node_group.users == 0:
                bpy.data.node_groups.remove(node_group)
            
            return True
            
        except Exception as e:
            print(f"Error removing controller: {e}")
            return False
    
    @classmethod
    def _create_node_group(cls, obj, target_modifier, **kwargs):
        """
        Создает группу узлов для контроллера.
        Должен быть переопределен в дочерних классах.
        
        Args:
            obj: Объект с модификатором
            target_modifier: Целевой модификатор
            **kwargs: Дополнительные параметры
        
        Returns:
            bpy.types.NodeGroup: Созданная группа узлов или None в случае ошибки
        """
        # Базовая реализация - создает пустую группу
        try:
            node_group = bpy.data.node_groups.new(type='GeometryNodeTree', 
                                                 name=f"{cls.CONTROLLER_NAME} Group")
            
            # Настраиваем интерфейс
            input_socket = node_group.interface.new_socket(
                name="Geometry",
                in_out='INPUT',
                socket_type='NodeSocketGeometry'
            )
            
            output_socket = node_group.interface.new_socket(
                name="Geometry",
                in_out='OUTPUT',
                socket_type='NodeSocketGeometry'
            )
            
            # Создаем узлы
            input_node = node_group.nodes.new('NodeGroupInput')
            input_node.location = Vector((-300, 0))
            
            output_node = node_group.nodes.new('NodeGroupOutput')
            output_node.location = Vector((300, 0))
            
            # Соединяем узлы
            node_group.links.new(input_node.outputs["Geometry"], output_node.inputs["Geometry"])
            
            return node_group
            
        except Exception as e:
            print(f"Error creating controller node group: {e}")
            return None
    
    @classmethod
    def _get_modifier_index(cls, obj, modifier):
        """
        Получает индекс модификатора в стеке модификаторов объекта.
        
        Args:
            obj: Объект с модификаторами
            modifier: Модификатор
        
        Returns:
            int: Индекс модификатора или -1, если не найден
        """
        for i, mod in enumerate(obj.modifiers):
            if mod == modifier:
                return i
        return -1