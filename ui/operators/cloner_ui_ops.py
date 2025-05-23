import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty

from ..common.ui_utils import is_element_expanded, set_element_expanded, find_socket_by_name
from ...core.utils.cloner_effector_utils import update_cloner_with_effectors
from ...models.cloners import CLONER_NODE_GROUP_PREFIXES
from ...models.effectors import EFFECTOR_NODE_GROUP_PREFIXES

class CLONER_OT_add_effector(Operator):
    bl_idname = "object.cloner_add_effector"
    bl_label  = "Add Effector to Cloner"
    cloner_name: StringProperty()

    def execute(self, context):
        # Сначала создаем новый эффектор
        bpy.ops.object.create_effector(effector_type="RANDOM")
        
        # Находим последний созданный эффектор (должен быть в конце списка модификаторов)
        obj = context.active_object
        new_effector = None
        for mod in reversed(obj.modifiers):
            if mod.type == 'NODES' and mod.node_group and "Effector" in mod.node_group.name:
                new_effector = mod
                break
        
        if not new_effector:
            self.report({'ERROR'}, "Failed to create effector")
            return {'CANCELLED'}
        
        # Получаем модификатор клонера
        mod = obj.modifiers.get(self.cloner_name)
        if not mod or not mod.node_group:
            return {'CANCELLED'}
        
        # Связываем новый эффектор с клонером
        from ...core.utils.effector_main_utils import link_effector_to_cloner
        success = link_effector_to_cloner(obj, mod, new_effector)
        
        if success:
            self.report({'INFO'}, f"Created and linked new effector '{new_effector.name}' to '{self.cloner_name}'")
        else:
            self.report({'ERROR'}, "Failed to link the new effector")
            
        return {'FINISHED'}

class CLONER_OT_remove_effector(Operator):
    bl_idname = "object.cloner_remove_effector"
    bl_label  = "Remove Effector from Cloner"
    cloner_name:   StringProperty()
    effector_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.cloner_name)
        if not mod or not mod.node_group:
            return {'CANCELLED'}
        grp = mod.node_group
        linked = list(grp.get("linked_effectors", []))
        if self.effector_name in linked:
            linked.remove(self.effector_name)
            grp["linked_effectors"] = linked
            
            # Проверим, нужно ли отключить эффектор полностью
            # Проверяем, связан ли эффектор с другими клонерами
            effector_still_used = False
            for m in obj.modifiers:
                if m != mod and m.type == 'NODES' and m.node_group and m.node_group.get("linked_effectors") is not None:
                    if self.effector_name in m.node_group.get("linked_effectors", []):
                        effector_still_used = True
                        break
            
            # Если эффектор больше не используется нигде, отключаем его
            if not effector_still_used:
                effector_mod = obj.modifiers.get(self.effector_name)
                if effector_mod and effector_mod.node_group:
                    # Отключаем видимость эффектора, так как он больше не привязан ни к одному клонеру
                    effector_mod.show_viewport = False
                    
                    # Ищем параметры Enable и Strength в интерфейсе эффектора
                    for socket in effector_mod.node_group.interface.items_tree:
                        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
                            if socket.name == "Enable":
                                try:
                                    effector_mod[socket.identifier] = False
                                except:
                                    pass
                            elif socket.name == "Strength":
                                try:
                                    effector_mod[socket.identifier] = 0.0
                                except:
                                    pass
            
            # Обновляем нод-группу клонера с эффекторами
            update_cloner_with_effectors(obj, mod)
            
        return {'FINISHED'}

class CLONER_OT_update_active_collection(Operator):
    """Update active collection after cloning"""
    bl_idname = "object.update_active_collection"
    bl_label = "Update Active Collection"
    
    collection_name: StringProperty()
    
    def execute(self, context):
        # Set the currently selected collection to the one passed
        context.scene.collection_to_clone = self.collection_name
        return {'FINISHED'}

class CLONER_OT_toggle_expanded(Operator):
    """Toggle expanded state of a cloner"""
    bl_idname = "object.toggle_cloner_expanded"
    bl_label = "Toggle Cloner Expanded"
    
    obj_name: StringProperty()
    modifier_name: StringProperty()
    
    def execute(self, context):
        current = is_element_expanded(context, self.obj_name, self.modifier_name, "cloner_expanded_states")
        set_element_expanded(context, self.obj_name, self.modifier_name, not current, "cloner_expanded_states")
        return {'FINISHED'}

