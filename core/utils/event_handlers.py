"""
Обработчики событий для клонеров.
"""

import bpy
import time
_effector_handler_blocked = False
_effector_handler_call_count = 0
_EFFECTOR_HANDLER_MAX_CALLS = 10
_effector_last_parameters = {}
_last_selection_time = 0
_last_selected_object = None
_SELECTION_COOLDOWN = 0.5  # Минимальное время между переключениями в секундах

# Используем force_update_cloners из service_utils.py

from ..common.constants import CLONER_NODE_GROUP_PREFIXES, EFFECTOR_NODE_GROUP_PREFIXES

@bpy.app.handlers.persistent
def cloner_chain_update_handler(scene, depsgraph):
    """
    Обработчик изменений в цепочке клонеров.
    Следит за изменением активного клонера в цепочке и выделяет соответствующий объект.
    """
    global _last_selection_time, _last_selected_object
    
    # Проверяем, есть ли активный клонер в цепочке
    if not hasattr(scene, "active_cloner_in_chain") or not scene.active_cloner_in_chain:
        return
    
    # Получаем информацию об активном клонере
    active_cloner_info = scene.active_cloner_in_chain
    parts = active_cloner_info.split("|")
    if len(parts) != 2:
        return
    
    obj_name, mod_name = parts
    
    # Проверяем, существует ли объект с таким именем
    if obj_name not in bpy.data.objects:
        print(f"[HANDLER] Объект {obj_name} не найден, сбрасываем активный клонер в цепочке")
        scene.active_cloner_in_chain = ""
        return
    
    obj = bpy.data.objects[obj_name]
    
    # Проверяем, существует ли модификатор с таким именем на объекте
    if mod_name not in obj.modifiers:
        print(f"[HANDLER] Модификатор {mod_name} не найден на объекте {obj_name}, сбрасываем активный клонер в цепочке")
        scene.active_cloner_in_chain = ""
        return
    
    # Проверяем режим стекового клонера
    active_mod = obj.modifiers[mod_name]
    is_stacked_cloner = active_mod.get("is_stacked_cloner", False)
    
    # Проверяем, не слишком ли часто происходит переключение
    current_time = time.time()
    time_since_last = current_time - _last_selection_time
    
    # Если прошло слишком мало времени с последнего переключения
    if time_since_last < _SELECTION_COOLDOWN:
        # Если объект совпадает с последним выбранным или это стековый клонер, пропускаем
        if _last_selected_object == obj_name or is_stacked_cloner:
            return
        
        # Если первый объект пытается перехватить выбор слишком быстро,
        # игнорируем это, чтобы избежать циклического переключения
        if "Cloner_" in obj_name and obj_name.count("_") == 1:
            print(f"[HANDLER] Блокировка частого переключения на {obj_name}")
            return
    
    # Проверяем, является ли объект уже активным и выделенным
    is_already_active = (bpy.context.view_layer.objects.active == obj)
    is_already_selected = obj.select_get()
    
    # Если объект уже выделен и активен, не делаем ничего
    if is_already_active and is_already_selected:
        return
    
    # Для стековых клонеров мы не переключаем объект, только обновляем интерфейс
    if is_stacked_cloner:
        print(f"[HANDLER] Обнаружен стековый клонер, только обновляем интерфейс")
        # Обновляем интерфейс в следующем кадре
        def update_ui():
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            return None
        
        # Регистрируем функцию обновления UI
        if hasattr(bpy.app, "timers"):
            bpy.app.timers.register(update_ui, first_interval=0.1)
        
        return
    
    # Сохраняем информацию о текущем выборе
    _last_selection_time = current_time
    _last_selected_object = obj_name
    
    # Снимаем выделение со всех объектов
    try:
        # Берем текущий активный объект для более плавного переключения
        current_active = bpy.context.view_layer.objects.active
        if current_active:
            current_active.select_set(False)
        
        # Безопасно устанавливаем новый активный объект и выделение
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Обновляем view_layer для применения изменений
        bpy.context.view_layer.update()
    except Exception as e:
        print(f"[HANDLER] Ошибка при переключении объекта: {e}")
    
    # Настройка таймера, который удалит защиту от повторного выбора через некоторое время
    def reset_selection_lock():
        global _last_selection_time
        _last_selection_time = 0
        return None  # Запуск только один раз
    
    # Добавляем таймер для сброса блокировки выбора через 1 секунду
    # Это позволит пользователю выбрать объект вручную через некоторое время
    if hasattr(bpy.app, "timers"):
        bpy.app.timers.register(reset_selection_lock, first_interval=1.0)

