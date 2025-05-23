import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty

from ..common.ui_utils import is_element_expanded, set_element_expanded

class EFFECTOR_OT_add_field(Operator):
    bl_idname = "object.effector_add_field"
    bl_label  = "Add Field to Effector"
    effector_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.effector_name)
        if not mod or not mod.node_group:
            return {'CANCELLED'}
            
        # Найдем первое поле на объекте
        field_mod = None
        for m in obj.modifiers:
            if m.type == 'NODES' and m.node_group and "SphereField" in m.node_group.name:
                field_mod = m
                break
                
        if not field_mod:
            self.report({'ERROR'}, "Поле не найдено. Сначала создайте поле.")
            return {'CANCELLED'}
            
        # Подключим поле к эффектору
        # Для RandomEffector у нас уже есть входной сокет 'Field'
        if mod.node_group.name.startswith("RandomEffector"):
            # 1. Сначала отключаем Use Field для безопасности
            try:
                mod["Use Field"] = False
            except:
                pass
                
            # 2. Устанавливаем значение Field = 1.0 до включения Use Field
            try:
                mod["Field"] = 1.0
                print("Установлено Field = 1.0")
            except Exception as e:
                print(f"Ошибка при установке Field: {e}")
                
            # 3. Устанавливаем драйвер при отключенном Use Field
            try:
                # Находим сокет Value в поле
                value_socket = None
                for item in field_mod.node_group.interface.items_tree:
                    if item.item_type == 'SOCKET' and item.in_out == 'OUTPUT' and item.name == "Value":
                        value_socket = item.identifier
                        break
                        
                if value_socket:
                    # Создаем ссылку на выход поля
                    field_path = f'modifiers["{field_mod.name}"]'
                    socket_path = f'["{value_socket}"]'
                    full_path = field_path + socket_path
                    
                    # Устанавливаем драйвер
                    try:
                        # Удаляем старый драйвер, если есть
                        try:
                            mod.driver_remove('Field')
                        except:
                            pass
                            
                        # Создаем новый драйвер
                        driver = mod.driver_add('Field').driver
                        driver.type = 'AVERAGE'
                        var = driver.variables.new()
                        var.name = "field_value"
                        var.type = 'SINGLE_PROP'
                        var.targets[0].id_type = 'OBJECT'
                        var.targets[0].id = obj
                        var.targets[0].data_path = full_path
                        print(f"Драйвер установлен: {full_path}")
                        
                        # Проверка, что драйвер работает
                        try:
                            test_val = driver.evaluate()
                            print(f"Драйвер возвращает: {test_val}")
                        except:
                            pass
                    except Exception as e:
                        print(f"Ошибка при установке драйвера: {e}")
            except Exception as e:
                print(f"Ошибка при настройке драйвера: {e}")
                        
            # 4. Наконец, включаем использование поля
            try:
                mod["Use Field"] = True
                print("Use Field включено")
                self.report({'INFO'}, f"Поле '{field_mod.name}' подключено к эффектору")
                return {'FINISHED'}
            except Exception as e:
                print(f"Ошибка при включении Use Field: {e}")
                mod["Field"] = 1.0  # безопасное значение на случай ошибки
                return {'CANCELLED'}
                
        self.report({'ERROR'}, "Этот тип эффектора не поддерживает поля")
        return {'CANCELLED'}
        
class EFFECTOR_OT_remove_field(Operator):
    bl_idname = "object.effector_remove_field"
    bl_label  = "Remove Field from Effector"
    effector_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.effector_name)
        if not mod or not mod.node_group:
            return {'CANCELLED'}
            
        # Для RandomEffector просто отключаем использование поля
        # и удаляем драйвер
        if mod.node_group.name.startswith("RandomEffector"):
            # Сначала установим безопасное значение поля
            try:
                mod["Field"] = 1.0
            except:
                pass
                
            # Удаляем драйвер до отключения Use Field
            try:
                mod.driver_remove('Field')
                print("Драйвер поля удален")
            except Exception as e:
                print(f"Ошибка при удалении драйвера: {e}")
                
            # Отключаем использование поля
            try:
                mod["Use Field"] = False
                self.report({'INFO'}, "Поле отключено от эффектора")
                return {'FINISHED'}
            except Exception as e:
                print(f"Ошибка при отключении поля: {e}")
                return {'CANCELLED'}
            
        self.report({'ERROR'}, "Этот тип эффектора не поддерживает поля")
        return {'CANCELLED'}

