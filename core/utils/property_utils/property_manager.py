"""
Система параметризации компонентов аддона через кастомные свойства.
Позволяет добавлять новые параметры к существующим компонентам без изменения их внутренней структуры.
"""

import bpy
import json
from typing import Dict, List, Any, Optional, Union, Tuple


class ComponentPropertyManager:
    """
    Менеджер для управления кастомными свойствами компонентов.
    Позволяет добавлять, получать и обновлять динамические свойства компонентов аддона.
    """
    
    # Реестр определенных типов свойств
    _property_types = {}
    
    # Реестр обновляющих функций для свойств
    _update_callbacks = {}
    
    @classmethod
    def register_property_type(cls, property_id: str, property_definition: Dict[str, Any]):
        """
        Регистрирует новый тип свойства.
        
        Args:
            property_id: Уникальный идентификатор типа свойства
            property_definition: Определение свойства для bpy.props
        """
        cls._property_types[property_id] = property_definition
        print(f"Registered property type: {property_id}")
    
    @classmethod
    def register_update_callback(cls, property_id: str, component_type: str, callback):
        """
        Регистрирует функцию обратного вызова для обновления компонента.
        
        Args:
            property_id: Идентификатор свойства
            component_type: Тип компонента (например, 'grid_cloner', 'random_effector')
            callback: Функция обратного вызова
        """
        key = f"{component_type}.{property_id}"
        cls._update_callbacks[key] = callback
        print(f"Registered update callback for {key}")
    
    @classmethod
    def add_property_group_to_object(cls, obj, group_id: str, display_name: str):
        """
        Добавляет группу свойств к объекту, если она еще не существует.
        
        Args:
            obj: Объект Blender
            group_id: Идентификатор группы свойств
            display_name: Имя для отображения
        
        Returns:
            str: Полный ID для доступа к группе
        """
        # Формируем полный ID
        full_id = f"advanced_cloners_{group_id}"
        
        # Проверяем, существует ли уже такая группа
        if hasattr(bpy.types, full_id):
            return full_id
        
        # Создаем класс группы свойств
        property_group = type(
            full_id,
            (bpy.types.PropertyGroup,),
            {
                "display_name": display_name,
                "properties": {}
            }
        )
        
        # Регистрируем группу
        bpy.utils.register_class(property_group)
        
        # Добавляем свойство к типу объекта
        setattr(bpy.types.Object, full_id, bpy.props.PointerProperty(type=property_group))
        
        return full_id
    
    @classmethod
    def add_property_to_group(cls, obj, group_id: str, property_id: str, 
                              property_type: str, component_name: str,
                              property_name: str = None, **kwargs):
        """
        Добавляет свойство к группе свойств объекта.
        
        Args:
            obj: Объект Blender
            group_id: ID группы свойств
            property_id: ID свойства
            property_type: Тип свойства (из зарегистрированных типов)
            component_name: Имя компонента (модификатора), к которому привязано свойство
            property_name: Имя свойства для отображения (если не указано, используется property_id)
            **kwargs: Дополнительные параметры для определения свойства
        
        Returns:
            bool: True, если свойство успешно добавлено
        """
        # Формируем полный ID группы
        full_group_id = f"advanced_cloners_{group_id}"
        
        # Проверяем, существует ли группа
        if not hasattr(bpy.types, full_group_id):
            print(f"Property group {full_group_id} does not exist")
            return False
        
        # Получаем класс группы
        group_class = getattr(bpy.types, full_group_id)
        
        # Формируем ID свойства
        full_property_id = f"{property_id}_{component_name}"
        
        # Проверяем, существует ли уже такое свойство
        if hasattr(group_class, full_property_id):
            print(f"Property {full_property_id} already exists in group {full_group_id}")
            return True
        
        # Проверяем, зарегистрирован ли запрошенный тип свойства
        if property_type not in cls._property_types:
            print(f"Unknown property type: {property_type}")
            return False
        
        # Получаем определение свойства
        property_def = cls._property_types[property_type].copy()
        
        # Обновляем определение свойства с переданными параметрами
        property_def.update(kwargs)
        
        # Если есть функция обновления для этого типа свойства и компонента
        component_type = cls._get_component_type(obj, component_name)
        update_key = f"{component_type}.{property_id}"
        
        if update_key in cls._update_callbacks:
            # Создаем замыкание для функции обновления
            def create_update_function(obj_ref, mod_name, callback):
                def update_function(self, context):
                    # Находим объект и модификатор
                    if obj_ref and mod_name in obj_ref.modifiers:
                        modifier = obj_ref.modifiers[mod_name]
                        # Вызываем функцию обновления
                        callback(obj_ref, modifier, self)
                return update_function
            
            # Добавляем функцию обновления к определению свойства
            property_def["update"] = create_update_function(
                obj, component_name, cls._update_callbacks[update_key]
            )
        
        # Имя свойства для отображения
        display_name = property_name or property_id.replace("_", " ").title()
        
        # Создаем свойство
        setattr(group_class, full_property_id, property_def)
        
        # Добавляем информацию о свойстве в список свойств группы
        if not hasattr(group_class, "properties"):
            group_class.properties = {}
        
        group_class.properties[full_property_id] = {
            "id": property_id,
            "name": display_name,
            "type": property_type,
            "component": component_name
        }
        
        # Проверяем, что группа присутствует на объекте
        if not hasattr(obj, full_group_id):
            print(f"Object does not have property group {full_group_id}")
            return False
        
        return True
    
    @classmethod
    def get_property(cls, obj, group_id: str, property_id: str, component_name: str):
        """
        Получает значение кастомного свойства компонента.
        
        Args:
            obj: Объект Blender
            group_id: ID группы свойств
            property_id: ID свойства
            component_name: Имя компонента (модификатора)
        
        Returns:
            Any: Значение свойства или None, если свойство не найдено
        """
        # Формируем полный ID группы
        full_group_id = f"advanced_cloners_{group_id}"
        
        # Формируем ID свойства
        full_property_id = f"{property_id}_{component_name}"
        
        # Проверяем, существует ли группа и свойство
        if not hasattr(obj, full_group_id):
            print(f"Object does not have property group {full_group_id}")
            return None
        
        group = getattr(obj, full_group_id)
        
        if not hasattr(group, full_property_id):
            print(f"Property group does not have property {full_property_id}")
            return None
        
        # Возвращаем значение свойства
        return getattr(group, full_property_id)
    
    @classmethod
    def set_property(cls, obj, group_id: str, property_id: str, component_name: str, value):
        """
        Устанавливает значение кастомного свойства компонента.
        
        Args:
            obj: Объект Blender
            group_id: ID группы свойств
            property_id: ID свойства
            component_name: Имя компонента (модификатора)
            value: Новое значение свойства
        
        Returns:
            bool: True, если значение успешно установлено
        """
        # Формируем полный ID группы
        full_group_id = f"advanced_cloners_{group_id}"
        
        # Формируем ID свойства
        full_property_id = f"{property_id}_{component_name}"
        
        # Проверяем, существует ли группа и свойство
        if not hasattr(obj, full_group_id):
            print(f"Object does not have property group {full_group_id}")
            return False
        
        group = getattr(obj, full_group_id)
        
        if not hasattr(group, full_property_id):
            print(f"Property group does not have property {full_property_id}")
            return False
        
        # Устанавливаем значение свойства
        try:
            setattr(group, full_property_id, value)
            return True
        except Exception as e:
            print(f"Error setting property value: {e}")
            return False
    
    @classmethod
    def remove_property_group(cls, group_id: str):
        """
        Удаляет группу свойств.
        
        Args:
            group_id: ID группы свойств
        
        Returns:
            bool: True, если группа успешно удалена
        """
        # Формируем полный ID группы
        full_group_id = f"advanced_cloners_{group_id}"
        
        # Проверяем, существует ли группа
        if not hasattr(bpy.types, full_group_id):
            print(f"Property group {full_group_id} does not exist")
            return False
        
        # Получаем класс группы
        group_class = getattr(bpy.types, full_group_id)
        
        # Удаляем свойство из типа объекта
        delattr(bpy.types.Object, full_group_id)
        
        # Отменяем регистрацию класса группы
        bpy.utils.unregister_class(group_class)
        
        return True
    
    @classmethod
    def _get_component_type(cls, obj, component_name: str) -> str:
        """
        Определяет тип компонента по его имени.
        
        Args:
            obj: Объект Blender
            component_name: Имя компонента (модификатора)
        
        Returns:
            str: Тип компонента или 'unknown'
        """
        if component_name not in obj.modifiers:
            return 'unknown'
        
        mod = obj.modifiers[component_name]
        
        if not hasattr(mod, "node_group") or not mod.node_group:
            return 'unknown'
        
        # Пытаемся определить тип по имени группы узлов
        node_group_name = mod.node_group.name.lower()
        
        if 'grid' in node_group_name and 'cloner' in node_group_name:
            return 'grid_cloner'
        elif 'linear' in node_group_name and 'cloner' in node_group_name:
            return 'linear_cloner'
        elif 'circle' in node_group_name and 'cloner' in node_group_name:
            return 'circle_cloner'
        elif 'random' in node_group_name and 'effector' in node_group_name:
            return 'random_effector'
        elif 'noise' in node_group_name and 'effector' in node_group_name:
            return 'noise_effector'
        
        # Если не удалось определить по имени, пытаемся получить из метаданных
        metadata_str = mod.node_group.get("metadata", "{}")
        try:
            metadata = json.loads(metadata_str)
            if "type" in metadata:
                return metadata["type"].lower()
        except (json.JSONDecodeError, KeyError):
            pass
        
        return 'unknown'


