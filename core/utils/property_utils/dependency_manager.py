"""
Менеджер зависимостей для компонентов аддона.
Управляет связями между клонерами, эффекторами и полями.
"""

import bpy
from typing import List, Dict, Optional, Any, Union

class ComponentDependencyManager:
    """
    Управляет связями между компонентами аддона (клонерами, эффекторами, полями).
    Отслеживает зависимости и обновляет компоненты при изменении параметров.
    """
    
    def __init__(self):
        self.cloner_effector_map = {}  # Связь клонеров с эффекторами
        self.effector_field_map = {}   # Связь эффекторов с полями
    
    def link_effector_to_cloner(self, cloner_mod: bpy.types.Modifier, effector_mod: bpy.types.Modifier) -> bool:
        """
        Связывает эффектор с клонером.
        
        Args:
            cloner_mod: Модификатор клонера
            effector_mod: Модификатор эффектора
            
        Returns:
            bool: True, если связь успешно создана
        """
        if cloner_mod.name not in self.cloner_effector_map:
            self.cloner_effector_map[cloner_mod.name] = []
        
        if effector_mod.name not in self.cloner_effector_map[cloner_mod.name]:
            self.cloner_effector_map[cloner_mod.name].append(effector_mod.name)
            return True
        return False
    
    def unlink_effector_from_cloner(self, cloner_mod: bpy.types.Modifier, effector_mod: bpy.types.Modifier) -> bool:
        """
        Разрывает связь эффектора с клонером.
        
        Args:
            cloner_mod: Модификатор клонера
            effector_mod: Модификатор эффектора
            
        Returns:
            bool: True, если связь успешно разорвана
        """
        if cloner_mod.name in self.cloner_effector_map:
            if effector_mod.name in self.cloner_effector_map[cloner_mod.name]:
                self.cloner_effector_map[cloner_mod.name].remove(effector_mod.name)
                return True
        return False
    
    def link_field_to_effector(self, effector_mod: bpy.types.Modifier, field_mod: bpy.types.Modifier) -> bool:
        """
        Связывает поле с эффектором.
        
        Args:
            effector_mod: Модификатор эффектора
            field_mod: Модификатор поля
            
        Returns:
            bool: True, если связь успешно создана
        """
        if effector_mod.name not in self.effector_field_map:
            self.effector_field_map[effector_mod.name] = []
        
        if field_mod.name not in self.effector_field_map[effector_mod.name]:
            self.effector_field_map[effector_mod.name].append(field_mod.name)
            return True
        return False
    
    def unlink_field_from_effector(self, effector_mod: bpy.types.Modifier, field_mod: bpy.types.Modifier) -> bool:
        """
        Разрывает связь поля с эффектором.
        
        Args:
            effector_mod: Модификатор эффектора
            field_mod: Модификатор поля
            
        Returns:
            bool: True, если связь успешно разорвана
        """
        if effector_mod.name in self.effector_field_map:
            if field_mod.name in self.effector_field_map[effector_mod.name]:
                self.effector_field_map[effector_mod.name].remove(field_mod.name)
                return True
        return False
    
    def get_effectors_for_cloner(self, obj: bpy.types.Object, cloner_mod: bpy.types.Modifier) -> List[bpy.types.Modifier]:
        """
        Получает все эффекторы, связанные с клонером.
        
        Args:
            obj: Объект с модификаторами
            cloner_mod: Модификатор клонера
            
        Returns:
            list: Список эффекторов
        """
        if cloner_mod.name in self.cloner_effector_map:
            return [obj.modifiers.get(name) for name in self.cloner_effector_map[cloner_mod.name] 
                   if name in obj.modifiers]
        return []
    
    def get_fields_for_effector(self, obj: bpy.types.Object, effector_mod: bpy.types.Modifier) -> List[bpy.types.Modifier]:
        """
        Получает все поля, связанные с эффектором.
        
        Args:
            obj: Объект с модификаторами
            effector_mod: Модификатор эффектора
            
        Returns:
            list: Список полей
        """
        if effector_mod.name in self.effector_field_map:
            return [obj.modifiers.get(name) for name in self.effector_field_map[effector_mod.name] 
                   if name in obj.modifiers]
        return []
    
    def update_after_modifier_rename(self, obj: bpy.types.Object, old_name: str, new_name: str) -> None:
        """
        Обновляет связи после переименования модификатора.
        
        Args:
            obj: Объект с модификаторами
            old_name: Старое имя модификатора
            new_name: Новое имя модификатора
        """
        # Обновление ключей в словаре клонеров
        if old_name in self.cloner_effector_map:
            effectors = self.cloner_effector_map.pop(old_name)
            self.cloner_effector_map[new_name] = effectors
        
        # Обновление значений в словаре клонеров
        for cloner_name, effectors in self.cloner_effector_map.items():
            if old_name in effectors:
                effectors.remove(old_name)
                effectors.append(new_name)
                self.cloner_effector_map[cloner_name] = effectors
        
        # Обновление ключей в словаре эффекторов
        if old_name in self.effector_field_map:
            fields = self.effector_field_map.pop(old_name)
            self.effector_field_map[new_name] = fields
        
        # Обновление значений в словаре эффекторов
        for effector_name, fields in self.effector_field_map.items():
            if old_name in fields:
                fields.remove(old_name)
                fields.append(new_name)
                self.effector_field_map[effector_name] = fields
    
    def update_after_modifier_removal(self, obj: bpy.types.Object, modifier_name: str) -> None:
        """
        Обновляет связи после удаления модификатора.
        
        Args:
            obj: Объект с модификаторами
            modifier_name: Имя удаляемого модификатора
        """
        # Удаление из словаря клонеров
        if modifier_name in self.cloner_effector_map:
            del self.cloner_effector_map[modifier_name]
        
        # Удаление из значений в словаре клонеров
        for cloner_name, effectors in list(self.cloner_effector_map.items()):
            if modifier_name in effectors:
                effectors.remove(modifier_name)
                self.cloner_effector_map[cloner_name] = effectors
        
        # Удаление из словаря эффекторов
        if modifier_name in self.effector_field_map:
            del self.effector_field_map[modifier_name]
        
        # Удаление из значений в словаре эффекторов
        for effector_name, fields in list(self.effector_field_map.items()):
            if modifier_name in fields:
                fields.remove(modifier_name)
                self.effector_field_map[effector_name] = fields
    
    def save_to_object(self, obj: bpy.types.Object) -> None:
        """
        Сохраняет данные зависимостей в объекте для последующего восстановления.
        
        Args:
            obj: Объект для сохранения данных
        """
        import json
        
        # Преобразуем словари в строки JSON
        cloner_data = json.dumps(self.cloner_effector_map)
        effector_data = json.dumps(self.effector_field_map)
        
        # Сохраняем данные в кастомных свойствах объекта
        obj["cloner_effector_map"] = cloner_data
        obj["effector_field_map"] = effector_data
    
    def load_from_object(self, obj: bpy.types.Object) -> None:
        """
        Загружает данные зависимостей из объекта.
        
        Args:
            obj: Объект для загрузки данных
        """
        import json
        
        # Загружаем данные из кастомных свойств объекта
        if "cloner_effector_map" in obj:
            try:
                self.cloner_effector_map = json.loads(obj["cloner_effector_map"])
            except:
                self.cloner_effector_map = {}
        
        if "effector_field_map" in obj:
            try:
                self.effector_field_map = json.loads(obj["effector_field_map"])
            except:
                self.effector_field_map = {}
    
    def clear(self) -> None:
        """
        Очищает все связи.
        """
        self.cloner_effector_map = {}
        self.effector_field_map = {}

# Создаем глобальный экземпляр для использования во всем аддоне
dependency_manager = ComponentDependencyManager()
