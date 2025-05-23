"""
Фабрика для создания компонентов аддона.
"""

import bpy
from typing import Optional
from ...models.cloners import AVAILABLE_CLONERS, NODE_GROUP_CREATORS, CLONER_GROUP_NAMES
from ...models.effectors import AVAILABLE_EFFECTORS, EFFECTOR_CREATORS, EFFECTOR_GROUP_NAMES
from ...models.fields import AVAILABLE_FIELDS, FIELD_CREATORS, FIELD_GROUP_NAMES
from ..utils.node_utils import create_independent_node_group

class ComponentFactory:
    """
    Фабрика для создания компонентов аддона (клонеров, эффекторов, полей).
    Обеспечивает единый интерфейс для создания всех типов компонентов.
    """
    
    @classmethod
    def create_cloner(cls, cloner_type: str, use_custom_group: bool = True, **kwargs) -> Optional[bpy.types.NodeGroup]:
        """
        Создает группу узлов клонера указанного типа.
        
        Args:
            cloner_type: Тип клонера (например, 'GRID', 'LINEAR', 'CIRCLE')
            use_custom_group: Использовать ли уникальную группу для каждого экземпляра
            **kwargs: Дополнительные параметры для создания клонера
        
        Returns:
            Созданная группа узлов или None, если создание не удалось
        """
        # Проверяем, есть ли такой тип клонера
        if cloner_type not in AVAILABLE_CLONERS:
            print(f"Unknown cloner type: {cloner_type}")
            return None
        
        # Получаем класс клонера и имена
        cloner_class = AVAILABLE_CLONERS[cloner_type]
        base_node_name = CLONER_GROUP_NAMES[cloner_type]
        
        # Создаем группу узлов
        if use_custom_group:
            # Если указан объект для создания уникального суффикса
            obj = kwargs.get('obj')
            suffix = ""
            if obj:
                suffix = f".{obj.name}.{hash(obj.name) % 1000:03d}"
            
            # Создаем группу с суффиксом
            node_group = cloner_class.create_node_group(name_suffix=suffix)
        else:
            # Используем традиционный метод с шаблоном
            creator_func = NODE_GROUP_CREATORS[cloner_type]
            
            # Создаем независимую копию шаблона
            node_group = create_independent_node_group(creator_func, base_node_name)
        
        return node_group
    
    @classmethod
    def create_effector(cls, effector_type: str, use_custom_group: bool = True, **kwargs) -> Optional[bpy.types.NodeGroup]:
        """
        Создает группу узлов эффектора указанного типа.
        
        Args:
            effector_type: Тип эффектора (например, 'RANDOM', 'NOISE')
            use_custom_group: Использовать ли уникальную группу для каждого экземпляра
            **kwargs: Дополнительные параметры для создания эффектора
        
        Returns:
            Созданная группа узлов или None, если создание не удалось
        """
        # Проверяем, есть ли такой тип эффектора
        if effector_type not in EFFECTOR_CREATORS:
            print(f"Unknown effector type: {effector_type}")
            return None
        
        base_node_name = EFFECTOR_GROUP_NAMES[effector_type]
        
        # Создаем группу узлов
        if use_custom_group:
            # Получаем класс эффектора по типу
            effector_class = AVAILABLE_EFFECTORS[effector_type]
            
            # Если класс найден, создаем группу узлов через него
            if effector_class:
                # Если указан объект для создания уникального суффикса
                obj = kwargs.get('obj')
                suffix = ""
                if obj:
                    suffix = f".{obj.name}.{hash(obj.name) % 1000:03d}"
                
                # Создаем группу с суффиксом
                node_group = effector_class.create_node_group(name_suffix=suffix)
            else:
                # Fallback к стандартному методу
                creator_func = EFFECTOR_CREATORS[effector_type]
                
                # Создаем независимую копию шаблона
                node_group = create_independent_node_group(creator_func, base_node_name)
        else:
            # Используем стандартный подход
            creator_func = EFFECTOR_CREATORS[effector_type]
            
            # Создаем независимую копию шаблона
            node_group = create_independent_node_group(creator_func, base_node_name)
        
        return node_group
    
    @classmethod
    def create_field(cls, field_type: str, use_custom_group: bool = True, **kwargs) -> Optional[bpy.types.NodeGroup]:
        """
        Создает группу узлов поля указанного типа.
        
        Args:
            field_type: Тип поля (например, 'SPHERE')
            use_custom_group: Использовать ли уникальную группу для каждого экземпляра
            **kwargs: Дополнительные параметры для создания поля
        
        Returns:
            Созданная группа узлов или None, если создание не удалось
        """
        # Проверяем, есть ли такой тип поля
        if field_type not in FIELD_CREATORS:
            print(f"Unknown field type: {field_type}")
            return None
        
        base_node_name = FIELD_GROUP_NAMES[field_type]
        field_class = AVAILABLE_FIELDS[field_type]
        
        # Создаем группу узлов
        if use_custom_group:
            # Если указан объект для создания уникального суффикса
            obj = kwargs.get('obj')
            suffix = ""
            if obj:
                suffix = f".{obj.name}.{hash(obj.name) % 1000:03d}"
            
            # Создаем группу с суффиксом
            node_group = field_class.create_node_group(name_suffix=suffix)
        else:
            # Используем традиционный метод с шаблоном
            creator_func = FIELD_CREATORS[field_type]
            
            # Создаем независимую копию шаблона
            node_group = create_independent_node_group(creator_func, base_node_name)
        
        return node_group 