# Регистрируем стандартные типы свойств
ComponentPropertyManager.register_property_type(
    "float",
    bpy.props.FloatProperty(
        name="Float Value",
        description="Floating point value",
        default=0.0,
        min=-1000.0,
        max=1000.0
    )
)

ComponentPropertyManager.register_property_type(
    "int",
    bpy.props.IntProperty(
        name="Integer Value",
        description="Integer value",
        default=0,
        min=-1000,
        max=1000
    )
)

ComponentPropertyManager.register_property_type(
    "bool",
    bpy.props.BoolProperty(
        name="Boolean Value",
        description="Boolean value",
        default=False
    )
)

ComponentPropertyManager.register_property_type(
    "vector",
    bpy.props.FloatVectorProperty(
        name="Vector Value",
        description="Vector value",
        default=(0.0, 0.0, 0.0),
        size=3
    )
)

ComponentPropertyManager.register_property_type(
    "color",
    bpy.props.FloatVectorProperty(
        name="Color Value",
        description="Color value",
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        subtype='COLOR'
    )
)

ComponentPropertyManager.register_property_type(
    "enum",
    bpy.props.EnumProperty(
        name="Enum Value",
        description="Enumeration value",
        items=[
            ('OPTION1', "Option 1", "First option"),
            ('OPTION2', "Option 2", "Second option"),
            ('OPTION3', "Option 3", "Third option")
        ],
        default='OPTION1'
    )
)


