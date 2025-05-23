import bpy
from ...core.utils.node_utils import find_socket_by_name

from .common_utils import find_layer_collection

def delete_cloner(context, obj, modifier_name):
    """
    Удаляет клонер с заданным именем модификатора.
    
    Args:
        context: Контекст Blender
        obj: Объект, содержащий модификатор клонера
        modifier_name: Имя модификатора клонера для удаления
        
    Returns:
        tuple: (bool, str) где bool - True если клонер успешно удален, 
               str - имя предыдущего объекта в цепочке или None
    """
    print(f"[DELETE] Начинаем удаление клонера {modifier_name} с объекта {obj.name}")
    
    # Переменная для хранения предыдущего объекта в цепочке
    previous_obj_name = None
    
    if not obj or modifier_name not in obj.modifiers:
        print(f"[DELETE] Ошибка: Объект {obj} или модификатор {modifier_name} не найден")
        return False, None
    
    # ВАЖНО: ищем предыдущий объект в цепочке ДО удаления текущего
    try:
        modifier = obj.modifiers[modifier_name]
        
        # Ищем предыдущий объект по метаданным модификатора
        if "previous_cloner_object" in modifier:
            previous_obj_name = modifier["previous_cloner_object"]
            print(f"[DELETE] Найден предыдущий объект в цепочке через метаданные: {previous_obj_name}")
        
        # Если нет прямой ссылки и объект в цепочке, пытаемся определить по имени
        if not previous_obj_name and obj.name.startswith("Cloner_") and "_" in obj.name:
            parts = obj.name.split("_")
            if len(parts) > 2:
                base_name = "_".join(parts[:-1])
                if base_name in bpy.data.objects:
                    previous_obj_name = base_name
                    print(f"[DELETE] Определен предыдущий объект по имени: {previous_obj_name}")
    except Exception as e:
        print(f"[DELETE] Ошибка при поиске предыдущего объекта: {e}")
        # Продолжаем выполнение, так как поиск предыдущего объекта - необязательная операция

    # Сохраняем имя объекта в начале операции для использования в timer callback
    cloner_obj_name = obj.name
    print(f"[DELETE] Сохранили имя объекта: {cloner_obj_name}")
    
    # Находим все клонеры на объекте, чтобы выбрать предыдущий после удаления
    all_cloners = []
    current_index = -1
    
    # Удаляем лишний try без except
    for i, mod in enumerate(obj.modifiers):
        if mod.type == 'NODES' and mod.node_group:
            # Проверка префикса имени группы узлов
            is_cloner = False
            from ...models.cloners import CLONER_NODE_GROUP_PREFIXES
            
            # Проверяем, является ли модификатор клонером
            if any(mod.node_group.name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES):
                is_cloner = True
            
            # Дополнительная проверка для клонеров коллекций и пользовательских групп
            if not is_cloner and ("Cloner" in mod.node_group.name or mod.name.endswith("_Cloner")):
                is_cloner = True
            
            # Проверка флага стекового клонера
            if not is_cloner and mod.get("is_stacked_cloner", False):
                is_cloner = True
            
            if is_cloner:
                all_cloners.append(mod.name)
                if mod.name == modifier_name:
                    current_index = len(all_cloners) - 1
    
    print(f"[DELETE] Найдено {len(all_cloners)} клонеров, удаляемый клонер имеет индекс {current_index}")
    
    modifier = obj.modifiers[modifier_name]
    print(f"[DELETE] Получили модификатор {modifier_name}")
    
    # Сохраняем ссылку на node_group, но не используем её напрямую пока
    node_group_name = None
    if modifier.node_group:
        node_group_name = modifier.node_group.name
        print(f"[DELETE] Группа узлов: {node_group_name}")
    
    # Determine source type (object or collection)
    source_type = modifier.get("source_type", "OBJECT")
    print(f"[DELETE] Тип источника: {source_type}")
    
    # Проверка стекового клонера (используем другую логику удаления)
    is_stacked_cloner = modifier.get("is_stacked_cloner", False)
    print(f"[DELETE] Стековый клонер: {is_stacked_cloner}")
    
    # ВАЖНО: перемещаем логику выбора следующего клонера сюда, ДО удаления объекта и модификатора
    # Выбираем предыдущий клонер, если он есть
    previous_obj = None  # Переменная для хранения объекта, который будет выбран после удаления
    
    if all_cloners and current_index >= 0:
        # Определяем, какой клонер выбрать после удаления
        if current_index > 0:
            # Выбираем предыдущий клонер
            next_cloner_index = current_index - 1
        else:
            # Если удаляемый клонер был первым и есть другие клонеры, выбираем следующий
            next_cloner_index = 0 if len(all_cloners) > 1 else -1
        
        # Обновляем список клонеров после удаления
        if modifier_name in all_cloners:
            all_cloners.remove(modifier_name)
        
        if next_cloner_index >= 0 and next_cloner_index < len(all_cloners):
            next_cloner = all_cloners[next_cloner_index]
            print(f"[DELETE] Выбираем следующий клонер: {next_cloner}")
            
            # Запоминаем текущий объект для выделения
            previous_obj = obj
            
            # Устанавливаем его активным для UI
            if hasattr(context.scene, "active_cloner_in_chain"):
                context.scene.active_cloner_in_chain = f"{obj.name}|{next_cloner}"
                print(f"[DELETE] Установлен активный клонер в цепочке: {obj.name}|{next_cloner}")
    
    # Дополнительная проверка для цепочки клонеров
    # Если это объект в цепочке клонеров, найдем его предыдущий клонер
    elif obj.name.startswith("Cloner_") and hasattr(context.scene, "active_cloner_in_chain"):
        print(f"[DELETE] Объект {obj.name} является частью цепочки клонеров")
        
        # Проверяем, есть ли у модификатора информация о предыдущем клонере
        if "previous_cloner_object" in modifier:
            previous_obj_name = modifier["previous_cloner_object"]
            print(f"[DELETE] Найден предыдущий объект в цепочке: {previous_obj_name}")
    
    # Здесь был проблемный try без except - удаляем его
    # Основная логика удаления клонера остается без изменений
    # Вместо этого оборачиваем всю оставшуюся логику в один try-except блок
    try:
        # Здесь начинается остальная логика удаления клонера
        if is_stacked_cloner:
            # Для стековых клонеров просто удаляем модификатор и группу узлов
            print(f"[DELETE] Удаление стекового клонера {modifier_name}")
            
            # Удаляем node group если она больше не используется
            if node_group_name and node_group_name in bpy.data.node_groups:
                node_group = bpy.data.node_groups[node_group_name]
                if node_group.users <= 1:
                    try:
                        print(f"[DELETE] Удаляем группу узлов {node_group_name}")
                        bpy.data.node_groups.remove(node_group)
                    except Exception as e:
                        print(f"[DELETE] Ошибка при удалении группы узлов: {e}")
            
            # Удаляем модификатор
            try:
                print(f"[DELETE] Удаляем модификатор {modifier_name}")
                obj.modifiers.remove(modifier)
                print(f"[DELETE] Модификатор успешно удален")
            except Exception as e:
                print(f"[DELETE] Ошибка при удалении модификатора: {e}")
            
            # Обновляем depsgraph
            try:
                context.view_layer.update()
                print(f"[DELETE] View layer обновлен")
            except Exception as e:
                print(f"[DELETE] Ошибка при обновлении view layer: {e}")
            
            print(f"[DELETE] Стековый клонер успешно удален")
            return True, previous_obj_name
            
        # Общая логика для всех типов клонеров
        if source_type == "OBJECT":
            # Обрабатываем клонер объекта
            original_obj_name = modifier.get("original_object", "")
            print(f"[DELETE] Оригинальный объект: {original_obj_name}")
            
            # Восстанавливаем видимость оригинального объекта
            if original_obj_name and original_obj_name in bpy.data.objects:
                orig_obj = bpy.data.objects[original_obj_name]
                print(f"[DELETE] Найден оригинальный объект: {orig_obj.name}")
                
                # Проверяем, используется ли этот объект другими клонерами
                is_used_by_others = False
                for other_obj in bpy.data.objects:
                    if other_obj == obj:
                        continue  # Пропускаем текущий объект
                    
                    for other_mod in other_obj.modifiers:
                        if (other_mod.type == 'NODES' and 
                            other_mod.get("original_object") == original_obj_name):
                            is_used_by_others = True
                            print(f"[DELETE] Объект {original_obj_name} используется клонером {other_obj.name}")
                            break
                    
                    if is_used_by_others:
                        break
                
                # Восстанавливаем видимость только если объект не используется другими клонерами
                # и если это не клонер (для поддержки цепочек)
                if not is_used_by_others and not orig_obj.name.startswith("Cloner_"):
                    try:
                        orig_obj.hide_viewport = modifier.get("original_hide_viewport", False)
                        orig_obj.hide_render = modifier.get("original_hide_render", False)
                        print(f"Восстановлена видимость оригинального объекта {orig_obj.name}")
                    except Exception as e:
                        print(f"[DELETE] Ошибка при восстановлении видимости объекта: {e}")
                
                # Делаем оригинальный объект активным только если он не клонер
                # и нет цепочки клонеров
                if not orig_obj.name.startswith("Cloner_") and not modifier.get("is_object_chain", False):
                    # Если ранее не был найден предыдущий объект, и этот объект подходит,
                    # то сохраняем его как предыдущий для выделения
                    if not previous_obj_name:
                        previous_obj_name = orig_obj.name
                        print(f"[DELETE] Установлен предыдущий объект для выделения: {previous_obj_name}")
            
            # Удаляем клонер-коллекцию
            cloner_collection_name = modifier.get("cloner_collection", "")
            print(f"[DELETE] Коллекция клонера: {cloner_collection_name}")
            
            if cloner_collection_name and cloner_collection_name in bpy.data.collections:
                # Получаем ссылку на коллекцию
                cloner_collection = bpy.data.collections[cloner_collection_name]
                print(f"[DELETE] Найдена коллекция клонера с {len(cloner_collection.objects)} объектами")
                
                # Проверяем, используется ли эта коллекция другими клонерами
                is_used_by_others = False
                for other_obj in bpy.data.objects:
                    if other_obj == obj:
                        continue  # Пропускаем текущий объект
                    
                    for other_mod in other_obj.modifiers:
                        if (other_mod.type == 'NODES' and 
                            other_mod.get("cloner_collection") == cloner_collection_name):
                            is_used_by_others = True
                            print(f"[DELETE] Коллекция {cloner_collection_name} используется клонером {other_obj.name}")
                            break
                    
                    if is_used_by_others:
                        break
                
                if not is_used_by_others:
                    print(f"[DELETE] Удаляем коллекцию {cloner_collection_name} и её объекты")
                    # Удаляем все объекты в коллекции
                    objects_to_remove = list(cloner_collection.objects)  # Создаем копию списка
                    print(f"[DELETE] Найдено {len(objects_to_remove)} объектов для удаления")
                    
                    for o in objects_to_remove:
                        try:
                            mesh_data = None
                            obj_name = o.name  # Сохраняем имя заранее
                            
                            if o.data:
                                mesh_data = o.data
                                print(f"[DELETE] Получены данные меша для {obj_name}: {type(mesh_data).__name__}")
                            
                            print(f"[DELETE] Удаление объекта {obj_name}")
                            bpy.data.objects.remove(o)
                            print(f"[DELETE] Объект {obj_name} удален")
                            
                            # Удаляем меш данные, если они больше не используются
                            if mesh_data and mesh_data.users == 0:
                                print(f"[DELETE] Проверка на удаление данных меша")
                                
                                try:
                                    # Безопасное определение типа данных
                                    data_type = type(mesh_data).__name__
                                    print(f"[DELETE] Тип данных: {data_type}")
                                    
                                    # Безопасное определение коллекции для удаления
                                    if mesh_data in bpy.data.meshes:
                                        print(f"[DELETE] Найден в bpy.data.meshes")
                                        try:
                                            bpy.data.meshes.remove(mesh_data)
                                            print(f"[DELETE] Удален из bpy.data.meshes")
                                            continue
                                        except Exception as me:
                                            print(f"[DELETE] Ошибка при удалении из meshes: {me}")
                                    
                                    if mesh_data in bpy.data.curves:
                                        print(f"[DELETE] Найден в bpy.data.curves")
                                        try:
                                            bpy.data.curves.remove(mesh_data)
                                            print(f"[DELETE] Удален из bpy.data.curves")
                                            continue
                                        except Exception as ce:
                                            print(f"[DELETE] Ошибка при удалении из curves: {ce}")
                                    
                                    # Проверяем типы по-разному
                                    try:
                                        if isinstance(mesh_data, bpy.types.Mesh):
                                            print(f"[DELETE] Удаление меша (по isinstance)")
                                            bpy.data.meshes.remove(mesh_data)
                                        elif isinstance(mesh_data, bpy.types.Curve):
                                            print(f"[DELETE] Удаление кривой (по isinstance)")
                                            bpy.data.curves.remove(mesh_data)
                                        elif 'Mesh' in data_type:
                                            print(f"[DELETE] Удаление меша (по имени типа)")
                                            bpy.data.meshes.remove(mesh_data)
                                        elif 'Curve' in data_type:
                                            print(f"[DELETE] Удаление кривой (по имени типа)")
                                            bpy.data.curves.remove(mesh_data)
                                        else:
                                            print(f"[DELETE] Неизвестный тип данных: {data_type}, пробуем как mesh")
                                            # Последняя попытка удалить как mesh
                                            try:
                                                bpy.data.meshes.remove(mesh_data)
                                            except:
                                                print(f"[DELETE] Не удалось удалить как mesh")
                                    except Exception as te:
                                        print(f"[DELETE] Ошибка при определении типа данных: {te}")
                                except Exception as e:
                                    print(f"[DELETE] Общая ошибка при удалении данных меша: {e}")
                        except Exception as e:
                            print(f"[DELETE] Ошибка при удалении объекта: {e}")
                    
                    # Удаляем коллекцию
                    try:
                        print(f"[DELETE] Удаляем коллекцию {cloner_collection_name}")
                        bpy.data.collections.remove(cloner_collection)
                        print(f"[DELETE] Коллекция удалена")
                    except Exception as e:
                        print(f"[DELETE] Ошибка при удалении коллекции: {e}")
                else:
                    print(f"Коллекция {cloner_collection_name} используется другими клонерами, не удаляем")
            
            # Удаляем node group если она больше не используется
            if node_group_name and node_group_name in bpy.data.node_groups:
                node_group = bpy.data.node_groups[node_group_name]
                if node_group.users <= 1:
                    try:
                        print(f"[DELETE] Удаляем группу узлов {node_group_name}")
                        bpy.data.node_groups.remove(node_group)
                        print(f"[DELETE] Группа узлов удалена")
                    except Exception as e:
                        print(f"[DELETE] Ошибка при удалении группы узлов: {e}")
        
        elif source_type == "COLLECTION":
            # Обрабатываем клонер коллекции
            print(f"[DELETE] Обрабатываем клонер коллекции")
            
            # Восстанавливаем видимость оригинальной коллекции
            if "original_collection" in modifier:
                collection_name = modifier["original_collection"]
                print(f"[DELETE] Оригинальная коллекция: {collection_name}")
                
                if collection_name in bpy.data.collections:
                    # Получаем layer collection для восстановления видимости
                    try:
                        view_layer = context.view_layer
                        layer_collection = view_layer.layer_collection
                        
                                                                # Используем функцию find_layer_collection из common_utils
                        
                        layer_coll = find_layer_collection(layer_collection, collection_name)
                        print(f"[DELETE] Найдена layer collection: {layer_coll}")
                        
                        if layer_coll:
                            # Восстанавливаем видимость только если она была изменена этим клонером
                            # и только если это НЕ коллекция клонера (для поддержки цепочек)
                            if "was_collection_excluded" in modifier and not collection_name.startswith("cloner_"):
                                was_excluded = modifier["was_collection_excluded"]
                                layer_coll.exclude = was_excluded
                                print(f"Восстановлена видимость коллекции {collection_name}: {was_excluded}")
                    except Exception as e:
                        print(f"[DELETE] Ошибка при восстановлении видимости коллекции: {e}")
            
            # Удаляем клонер-коллекцию, но проверяем, используется ли она другими клонерами
            if "cloner_collection" in modifier:
                collection_name = modifier["cloner_collection"]
                print(f"[DELETE] Коллекция клонера: {collection_name}")
                
                if collection_name in bpy.data.collections:
                    collection = bpy.data.collections[collection_name]
                    print(f"[DELETE] Найдена коллекция клонера с {len(collection.objects)} объектами")
                    
                    # Проверяем, используется ли эта коллекция другими клонерами
                    is_used_by_others = False
                    for other_obj in bpy.data.objects:
                        if other_obj == obj:
                            continue  # Пропускаем текущий объект
                        
                        for other_mod in other_obj.modifiers:
                            if (other_mod.type == 'NODES' and 
                                other_mod.get("cloner_collection") == collection_name):
                                is_used_by_others = True
                                print(f"[DELETE] Коллекция {collection_name} используется клонером {other_obj.name}")
                                break
                        
                        if is_used_by_others:
                            break
                    
                    if not is_used_by_others:
                        # Удаляем все объекты в коллекции
                        objects_to_remove = list(collection.objects)  # Создаем копию списка
                        print(f"[DELETE] Найдено {len(objects_to_remove)} объектов для удаления в коллекции {collection_name}")
                        
                        for o in objects_to_remove:
                            try:
                                mesh_data = None
                                obj_name = o.name  # Сохраняем имя заранее
                                
                                if o.data:
                                    mesh_data = o.data
                                    print(f"[DELETE] Получены данные меша для {obj_name}: {type(mesh_data).__name__}")
                                
                                print(f"[DELETE] Удаление объекта {obj_name}")
                                bpy.data.objects.remove(o)
                                print(f"[DELETE] Объект {obj_name} удален")
                                
                                # Удаляем меш данные, если они больше не используются
                                if mesh_data and mesh_data.users == 0:
                                    print(f"[DELETE] Проверка на удаление данных меша")
                                    
                                    try:
                                        # Безопасное определение типа данных
                                        data_type = type(mesh_data).__name__
                                        print(f"[DELETE] Тип данных: {data_type}")
                                        
                                        # Безопасное определение коллекции для удаления
                                        if mesh_data in bpy.data.meshes:
                                            print(f"[DELETE] Найден в bpy.data.meshes")
                                            try:
                                                bpy.data.meshes.remove(mesh_data)
                                                print(f"[DELETE] Удален из bpy.data.meshes")
                                                continue
                                            except Exception as me:
                                                print(f"[DELETE] Ошибка при удалении из meshes: {me}")
                                        
                                        if mesh_data in bpy.data.curves:
                                            print(f"[DELETE] Найден в bpy.data.curves")
                                            try:
                                                bpy.data.curves.remove(mesh_data)
                                                print(f"[DELETE] Удален из bpy.data.curves")
                                                continue
                                            except Exception as ce:
                                                print(f"[DELETE] Ошибка при удалении из curves: {ce}")
                                        
                                        # Проверяем типы по-разному
                                        try:
                                            if isinstance(mesh_data, bpy.types.Mesh):
                                                print(f"[DELETE] Удаление меша (по isinstance)")
                                                bpy.data.meshes.remove(mesh_data)
                                            elif isinstance(mesh_data, bpy.types.Curve):
                                                print(f"[DELETE] Удаление кривой (по isinstance)")
                                                bpy.data.curves.remove(mesh_data)
                                            elif 'Mesh' in data_type:
                                                print(f"[DELETE] Удаление меша (по имени типа)")
                                                bpy.data.meshes.remove(mesh_data)
                                            elif 'Curve' in data_type:
                                                print(f"[DELETE] Удаление кривой (по имени типа)")
                                                bpy.data.curves.remove(mesh_data)
                                            else:
                                                print(f"[DELETE] Неизвестный тип данных: {data_type}, пробуем как mesh")
                                                # Последняя попытка удалить как mesh
                                                try:
                                                    bpy.data.meshes.remove(mesh_data)
                                                except:
                                                    print(f"[DELETE] Не удалось удалить как mesh")
                                        except Exception as te:
                                            print(f"[DELETE] Ошибка при определении типа данных: {te}")
                                    except Exception as e:
                                        print(f"[DELETE] Общая ошибка при удалении данных меша: {e}")
                            except Exception as e:
                                print(f"[DELETE] Ошибка при удалении объекта: {e}")
                        
                        # Удаляем коллекцию
                        try:
                            print(f"[DELETE] Удаляем коллекцию {collection_name}")
                            bpy.data.collections.remove(collection)
                            print(f"[DELETE] Коллекция удалена")
                        except Exception as e:
                            print(f"[DELETE] Ошибка при удалении коллекции: {e}")
                    else:
                        print(f"Коллекция {collection_name} используется другими клонерами, не удаляем")
            
            # Удаляем node group
            if node_group_name and node_group_name in bpy.data.node_groups:
                node_group = bpy.data.node_groups[node_group_name]
                if node_group.users <= 1:
                    try:
                        print(f"[DELETE] Удаляем группу узлов {node_group_name}")
                        bpy.data.node_groups.remove(node_group)
                        print(f"[DELETE] Группа узлов удалена")
                    except Exception as e:
                        print(f"[DELETE] Ошибка при удалении группы узлов: {e}")
        
        # Удаляем модификатор независимо от типа источника
        try:
            print(f"[DELETE] Удаляем модификатор {modifier_name}")
            obj.modifiers.remove(modifier)
            print(f"[DELETE] Модификатор успешно удален")
        except Exception as e:
            print(f"[DELETE] Ошибка при удалении модификатора: {e}")
        
        # Обновляем цепочку клонеров, если они были связаны с этим клонером
        if hasattr(bpy.app, "timers"):
            def update_cloner_chain():
                try:
                    print(f"[CHAIN] Обновление цепочки для удаленного клонера {cloner_obj_name}")
                    
                    # Находим объекты, которые могли ссылаться на этот клонер
                    for potential_obj in bpy.data.objects:
                        if potential_obj.name.startswith("Cloner_"):
                            for mod in potential_obj.modifiers:
                                if mod.type == 'NODES' and mod.get("is_chained_cloner"):
                                    # Обновляем списки next_cloners
                                    if "next_cloners" in mod and cloner_obj_name in mod["next_cloners"]:
                                        mod["next_cloners"].remove(cloner_obj_name)
                                        print(f"[CHAIN] Удален {cloner_obj_name} из цепочки клонера {potential_obj.name}")
                                    
                                    # Обновляем previous_cloner_object если он указывал на удаленный клонер
                                    if cloner_obj_name and mod.get("previous_cloner_object") == cloner_obj_name:
                                        mod["previous_cloner_object"] = ""
                                        print(f"[CHAIN] Сброшена ссылка на предыдущий клонер для {potential_obj.name}")
                except Exception as e:
                    print(f"[CHAIN] Ошибка при обновлении цепочки клонеров: {e}")
                
                # Обновляем depsgraph для всех объектов
                try:
                    print(f"[CHAIN] Обновление depsgraph")
                    bpy.context.view_layer.update()
                except Exception as e:
                    print(f"[CHAIN] Ошибка при обновлении view layer: {e}")
                    
                return None  # Запуск только один раз
            
            # Регистрируем отложенное обновление цепочки с небольшой задержкой
            print(f"[DELETE] Регистрируем отложенное обновление цепочки")
            bpy.app.timers.register(update_cloner_chain, first_interval=0.5)
        
        # Сбрасываем выделение и активный объект, чтобы избежать ошибок
        # при удалении объекта, который был активным
        try:
            if context.active_object == obj:
                print(f"[DELETE] Сбрасываем активный объект")
                context.view_layer.objects.active = None
        except Exception as e:
            print(f"[DELETE] Ошибка при сбросе активного объекта: {e}")
            
        # Принудительно обновляем вид
        try:
            print(f"[DELETE] Обновляем вид")
            context.view_layer.update()
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            print(f"[DELETE] Вид обновлен")
        except Exception as e:
            print(f"[DELETE] Предупреждение при обновлении вида: {e}")
            # Ошибка не критична, продолжаем выполнение
        
        print(f"[DELETE] Клонер {modifier_name} успешно удален")
        
        # В конце возвращаем результат
        return True, previous_obj_name
    except Exception as e:
        print(f"[DELETE] Критическая ошибка при удалении клонера: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def move_cloner_modifier(context, obj, modifier_name, direction):
    """
    Перемещает модификатор клонера вверх или вниз в стеке модификаторов.
    
    Args:
        context: Контекст Blender
        obj: Объект, содержащий модификатор клонера
        modifier_name: Имя модификатора клонера для перемещения
        direction: Направление перемещения ('UP' или 'DOWN')
        
    Returns:
        bool: True если модификатор успешно перемещен, False в случае ошибки
    """
    if not obj or modifier_name not in obj.modifiers:
        return False
        
    try:
        if direction == 'UP':
            bpy.ops.object.modifier_move_up(modifier=modifier_name)
        else:
            bpy.ops.object.modifier_move_down(modifier=modifier_name)
        return True
    except Exception as e:
        print(f"Error moving modifier: {e}")
        return False
    
class ClonerChainUpdateHandler:

    """Обработчик для обновления цепочки клонеров при изменении параметров"""
    
    @staticmethod
    def register():
        """Регистрирует обработчики событий для отслеживания изменений параметров клонеров"""
        if hasattr(bpy.app, "handlers"):
            # Обработчик для обновления depsgraph
            if ClonerChainUpdateHandler.depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.append(ClonerChainUpdateHandler.depsgraph_update_post)
            print("Зарегистрирован обработчик цепочки клонеров")
    
    @staticmethod
    def unregister():
        """Удаляет обработчики событий"""
        if hasattr(bpy.app, "handlers"):
            if ClonerChainUpdateHandler.depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(ClonerChainUpdateHandler.depsgraph_update_post)
            print("Удален обработчик цепочки клонеров")
    
    @staticmethod
    def depsgraph_update_post(scene, depsgraph):
        """Обрабатывает обновления depsgraph и передает изменения через цепочку клонеров"""
        # Отслеживаем только изменения объектов
        for update in depsgraph.updates:
            if update.id.__class__ == bpy.types.Object:
                obj = update.id
                if obj.name.startswith("Cloner_"):
                    # Проверяем, есть ли модификаторы-клонеры с флагом is_chained_cloner
                    for mod in obj.modifiers:
                        if mod.type == 'NODES' and mod.get("is_chained_cloner"):
                            # Проверяем, есть ли следующие клонеры в цепочке
                            if "next_cloners" in mod and mod["next_cloners"]:
                                # Зарегистрируем отложенное обновление для следующих клонеров
                                # для предотвращения блокировки интерфейса
                                if hasattr(bpy.app, "timers"):
                                    def update_next_cloners():
                                        for next_cloner_name in mod["next_cloners"]:
                                            if next_cloner_name in bpy.data.objects:
                                                next_cloner_obj = bpy.data.objects[next_cloner_name]
                                                # Делаем минимальное обновление, чтобы запустить recalc
                                                if next_cloner_obj.hide_viewport:
                                                    next_cloner_obj.hide_viewport = False
                                                else:
                                                    # Можно использовать любое свойство
                                                    # для вызова обновления
                                                    current_loc = next_cloner_obj.location.copy()
                                                    next_cloner_obj.location = current_loc
                                        
                                        # Обновляем depsgraph
                                        bpy.context.view_layer.update()
                                        return None  # Запуск только один раз
                                    
                                    # Используем таймер с небольшой задержкой
                                    bpy.app.timers.register(update_next_cloners, first_interval=0.05) 

def select_previous_cloner_in_chain(context, previous_obj_name):
    """
    Гарантированно выделяет предыдущий объект в цепочке клонеров
    и устанавливает его активным.
    
    Args:
        context: Контекст Blender
        previous_obj_name: Имя объекта, который нужно выделить
        
    Returns:
        bool: True если объект успешно выделен, False в случае ошибки
    """
    print(f"[SELECT] Принудительное выделение предыдущего объекта {previous_obj_name}")
    
    if not previous_obj_name or previous_obj_name not in bpy.data.objects:
        print(f"[SELECT] Предыдущий объект {previous_obj_name} не найден")
        return False
    
    previous_obj = bpy.data.objects[previous_obj_name]
    
    try:
        # Очищаем текущее выделение
        for obj in context.selected_objects:
            obj.select_set(False)
        
        # Выделяем предыдущий объект и делаем его активным
        previous_obj.select_set(True)
        context.view_layer.objects.active = previous_obj
        print(f"[SELECT] Объект {previous_obj_name} выделен и установлен активным")
        
        # Обновляем вид для применения изменений
        context.view_layer.update()
        
        # Принудительно обновляем интерфейс для отображения изменений
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ['VIEW_3D', 'PROPERTIES', 'OUTLINER']:
                    area.tag_redraw()
        
        # Используем redraw_timer для принудительного обновления
        if hasattr(bpy.ops, "wm") and hasattr(bpy.ops.wm, "redraw_timer"):
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            
        return True
    except Exception as e:
        print(f"[SELECT] Ошибка при выделении объекта: {e}")
        return False

def update_cloner_chain(cloner_obj_name=None):
    """
    Обновляет цепочку клонеров после изменений.
    Эта функция сохранена для обратной совместимости.
    
    Args:
        cloner_obj_name: Имя объекта клонера, который был удален или изменен
        
    Returns:
        None
    """
    try:
        print(f"[CHAIN] Обновление цепочки для клонера {cloner_obj_name}")
        
        # Находим объекты, которые могли ссылаться на этот клонер
        for potential_obj in bpy.data.objects:
            if potential_obj.name.startswith("Cloner_"):
                for mod in potential_obj.modifiers:
                    if mod.type == 'NODES' and mod.get("is_chained_cloner"):
                        # Обновляем списки next_cloners
                        if cloner_obj_name and "next_cloners" in mod and cloner_obj_name in mod["next_cloners"]:
                            mod["next_cloners"].remove(cloner_obj_name)
                            print(f"[CHAIN] Удален {cloner_obj_name} из цепочки клонера {potential_obj.name}")
                        
                        # Обновляем previous_cloner_object если он указывал на удаленный клонер
                        if cloner_obj_name and mod.get("previous_cloner_object") == cloner_obj_name:
                            mod["previous_cloner_object"] = ""
                            print(f"[CHAIN] Сброшена ссылка на предыдущий клонер для {potential_obj.name}")
    except Exception as e:
        print(f"[CHAIN] Ошибка при обновлении цепочки клонеров: {e}")
    
    # Обновляем depsgraph для всех объектов
    try:
        print(f"[CHAIN] Обновление depsgraph")
        bpy.context.view_layer.update()
    except Exception as e:
        print(f"[CHAIN] Ошибка при обновлении view layer: {e}")
        
    return None  # Для совместимости с предыдущими вызовами