class EFFECTOR_OT_auto_link(Operator):
    bl_idname = "object.auto_link_effector"
    bl_label  = "Auto-Link Effector to Cloners"
    effector_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        effector_mod = obj.modifiers.get(self.effector_name)
        if not effector_mod or not effector_mod.node_group:
            self.report({'ERROR'}, "Эффектор не найден")
            return {'CANCELLED'}
        
        # Найдем все обычные клонеры на объекте
        cloner_mods = [
            m for m in obj.modifiers
            if m.type == 'NODES' and m.node_group
               and m.node_group.get("linked_effectors") is not None
        ]
        
        # Найдем все стековые клонеры на объекте
        stacked_cloner_mods = [
            m for m in obj.modifiers
            if m.type == 'NODES' and m.node_group
               and (m.get("is_stacked_cloner") == True or 
                   (m.node_group and m.node_group.get("is_stacked_cloner") == True))
        ]
        
        # Логируем информацию о найденных клонерах
        print(f"Найдено обычных клонеров: {len(cloner_mods)}")
        print(f"Найдено стековых клонеров: {len(stacked_cloner_mods)}")
        for mod in stacked_cloner_mods:
            print(f"Стековый клонер: {mod.name} (mod: {mod.get('is_stacked_cloner')}, node: {mod.node_group.get('is_stacked_cloner')})")
        
        # Объединяем все клонеры
        all_cloners = cloner_mods + stacked_cloner_mods
        
        if not all_cloners:
            self.report({'ERROR'}, "На объекте нет клонеров")
            return {'CANCELLED'}
        
        # Активируем эффектор, устанавливая его параметры
        if effector_mod and effector_mod.node_group:
            # Включаем отображение эффектора, так как он будет привязан
            effector_mod.show_viewport = True
            
            # Ищем параметры Enable и Strength в интерфейсе эффектора
            for socket in effector_mod.node_group.interface.items_tree:
                if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
                    if socket.name == "Enable":
                        try:
                            effector_mod[socket.identifier] = True
                        except:
                            pass
                    elif socket.name == "Strength":
                        try:
                            effector_mod[socket.identifier] = 1.0
                        except:
                            pass
        
        # Связываем эффектор со всеми клонерами, к которым он еще не привязан
        linked_count = 0
        
        # Для обычных клонеров
        for cloner in cloner_mods:
            # Преобразуем IDPropertyArray в обычный список Python
            linked_effectors_prop = cloner.node_group.get("linked_effectors", [])
            
            # Конвертируем в список Python, если это не список
            linked_effectors = list(linked_effectors_prop) if linked_effectors_prop else []
            
            # Добавляем эффектор, если он еще не связан с этим клонером
            if self.effector_name not in linked_effectors:
                linked_effectors.append(self.effector_name)
                cloner.node_group["linked_effectors"] = linked_effectors
                
                # Обновляем клонер с новыми эффекторами
                try:
                    # Используем прямой импорт - более надежно в этом конкретном случае
                    from ...core.utils.cloner_effector_utils import update_cloner_with_effectors
                    update_cloner_with_effectors(obj, cloner)
                    print(f"Обновлен клонер {cloner.name} с эффектором {self.effector_name}")
                except Exception as e:
                    print(f"Ошибка при обновлении клонера: {e}")
                
                linked_count += 1
        
        # Для стековых клонеров
        for cloner in stacked_cloner_mods:
            # Инициализируем список linked_effectors, если его нет
            if not cloner.node_group.get("linked_effectors"):
                cloner.node_group["linked_effectors"] = []
            
            # Преобразуем IDPropertyArray в обычный список Python
            linked_effectors_prop = cloner.node_group.get("linked_effectors", [])
            
            # Конвертируем в список Python, если это не список
            linked_effectors = list(linked_effectors_prop) if linked_effectors_prop else []
            
            # Добавляем эффектор, если он еще не связан с этим клонером
            if self.effector_name not in linked_effectors:
                linked_effectors.append(self.effector_name)
                cloner.node_group["linked_effectors"] = linked_effectors
                
                # Для стековых клонеров применяем специальную функцию
                try:
                    from ...core.utils.cloner_utils import apply_effector_to_stacked_cloner
                    print(f"[DEBUG] Применение эффектора {self.effector_name} к стековому клонеру {cloner.name}")
                    print(f"[DEBUG] Свойство is_stacked_cloner в модификаторе: {cloner.get('is_stacked_cloner', False)}")
                    print(f"[DEBUG] Свойство is_stacked_cloner в node_group: {cloner.node_group.get('is_stacked_cloner', False)}")
                    
                    # Принудительно обновляем параметры эффектора, чтобы получить актуальные значения
                    # После внесения изменений в интерфейсе
                    for area in context.screen.areas:
                        if area.type == 'PROPERTIES':
                            area.tag_redraw()
                    
                    # Обновляем depsgraph перед получением значений
                    context.view_layer.update()
                    
                    apply_effector_to_stacked_cloner(obj, cloner, effector_mod)
                except Exception as e:
                    print(f"Ошибка при применении apply_effector_to_stacked_cloner: {e}")
                
                # Также вызываем стандартную функцию обновления клонера для обработки UI
                try:
                    from ...core.utils.cloner_effector_utils import update_cloner_with_effectors
                    update_cloner_with_effectors(obj, cloner)
                except Exception as e:
                    print(f"Ошибка при обновлении клонера через update_cloner_with_effectors: {e}")
                
                linked_count += 1
        
        if linked_count > 0:
            self.report({'INFO'}, f"Эффектор '{self.effector_name}' связан с {linked_count} клонерами")
        else:
            self.report({'INFO'}, "Эффектор уже связан со всеми клонерами")
            
        return {'FINISHED'}

