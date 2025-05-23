"""
Служебные утилиты для работы с клонерами и эффекторами.
"""

import bpy
from .globals import _effector_handler_blocked
from ...models.cloners import CLONER_NODE_GROUP_PREFIXES
from .cloner_effector_utils import apply_effector_to_stacked_cloner, update_cloner_with_effectors

def force_update_cloners(effector_name=None, effector_obj=None):
    """
    Принудительно обновляет все клонеры, связанные с указанным эффектором.
    
    Args:
        effector_name (str, optional): Имя эффектора (модификатора)
        effector_obj (Object, optional): Объект, которому принадлежит эффектор
    
    Returns:
        bool: True, если хотя бы один клонер был обновлен, иначе False
    """
    # Если обработчик заблокирован, не выполняем обновление, чтобы избежать бесконечного цикла
    global _effector_handler_blocked
    if _effector_handler_blocked:
        print("[DEBUG] force_update_cloners: Обработчик заблокирован, пропускаем обновление")
        return False
        
    # Если не указаны аргументы, просто обновляем весь View Layer
    if effector_name is None and effector_obj is None:
        try:
            bpy.context.view_layer.update()
            return True
        except Exception as e:
            print(f"[DEBUG] force_update_cloners: Ошибка при обновлении view_layer: {e}")
            return False
        
    print(f"[DEBUG] force_update_cloners: Принудительное обновление клонеров для эффектора {effector_name}")
    
    # Проверяем существование эффектора
    if not effector_obj or effector_name not in effector_obj.modifiers:
        print(f"[DEBUG] force_update_cloners: Эффектор {effector_name} не найден на объекте {effector_obj.name if effector_obj else 'None'}")
        return False
        
    effector_mod = effector_obj.modifiers[effector_name]
    if not effector_mod.type == 'NODES' or not effector_mod.node_group:
        print(f"[DEBUG] force_update_cloners: Эффектор {effector_name} не является нодовым модификатором или не имеет node_group")
        return False
        
    print(f"[DEBUG] force_update_cloners: Эффектор {effector_name} найден и валиден. Ищем связанные клонеры...")
    
    # Отслеживаем количество обновленных клонеров
    updated_count = 0
    
    # Сначала проверяем объекты, которые могут использовать эффектор локально
    for obj in bpy.data.objects:
        # Пропускаем объекты без модификаторов
        if not obj.modifiers:
            continue
        
        # Ищем клонеры среди модификаторов
        for mod in obj.modifiers:
            if (mod.type == 'NODES' and mod.node_group and 
                any(mod.node_group.name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES)):
                
                # Проверяем, что это клонер и что он связан с эффектором
                linked_effectors = mod.node_group.get("linked_effectors", [])
                if effector_name in linked_effectors:
                    print(f"[DEBUG] force_update_cloners: Найден связанный клонер {mod.name} на объекте {obj.name}")
                    
                    # Проверяем, является ли клонер стековым
                    is_stacked = mod.get("is_stacked_cloner", False) or mod.node_group.get("is_stacked_cloner", False)
                    print(f"[DEBUG] force_update_cloners: Клонер {mod.name} является {'стековым' if is_stacked else 'обычным'}")
                    
                    # Если это стековый клонер, применяем эффектор напрямую
                    if is_stacked:
                        print(f"[DEBUG] force_update_cloners: Применение эффектора {effector_name} к стековому клонеру {mod.name}")
                        success = apply_effector_to_stacked_cloner(obj, mod, effector_mod)
                        print(f"[DEBUG] force_update_cloners: Результат применения: {'Успешно' if success else 'Ошибка'}")
                        
                        # Обновляем модификатор, чтобы отобразить изменения
                        try:
                            mod.show_viewport = False
                            mod.show_viewport = True
                            obj.update_tag(refresh={'OBJECT'})
                            print(f"[DEBUG] force_update_cloners: Принудительное обновление клонера {mod.name}")
                            updated_count += 1
                        except Exception as e:
                            print(f"[DEBUG] force_update_cloners: Ошибка при обновлении модификатора: {e}")
                    
                    # Для всех типов клонеров вызываем обновление
                    print(f"[DEBUG] force_update_cloners: Вызов update_cloner_with_effectors для клонера {mod.name}")
                    update_cloner_with_effectors(obj, mod)
                    updated_count += 1
    
    # Принудительное обновление view_layer для перерисовки изменений
    try:
        bpy.context.view_layer.update()
        print(f"[DEBUG] force_update_cloners: Обновлен view_layer")
    except Exception as e:
        print(f"[DEBUG] force_update_cloners: Ошибка при обновлении view_layer: {e}")
    
    print(f"[DEBUG] force_update_cloners: Обновлено {updated_count} клонеров")
    return updated_count > 0 