# UI-класс для отображения кастомных свойств
class CUSTOM_PT_properties_panel(bpy.types.Panel):
    """Панель для отображения кастомных свойств компонентов"""
    bl_label = "Extra Properties"
    bl_idname = "CUSTOM_PT_properties_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cloners'
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        # Перебираем все группы свойств объекта
        for attr in dir(obj):
            if attr.startswith('advanced_cloners_'):
                group_id = attr
                group = getattr(obj, group_id)
                
                # Проверяем, есть ли у группы атрибут display_name
                group_cls = getattr(bpy.types, group_id)
                if hasattr(group_cls, 'display_name'):
                    box = layout.box()
                    box.label(text=group_cls.display_name)
                    
                    # Перебираем все свойства группы
                    if hasattr(group_cls, 'properties'):
                        for prop_id, prop_info in group_cls.properties.items():
                            # Проверяем, относится ли свойство к активному компоненту
                            component_name = prop_info.get('component', '')
                            if component_name in obj.modifiers:
                                row = box.row()
                                row.label(text=prop_info.get('name', prop_id))
                                row.prop(group, prop_id, text="")


# Функция регистрации
def register():
    bpy.utils.register_class(CUSTOM_PT_properties_panel)

# Функция отмены регистрации
def unregister():
    bpy.utils.unregister_class(CUSTOM_PT_properties_panel)