class CLONER_OT_link_effector(Operator):
    """Link an effector to a cloner"""
    bl_idname = "object.cloner_link_effector"
    bl_label = "Link Effector to Cloner"
    bl_description = "Link selected effector to active cloner"
    
    effector_name: bpy.props.StringProperty(
        name="Effector Name",
        description="Name of the effector to link",
        default=""
    )
    
    cloner_name: bpy.props.StringProperty(
        name="Cloner Name",
        description="Name of the cloner to link to",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.active_object
        
        # Если имена не предоставлены, пытаемся получить их из выделенных объектов
        if not self.effector_name or not self.cloner_name:
            # Ищем клонер в активном объекте
            cloner_mod = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group:
                    # Проверяем префикс имени нод-группы
                    is_cloner = any(mod.node_group.name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES)
                    # Дополнительная проверка по имени модификатора
                    if not is_cloner and any(name_part in mod.name for name_part in ["Linear Cloner", "Grid Cloner", "Circle Cloner", "Cloner"]):
                        is_cloner = True
                    
                    if is_cloner:
                        cloner_mod = mod
                        self.cloner_name = mod.name
                        print(f"[DEBUG] link_effector: Найден клонер {mod.name} в активном объекте")
                        break
            
            # Ищем эффектор в выделенных объектах
            if len(context.selected_objects) > 1:
                for sel_obj in context.selected_objects:
                    if sel_obj == obj:
                        continue
                    
                    # Проверяем модификаторы этого объекта
                    for mod in sel_obj.modifiers:
                        if mod.type == 'NODES' and mod.node_group:
                            # Проверка по префиксу имени node_group
                            is_effector = any(mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES)
                            # Дополнительная проверка по имени модификатора
                            if not is_effector and any(name_part in mod.name for name_part in ["Random Effector", "Noise Effector", "Effector"]):
                                is_effector = True
                            # Проверка по наличию характерных параметров
                            if not is_effector and hasattr(mod.node_group, "interface") and hasattr(mod.node_group.interface, "items_tree"):
                                param_names = [socket.name for socket in mod.node_group.interface.items_tree 
                                             if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT']
                                if 'Enable' in param_names and 'Strength' in param_names:
                                    is_effector = True
                            
                            if is_effector:
                                self.effector_name = mod.name
                                print(f"[DEBUG] link_effector: Найден эффектор {mod.name} в выделенном объекте {sel_obj.name}")
                                break
                    
                    if self.effector_name:
                        break
        
        if not self.effector_name or not self.cloner_name:
            self.report({'ERROR'}, "Please select cloner and effector objects")
            return {'CANCELLED'}
        
        print(f"[DEBUG] link_effector: Linking effector {self.effector_name} to cloner {self.cloner_name}")
        
        # Находим объект клонера и эффектора
        cloner_obj = obj
        cloner_mod = cloner_obj.modifiers.get(self.cloner_name)
        
        if not cloner_mod or not cloner_mod.node_group:
            self.report({'ERROR'}, f"Cloner modifier '{self.cloner_name}' not found or has no node group")
            return {'CANCELLED'}
        
        effector_obj = obj  # По умолчанию считаем, что эффектор на том же объекте
        effector_mod = None
        
        # Ищем эффектор сначала на том же объекте
        effector_mod = cloner_obj.modifiers.get(self.effector_name)
        
        # Если не нашли на текущем объекте, ищем в выделенных объектах
        if not effector_mod and len(context.selected_objects) > 1:
            for sel_obj in context.selected_objects:
                if sel_obj != cloner_obj and self.effector_name in sel_obj.modifiers:
                    effector_obj = sel_obj
                    effector_mod = sel_obj.modifiers.get(self.effector_name)
                    break
        
        if not effector_mod or not effector_mod.node_group:
            self.report({'ERROR'}, f"Effector '{self.effector_name}' not found or has no node group")
            return {'CANCELLED'}
        
        # Проверяем, является ли модификатор эффектором
        # (в некоторых старых версиях мы могли это не проверять и доверять имени, 
        # поэтому здесь оставляем лишь базовую проверку на наличие нужных параметров)
        is_effector = False
        if hasattr(effector_mod.node_group, "interface") and hasattr(effector_mod.node_group.interface, "items_tree"):
            param_names = [socket.name for socket in effector_mod.node_group.interface.items_tree 
                         if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT']
            is_effector = "Strength" in param_names or "Field" in param_names or "Random Position" in param_names
        
        if not is_effector:
            self.report({'ERROR'}, f"'{self.effector_name}' is not an effector")
            return {'CANCELLED'}
        
        # Связываем эффектор с клонером
        from ...core.utils.effector_main_utils import link_effector_to_cloner
        success = link_effector_to_cloner(cloner_obj, cloner_mod, effector_mod)
        
        if success:
            self.report({'INFO'}, f"Successfully linked '{self.effector_name}' to '{self.cloner_name}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Failed to link '{self.effector_name}' to '{self.cloner_name}'")
            return {'CANCELLED'}

# Добавляем пропущенный оператор для отвязки эффектора
class CLONER_OT_unlink_effector(Operator):
    """Unlink an effector from a cloner"""
    bl_idname = "object.unlink_effector"
    bl_label = "Unlink Effector"
    bl_description = "Remove effector from the cloner"
    
    effector_name: StringProperty(
        name="Effector Name",
        description="Name of the effector to unlink",
        default=""
    )
    
    cloner_name: StringProperty(
        name="Cloner Name",
        description="Name of the cloner to unlink from",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.active_object
        
        # Получаем модификатор клонера
        cloner_mod = obj.modifiers.get(self.cloner_name)
        if not cloner_mod or not cloner_mod.node_group:
            self.report({'ERROR'}, f"Cloner '{self.cloner_name}' not found")
            return {'CANCELLED'}
        
        # Получаем список связанных эффекторов
        if "linked_effectors" not in cloner_mod.node_group:
            self.report({'WARNING'}, f"Cloner '{self.cloner_name}' has no linked effectors")
            return {'CANCELLED'}
        
        linked_effectors = list(cloner_mod.node_group["linked_effectors"])
        
        # Проверяем, что эффектор действительно связан
        if self.effector_name not in linked_effectors:
            self.report({'WARNING'}, f"Effector '{self.effector_name}' is not linked to this cloner")
            return {'CANCELLED'}
        
        # Удаляем эффектор из списка
        linked_effectors.remove(self.effector_name)
        cloner_mod.node_group["linked_effectors"] = linked_effectors
        
        # Обновляем нод-группу клонера
        update_cloner_with_effectors(obj, cloner_mod)
        
        self.report({'INFO'}, f"Unlinked '{self.effector_name}' from '{self.cloner_name}'")
        return {'FINISHED'}

# Добавляем пропущенный оператор для добавления эффектора к клонеру
class CLONER_OT_add_effector_to_cloner(Operator):
    """Add an existing effector to a cloner"""
    bl_idname = "object.add_effector_to_cloner"
    bl_label = "Link Effector to Cloner"
    bl_description = "Link an existing effector to this cloner"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.active_object
        
        # Получаем активный клонер
        active_cloner = None
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                # Проверка префикса имени группы узлов
                if any(mod.node_group.name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES):
                    active_cloner = mod
                    break
                # Дополнительная проверка для клонеров коллекций и пользовательских групп
                if "Cloner" in mod.node_group.name or "_Cloner" in mod.name:
                    active_cloner = mod
                    break
        
        if not active_cloner:
            self.report({'ERROR'}, "No active cloner found on this object")
            return {'CANCELLED'}
        
        # Получаем все доступные эффекторы
        available_effectors = []
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                # Если модификатор - эффектор
                is_effector = any(mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES)
                
                # Проверка по имени для собственных групп
                if not is_effector and ("Effector" in mod.node_group.name or "_Effector" in mod.name):
                    is_effector = True
                
                if is_effector:
                    # Проверяем, не привязан ли эффектор уже к активному клонеру
                    already_linked = False
                    if "linked_effectors" in active_cloner.node_group:
                        linked_effectors = active_cloner.node_group["linked_effectors"]
                        if mod.name in linked_effectors:
                            already_linked = True
                    
                    if not already_linked:
                        available_effectors.append((mod.name, mod.name, ""))
        
        # Если нет доступных эффекторов, предлагаем создать новый
        if not available_effectors:
            # Создаем новый эффектор
            bpy.ops.object.cloner_add_effector(cloner_name=active_cloner.name)
            return {'FINISHED'}
        
        # Сохраняем имя клонера для использования в операторе выбора эффектора
        context.scene.active_cloner_for_effector = active_cloner.name
        
        # Создаем меню для выбора эффектора
        def draw_menu(self, context):
            layout = self.layout
            for eff_name, label, _ in available_effectors:
                props = layout.operator("object.cloner_link_effector", text=label)
                props.effector_name = eff_name
                props.cloner_name = active_cloner.name
        
        # Показываем меню
        bpy.context.window_manager.popup_menu(draw_menu, title="Select Effector to Link")
        
        return {'FINISHED'}

class CLONER_OT_set_active_in_chain(Operator):
    """Set the active cloner in the chain"""
    bl_idname = "object.set_cloner_active_in_chain"
    bl_label = "Set Active Cloner"
    
    object_name: StringProperty()
    modifier_name: StringProperty()
    
    def execute(self, context):
        # Формируем новый идентификатор клонера
        new_active_cloner = f"{self.object_name}|{self.modifier_name}"
        
        # Проверяем, был ли этот клонер уже активным
        if context.scene.active_cloner_in_chain == new_active_cloner:
            # Если клонер уже активен, сбрасываем свойство (сворачиваем меню)
            context.scene.active_cloner_in_chain = ""
            print(f"Свернуто меню клонера: {new_active_cloner}")
        else:
            # Если клонер не был активен, делаем его активным
            context.scene.active_cloner_in_chain = new_active_cloner
            print(f"Выбран активный клонер: {new_active_cloner}")
        
        return {'FINISHED'}

class CLONER_OT_refresh_effector(Operator):
    """Refresh an effector connected to a cloner"""
    bl_idname = "object.cloner_refresh_effector"
    bl_label = "Refresh Effector"
    bl_description = "Manually update the connection between effector and cloner"
    
    cloner_name: StringProperty(
        name="Cloner Name",
        description="Name of the cloner to refresh",
        default=""
    )
    
    effector_name: StringProperty(
        name="Effector Name",
        description="Name of the effector to refresh",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.active_object
        cloner_mod = obj.modifiers.get(self.cloner_name)
        
        if not cloner_mod or not cloner_mod.node_group:
            self.report({'ERROR'}, f"Cloner '{self.cloner_name}' not found")
            return {'CANCELLED'}
        
        if self.effector_name:
            # Refresh only this effector
            effector_mod = obj.modifiers.get(self.effector_name)
            if not effector_mod or not effector_mod.node_group:
                self.report({'ERROR'}, f"Effector '{self.effector_name}' not found")
                return {'CANCELLED'}
                
            # Check if the effector is linked to the cloner
            if "linked_effectors" not in cloner_mod.node_group or self.effector_name not in cloner_mod.node_group["linked_effectors"]:
                self.report({'WARNING'}, f"Effector '{self.effector_name}' is not linked to '{self.cloner_name}'")
                return {'CANCELLED'}
            
            # Refresh the connection
            from ...core.utils.effector_main_utils import update_effector_connection
            success = update_effector_connection(obj, cloner_mod, effector_mod)
            
            if success:
                self.report({'INFO'}, f"Successfully refreshed '{self.effector_name}' connection")
            else:
                self.report({'WARNING'}, f"Failed to refresh '{self.effector_name}' connection")
                
        else:
            # Refresh all linked effectors
            if "linked_effectors" not in cloner_mod.node_group or not cloner_mod.node_group["linked_effectors"]:
                self.report({'WARNING'}, f"No effectors linked to '{self.cloner_name}'")
                return {'CANCELLED'}
                
            # Update all effectors at once
            update_cloner_with_effectors(obj, cloner_mod)
            self.report({'INFO'}, f"Successfully refreshed all effectors for '{self.cloner_name}'")
        
        return {'FINISHED'}

# Функции регистрации и отмены регистрации
def register():
    bpy.utils.register_class(CLONER_OT_add_effector)
    bpy.utils.register_class(CLONER_OT_remove_effector)
    bpy.utils.register_class(CLONER_OT_update_active_collection)
    bpy.utils.register_class(CLONER_OT_toggle_expanded)
    bpy.utils.register_class(CLONER_OT_link_effector)
    bpy.utils.register_class(CLONER_OT_unlink_effector)
    bpy.utils.register_class(CLONER_OT_add_effector_to_cloner)
    bpy.utils.register_class(CLONER_OT_set_active_in_chain)
    bpy.utils.register_class(CLONER_OT_refresh_effector)
    
    # Добавляем свойство для хранения активного клонера для эффектора
    bpy.types.Scene.active_cloner_for_effector = StringProperty(
        name="Active Cloner for Effector",
        description="Name of the cloner to link effector to",
        default=""
    )

def unregister():
    bpy.utils.unregister_class(CLONER_OT_refresh_effector)
    bpy.utils.unregister_class(CLONER_OT_set_active_in_chain)
    bpy.utils.unregister_class(CLONER_OT_add_effector_to_cloner)
    bpy.utils.unregister_class(CLONER_OT_unlink_effector)
    bpy.utils.unregister_class(CLONER_OT_link_effector)
    bpy.utils.unregister_class(CLONER_OT_toggle_expanded)
    bpy.utils.unregister_class(CLONER_OT_update_active_collection)
    bpy.utils.unregister_class(CLONER_OT_remove_effector)
    bpy.utils.unregister_class(CLONER_OT_add_effector)
    
    # Удаляем свойство для хранения активного клонера для эффектора
    if hasattr(bpy.types.Scene, "active_cloner_for_effector"):
        del bpy.types.Scene.active_cloner_for_effector