@bpy.app.handlers.persistent
def cloner_collection_update_handler(scene):
    """
    Обработчик обновления выбранной коллекции после клонирования.
    Устанавливает последнюю созданную коллекцию клонера в поле выбора.
    """
    # Проверяем, есть ли информация о последней созданной коллекции
    if hasattr(scene, "last_cloned_collection") and scene.last_cloned_collection:
        # Устанавливаем выбранную коллекцию напрямую, без манипуляций с выделением
        scene.collection_to_clone = scene.last_cloned_collection
        # Сбрасываем сохраненное значение
        scene.last_cloned_collection = ""
        
        # Обновляем UI только в областях VIEW_3D
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except:
            pass  # Игнорируем любые ошибки обновления UI
    
    return None

@bpy.app.handlers.persistent
def effector_parameter_update_handler(scene, depsgraph):
    """
    Обработчик изменений параметров эффекторов.
    Отслеживает изменения в параметрах эффекторов и обновляет связанные клонеры.
    """
    global _effector_handler_blocked, _effector_handler_call_count
    
    # Защита от бесконечного цикла - если обработчик уже выполняется, выходим
    if _effector_handler_blocked:
        return
    
    # Увеличиваем счетчик последовательных вызовов
    _effector_handler_call_count += 1
    
    # Проверяем, не превышен ли лимит последовательных вызовов
    if _effector_handler_call_count > _EFFECTOR_HANDLER_MAX_CALLS:
        print(f"[WARNING] effector_parameter_update_handler: Достигнут лимит последовательных вызовов ({_EFFECTOR_HANDLER_MAX_CALLS}). Возможно, возник бесконечный цикл обновлений.")
        _effector_handler_call_count = 0  # Сбрасываем счетчик
        return
    
    # Устанавливаем блокировку перед обработкой
    _effector_handler_blocked = True
    
    try:
        # Проверяем все изменения в depsgraph
        if not depsgraph.id_type_updated('OBJECT'):
            return
        
        # Словарь для хранения изменённых эффекторов и их модификаторов
        updated_effectors = {}
        
        # Проверяем все измененные объекты
        for update in depsgraph.updates:
            # Проверяем что update.id.original это объект Blender
            if hasattr(update.id, 'original'):
                obj = update.id.original
                # Проверяем что объект это bpy.types.Object
                if isinstance(obj, bpy.types.Object):
                    # Проверяем все модификаторы объекта
                    for mod in obj.modifiers:
                        # Определяем, является ли модификатор эффектором
                        is_effector = False
                        
                        # Проверка по типу модификатора и наличию node_group
                        if mod.type == 'NODES' and mod.node_group:
                            # Проверка по префиксу имени node_group
                            if any(mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES):
                                is_effector = True
                            # Дополнительная проверка по имени модификатора
                            elif any(mod.name.startswith(p) for p in ['Random Effector', 'Noise Effector']):
                                is_effector = True
                            # Проверка по наличию характерных параметров
                            elif hasattr(mod.node_group, "interface") and hasattr(mod.node_group.interface, "items_tree"):
                                param_names = [socket.name for socket in mod.node_group.interface.items_tree 
                                             if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT']
                                if 'Enable' in param_names and 'Strength' in param_names:
                                    is_effector = True
                        
                        if not is_effector:
                            continue
                        
                        # Создаем уникальный ключ для этого модификатора
                        mod_key = f"{obj.name}__{mod.name}"
                        
                        # Инициализируем словарь параметров, если это первый вызов
                        if mod_key not in _effector_last_parameters:
                            _effector_last_parameters[mod_key] = {}
                            for prop_name in mod.keys():
                                if prop_name.startswith("Socket_"):
                                    try:
                                        _effector_last_parameters[mod_key][prop_name] = mod[prop_name]
                                    except:
                                        pass
                            continue
                        
                        # Проверяем, есть ли изменения параметров
                        parameters_changed = False
                        changed_parameters = []
                        for prop_name in mod.keys():
                            if prop_name.startswith("Socket_"):
                                try:
                                    # Если параметр не был сохранен или его значение изменилось
                                    if (prop_name not in _effector_last_parameters[mod_key] or 
                                        _effector_last_parameters[mod_key][prop_name] != mod[prop_name]):
                                        parameters_changed = True
                                        changed_parameters.append(f"{prop_name}={mod[prop_name]}")
                                        # Обновляем сохраненное значение
                                        _effector_last_parameters[mod_key][prop_name] = mod[prop_name]
                                except:
                                    pass
                        
                        # Если параметры изменились, запоминаем этот эффектор для обновления
                        if parameters_changed:
                            print(f"[DEBUG] effector_parameter_update_handler: Изменены параметры эффектора {mod.name}: {' '.join(changed_parameters)}")
                            updated_effectors[mod_key] = (obj, mod)
        
        # Обновляем все клонеры, связанные с измененными эффекторами
        for mod_key, (obj, mod) in updated_effectors.items():
            print(f"[DEBUG] effector_parameter_update_handler: Принудительное обновление клонеров для эффектора {mod.name}")
            
            # Импортируем функцию здесь для избежания циклической зависимости
            from .cloner_effector_utils import apply_effector_to_stacked_cloner
            
            # Поиск связанных клонеров и их обновление
            for target_obj in bpy.data.objects:
                if not target_obj.modifiers:
                    continue
                    
                for target_mod in target_obj.modifiers:
                    if target_mod.type == 'NODES' and target_mod.node_group:
                        # Проверяем, является ли модификатор клонером
                        is_cloner = any(target_mod.node_group.name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES)
                        
                        if not is_cloner:
                            continue
                            
                        # Проверяем, связан ли клонер с эффектором
                        linked_effectors = target_mod.node_group.get("linked_effectors", [])
                        if mod.name in linked_effectors:
                            print(f"[DEBUG] effector_parameter_update_handler: Найден связанный клонер {target_mod.name}")
                            
                            # Проверяем, является ли клонер стековым
                            is_stacked = target_mod.get("is_stacked_cloner", False) or target_mod.node_group.get("is_stacked_cloner", False)
                            
                            # Если это стековый клонер, применяем эффектор напрямую
                            if is_stacked:
                                print(f"[DEBUG] effector_parameter_update_handler: Применение эффектора к стековому клонеру")
                                
                                # Импортируем здесь для избежания циклической зависимости
                                from .cloner_effector_utils import apply_effector_to_stacked_cloner
                                apply_effector_to_stacked_cloner(target_obj, target_mod, mod)
                            
                            # Принудительное обновление клонера
                            try:
                                target_mod.show_viewport = False
                                target_mod.show_viewport = True
                                target_obj.update_tag(refresh={'OBJECT'})
                            except Exception as e:
                                print(f"[DEBUG] effector_parameter_update_handler: Ошибка при обновлении модификатора: {e}")
            
            # Обновляем видимость всей сцены
            try:
                bpy.context.view_layer.update()
            except Exception as e:
                print(f"[DEBUG] effector_parameter_update_handler: Ошибка при обновлении view_layer: {e}")
    
    except Exception as e:
        print(f"[ERROR] effector_parameter_update_handler: {e}")
    
    finally:
        # Сбрасываем блокировку и счетчик вызовов
        _effector_handler_blocked = False
        _effector_handler_call_count = 0

def register_effector_update_handler():
    """
    Регистрирует обработчик обновления эффекторов.
    """
    if effector_parameter_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(effector_parameter_update_handler)
        print("Зарегистрирован обработчик обновления эффекторов")
    else:
        print("Обработчик обновления эффекторов уже зарегистрирован")

def unregister_effector_update_handler():
    """
    Отменяет регистрацию обработчика обновления эффекторов.
    """
    if effector_parameter_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(effector_parameter_update_handler)
        print("Отменена регистрация обработчика обновления эффекторов")
    else:
        print("Обработчик обновления эффекторов не был зарегистрирован") 