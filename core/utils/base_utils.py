"""
Базовые утилиты для работы с клонерами.
"""

import bpy
from ...models.cloners import CLONER_NODE_GROUP_PREFIXES

def convert_array_to_tuple(array):
    """
    Преобразует bpy_prop_array или аналогичный тип массива в кортеж Python.
    
    Args:
        array: Массив значений, который нужно преобразовать
        
    Returns:
        tuple: Кортеж из значений массива или (0,0,0) в случае ошибки
    """
    # Проверяем, что это bpy_prop_array или что-то подобное
    if hasattr(array, "__len__") and hasattr(array, "__getitem__"):
        try:
            # Напрямую доступ к элементам
            return tuple(float(array[i]) for i in range(len(array)))
        except:
            # Запасной вариант - преобразование через строку
            try:
                str_val = str(array)
                # Обычно выводится как "Vector((x, y, z))" или просто "(x, y, z)"
                if "(" in str_val and ")" in str_val:
                    # Извлекаем значения внутри скобок
                    inner = str_val[str_val.find("(")+1:str_val.rfind(")")]
                    # Удаляем возможные внутренние скобки
                    inner = inner.replace("(", "").replace(")", "")
                    # Разделяем по запятой и преобразуем в числа
                    values = [float(v.strip()) for v in inner.split(",") if v.strip()]
                    if len(values) >= 3:
                        return (values[0], values[1], values[2])
            except:
                pass
    # Если не удалось преобразовать, возвращаем (0,0,0)
    return (0.0, 0.0, 0.0)

def get_active_cloner(obj):
    """
    Получает активный модификатор клонера для объекта.
    
    Args:
        obj (bpy.types.Object): Объект, для которого нужно получить активный клонер
        
    Returns:
        bpy.types.Modifier: Активный модификатор клонера или None, если не найден
    """
    if not obj:
        return None
        
    # Проверяем свойство active_cloner_name в объекте
    active_cloner_name = obj.get("active_cloner_name", "")
    if active_cloner_name and active_cloner_name in obj.modifiers:
        mod = obj.modifiers[active_cloner_name]
        if mod.type == 'NODES' and mod.node_group:
            # Проверяем, что это действительно клонер
            for prefix in CLONER_NODE_GROUP_PREFIXES:
                if prefix in mod.node_group.name:
                    return mod
    
    # Если active_cloner_name не установлен или недействителен,
    # ищем первый модификатор клонера
    for mod in obj.modifiers:
        if mod.type == 'NODES' and mod.node_group:
            for prefix in CLONER_NODE_GROUP_PREFIXES:
                if prefix in mod.node_group.name:
                    # Запомним этот клонер как активный
                    obj["active_cloner_name"] = mod.name
                    return mod
    
    return None 