class EFFECTOR_OT_update_stacked_cloners(Operator):
    """Обновить параметры стековых клонеров после изменения настроек эффектора"""
    bl_idname = "object.update_stacked_effectors"
    bl_label = "Update Stacked Cloners"
    bl_description = "Обновить все стековые клонеры, связанные с этим эффектором"
    
    def execute(self, context):
        obj = context.active_object
        print("[DEBUG] Запуск обновления стековых клонеров...")
        
        if not obj:
            self.report({'ERROR'}, "Нет активного объекта")
            return {'CANCELLED'}
        
        # Найдем все эффекторы на объекте
        effector_mods = []
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group and mod.node_group.name.startswith(("RandomEffector", "NoiseEffector")):
                effector_mods.append(mod)
                print(f"[DEBUG] Найден эффектор: {mod.name}")
        
        if not effector_mods:
            self.report({'ERROR'}, "На объекте нет эффекторов")
            return {'CANCELLED'}
        
        # Найдем все стековые клонеры на объекте
        stacked_cloners = []
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group and (
                mod.get("is_stacked_cloner") or 
                (mod.node_group and mod.node_group.get("is_stacked_cloner"))
            ):
                stacked_cloners.append(mod)
                if mod.get("is_stacked_cloner"):
                    print(f"[DEBUG] Найден стековый клонер (mod): {mod.name}")
                else:
                    print(f"[DEBUG] Найден стековый клонер (node_group): {mod.name}")
        
        if not stacked_cloners:
            self.report({'ERROR'}, "На объекте нет стековых клонеров")
            return {'CANCELLED'}
        
        print(f"[DEBUG] Найдено {len(effector_mods)} эффекторов и {len(stacked_cloners)} стековых клонеров")
        
        # Для каждого стекового клонера применим все связанные эффекторы
        updated_count = 0
        
        for cloner in stacked_cloners:
            # Получаем список связанных эффекторов
            linked_effectors_prop = cloner.node_group.get("linked_effectors", [])
            print(f"[DEBUG] Обработка клонера: {cloner.name}")
            print(f"[DEBUG] Связанные эффекторы (сырые данные): {linked_effectors_prop}")
            
            # Простое преобразование в список Python
            linked_effectors = []
            if linked_effectors_prop:
                try:
                    linked_effectors = list(linked_effectors_prop)
                    print(f"[DEBUG] Преобразованный список эффекторов: {linked_effectors}")
                except Exception as e:
                    print(f"[DEBUG] Ошибка при преобразовании списка: {e}")
                    
            # Проверяем, активирован ли эффектор для стекового клонера через Use Effector
            if not linked_effectors:
                # Проверяем активацию Use Effector
                is_use_effector_active = False
                try:
                    for socket in cloner.node_group.interface.items_tree:
                        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Use Effector":
                            if socket.identifier in cloner and cloner[socket.identifier]:
                                is_use_effector_active = True
                                print(f"[DEBUG] В клонере {cloner.name} активирован Use Effector")
                                break
                except Exception as e:
                    print(f"[DEBUG] Ошибка при проверке Use Effector: {e}")
                
                # Если Use Effector активирован, но список эффекторов пуст, добавляем активный эффектор
                if is_use_effector_active:
                    # Находим эффектор на объекте
                    active_effector = None
                    for mod in obj.modifiers:
                        if mod.type == 'NODES' and mod.node_group and mod.node_group.name.startswith(("RandomEffector", "NoiseEffector")):
                            active_effector = mod
                            break
                    
                    if active_effector:
                        # Добавляем эффектор в список связанных эффекторов
                        cloner.node_group["linked_effectors"] = [active_effector.name]
                        linked_effectors = [active_effector.name]
                        print(f"[DEBUG] Автоматически добавлен эффектор {active_effector.name} в список клонера {cloner.name}")
            
            # Если нет связанных эффекторов, пропускаем
            if not linked_effectors:
                print(f"[DEBUG] У клонера {cloner.name} нет связанных эффекторов")
                continue
            
            # Применяем эффекторы к клонеру
            for effector_name in linked_effectors:
                effector_mod = obj.modifiers.get(effector_name)
                if not effector_mod or not effector_mod.node_group:
                    print(f"[DEBUG] Эффектор {effector_name} не найден или не имеет node_group")
                    continue
                
                print(f"[DEBUG] Применение эффектора {effector_name} к клонеру {cloner.name}")
                try:
                    from ...core.utils.cloner_utils import apply_effector_to_stacked_cloner
                    
                    # Обязательно обновляем представление перед применением
                    context.view_layer.update()
                    
                    # Применяем эффектор к клонеру, убедившись, что Use Effector активирован
                    try:
                        # Активируем Use Effector для клонера перед применением эффектора
                        for socket in cloner.node_group.interface.items_tree:
                            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Use Effector":
                                try:
                                    cloner[socket.identifier] = True
                                    print(f"[DEBUG] Активирован сокет Use Effector в {cloner.name} перед обновлением")
                                except Exception as inner_e:
                                    print(f"[DEBUG] Ошибка при активации Use Effector: {inner_e}")
                    except Exception as e:
                        print(f"[DEBUG] Ошибка при подготовке к обновлению: {e}")
                    
                    # Теперь применяем эффектор
                    result = apply_effector_to_stacked_cloner(obj, cloner, effector_mod)
                    if result:
                        updated_count += 1
                        print(f"[DEBUG] Успешно обновлен клонер {cloner.name} с эффектором {effector_name}")
                    else:
                        print(f"[DEBUG] Не удалось обновить клонер {cloner.name} с эффектором {effector_name}")
                except Exception as e:
                    print(f"[DEBUG] Ошибка при обновлении клонера {cloner.name} с эффектором {effector_name}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Обновляем UI
        try:
            for area in context.screen.areas:
                area.tag_redraw()
            print("[DEBUG] UI обновлен")
        except Exception as e:
            print(f"[DEBUG] Ошибка при обновлении UI: {e}")
        
        # Обновляем depsgraph
        try:
            context.view_layer.update()
            print("[DEBUG] View layer обновлен")
        except Exception as e:
            print(f"[DEBUG] Ошибка при обновлении view layer: {e}")
        
        if updated_count > 0:
            print(f"[DEBUG] Успешно обновлено {updated_count} стековых клонеров")
            self.report({'INFO'}, f"Обновлено {updated_count} эффекторов на стековых клонерах")
        else:
            print("[DEBUG] Не удалось обновить стековые клонеры")
            self.report({'WARNING'}, "Не удалось обновить эффекторы на стековых клонерах")
        
        return {'FINISHED'}

class EFFECTOR_OT_toggle_expanded(Operator):
    """Toggle expanded state of an effector"""
    bl_idname = "object.toggle_effector_expanded"
    bl_label = "Toggle Effector Expanded"
    
    obj_name: StringProperty()
    modifier_name: StringProperty()
    
    def execute(self, context):
        current = is_element_expanded(context, self.obj_name, self.modifier_name, "effector_expanded_states")
        set_element_expanded(context, self.obj_name, self.modifier_name, not current, "effector_expanded_states")
        return {'FINISHED'}

# Регистрация классов
classes = [
    EFFECTOR_OT_add_field,
    EFFECTOR_OT_remove_field,
    EFFECTOR_OT_auto_link,
    EFFECTOR_OT_update_stacked_cloners,
    EFFECTOR_OT_toggle_expanded,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
