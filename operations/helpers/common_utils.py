import bpy

def find_layer_collection(layer_coll, coll_name):
    """
    Рекурсивно находит layer_collection по имени коллекции.
    
    Args:
        layer_coll: Исходная layer_collection для поиска
        coll_name: Имя коллекции для поиска
    
    Returns:
        layer_collection или None если не найдена
    """
    if layer_coll.collection.name == coll_name:
        return layer_coll
    for child in layer_coll.children:
        result = find_layer_collection(child, coll_name)
        if result:
            return result
    return None

def register_chain_update(previous_cloner_object, cloner_obj):
    """
    Регистрирует обновление цепочки клонеров.
    Эта функция используется для обновления зависимостей между клонерами в цепочке.
    
    Args:
        previous_cloner_object: Предыдущий объект в цепочке
        cloner_obj: Текущий объект клонера
    
    Returns:
        None
    """
    try:
        # Импортируем только здесь для избегания циклических импортов
        from ...core.utils.cloner_utils import get_cloner_chain_for_object
        
        # Определяем, нужно ли строить цепочку вручную или использовать get_cloner_chain_for_object
        is_collection_chain = hasattr(previous_cloner_object, 'modifiers') and any(
            mod.get('is_collection_chain', False) for mod in previous_cloner_object.modifiers if hasattr(mod, 'get')
        )
        
        if is_collection_chain:
            # Для коллекций цепочку нужно строить вручную
            chain = []
            current_obj = previous_cloner_object
            while current_obj:
                chain.append(current_obj)
                # Ищем предыдущий объект в цепочке
                prev_name = None
                for mod in current_obj.modifiers:
                    if mod.type == 'NODES' and mod.get("previous_cloner_object"):
                        prev_name = mod.get("previous_cloner_object")
                        break
                
                if prev_name and prev_name in bpy.data.objects:
                    current_obj = bpy.data.objects[prev_name]
                else:
                    current_obj = None
        else:
            # Находим все предыдущие клонеры в цепочке
            chain = get_cloner_chain_for_object(previous_cloner_object)
        
        # Обновляем всю цепочку
        for chain_obj in chain:
            # Проверяем, является ли chain_obj объектом Blender или словарем
            if hasattr(chain_obj, 'name') and chain_obj.name != cloner_obj.name:
                # Добавляем этот клонер в список цепочки всех предыдущих
                for mod in chain_obj.modifiers:
                    if mod.type == 'NODES' and mod.get("is_chained_cloner"):
                        if "next_cloners" not in mod:
                            mod["next_cloners"] = []
                        if cloner_obj.name not in mod["next_cloners"]:
                            mod["next_cloners"].append(cloner_obj.name)
            elif isinstance(chain_obj, dict) and chain_obj.get('name') != cloner_obj.name:
                # Обработка случая, когда chain_obj является словарем
                print(f"Обнаружен chain_obj типа dict: {chain_obj}")
    except Exception as e:
        print(f"Ошибка при регистрации цепочки обновлений: {e}")
    
    # Принудительное обновление
    bpy.context.view_layer.update()
    return None  # Запуск только один раз
