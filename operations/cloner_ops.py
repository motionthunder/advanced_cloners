"""Операторы для создания и управления клонерами.
"""

import bpy
import re
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty, BoolProperty

from ..core.common.constants import CLONER_MOD_NAMES
from ..ui.common.cloner_utils import force_select_object
from ..core.utils.cloner_effector_utils import get_effector_modifiers
from .cloner_helpers import (
    create_object_cloner,
    create_collection_cloner,
    move_cloner_modifier,
    delete_cloner,
    ClonerChainUpdateHandler,
)

# Реэкспорт для обратной совместимости с __init__.py
register, unregister = ClonerChainUpdateHandler.register, ClonerChainUpdateHandler.unregister

class CLONER_OT_create_cloner(bpy.types.Operator):
    """Create a new cloner"""
    bl_idname = "object.create_cloner"
    bl_label = "Create Cloner"
    bl_options = {'REGISTER', 'UNDO'}
    
    cloner_type: bpy.props.StringProperty(default="GRID")
    use_custom_group: bpy.props.BoolProperty(default=True, 
                                        name="Use Custom Group",
                                        description="Create the cloner in a custom node group")
    
    source_type: bpy.props.EnumProperty(
        name="Source",
        description="What to clone: single object or entire collection",
        items=[
            ('OBJECT', "Object", "Clone selected object"),
            ('COLLECTION', "Collection", "Clone selected collection"),
        ],
        default='OBJECT'
    )
    
    target_collection: bpy.props.StringProperty(
        name="Collection",
        description="Collection to clone"
    )
    
    use_stacked_modifiers: bpy.props.BoolProperty(
        default=False,
        name="Use Stacked Modifiers (for objects)",
        description="Create all cloners as modifiers on a single object instead of creating a chain of objects. This allows you to easily reorder cloners by moving modifiers up/down. Only works for object cloners."
    )
    
    def invoke(self, context, event):
        if self.source_type == 'COLLECTION':
            # If any collection is selected in outliner, use it
            area = context.area
            if area and area.type == 'OUTLINER':
                for space in area.spaces:
                    if space.type == 'OUTLINER' and hasattr(space, "active_element"):
                        if space.active_element and space.active_element.type == 'COLLECTION':
                            if hasattr(space.active_element, "name"):
                                self.target_collection = space.active_element.name
            
            # If no collection set, show collection picker
            if not self.target_collection:
                return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "source_type", expand=True)
        
        if self.source_type == 'COLLECTION':
            row = layout.row()
            row.prop_search(self, "target_collection", bpy.data, "collections")
            
            # Add note about collection cloning
            info_box = layout.box()
            info_box.label(text="Note: The entire collection will be cloned")
            info_box.label(text="as a single group of objects.")
        else:
            # Опция стековых модификаторов только для объектных клонеров
            layout.prop(self, "use_stacked_modifiers")
        
        layout.prop(self, "cloner_type")
        layout.prop(self, "use_custom_group")
    
    def execute(self, context):
        # Сбрасываем выбор активного клонера в цепочке, чтобы предотвратить конфликты
        # между разными режимами клонеров
        if hasattr(context.scene, "active_cloner_in_chain") and context.scene.active_cloner_in_chain:
            print(f"[DEBUG] Сбрасываем выбор клонера в цепочке при создании нового клонера")
            context.scene.active_cloner_in_chain = ""
            
        # Сбрасываем глобальные переменные из event_handlers.py, управляющие выбором объектов
        # Импортируем их из модуля, чтобы иметь возможность изменить
        from ..core.utils.event_handlers import _last_selection_time, _last_selected_object
        import sys
        # Безопасно сбрасываем значения переменных в модуле
        try:
            mod = sys.modules["advanced_cloners.core.utils.event_handlers"]
            if hasattr(mod, "_last_selection_time"):
                setattr(mod, "_last_selection_time", 0)
            if hasattr(mod, "_last_selected_object"):
                setattr(mod, "_last_selected_object", None)
        except (KeyError, AttributeError) as e:
            print(f"[DEBUG] Ошибка при сбросе глобальных переменных: {e}")
        
        # Теперь просто выполняем создание клонера без манипуляций с выделением
        if self.source_type == 'OBJECT':
            if not context.active_object:
                self.report({'ERROR'}, "Please select an object for cloning")
                return {'CANCELLED'}
            
            # Вызываем соответствующую функцию в зависимости от режима (стековый или обычный)
            result = create_object_cloner(
                context,
                self.cloner_type,
                context.active_object,
                self.use_stacked_modifiers,
                self.use_custom_group
            )
            
            if result:
                self.report({'INFO'}, f"Created {self.cloner_type} cloner")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to create cloner")
                return {'CANCELLED'}
                
        else:  # COLLECTION
            if not self.target_collection or self.target_collection not in bpy.data.collections:
                self.report({'ERROR'}, "Please select a valid collection for cloning")
                return {'CANCELLED'}
            
            # Для коллекций игнорируем опцию стековых модификаторов, только обычный режим
            result = create_collection_cloner(
                context,
                self.cloner_type,
                self.target_collection,
                self.use_custom_group
            )
            
            if result:
                self.report({'INFO'}, f"Created {self.cloner_type} collection cloner")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to create collection cloner")
                return {'CANCELLED'}

class CLONER_OT_delete_cloner(bpy.types.Operator):
    """Delete this cloner"""
    bl_idname = "object.delete_cloner"
    bl_label = "Delete Cloner"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.active_object
        if obj and self.modifier_name in obj.modifiers:
            print(f"[OPERATOR] Начало выполнения оператора удаления клонера: {self.modifier_name}")
            
            # Сбрасываем глобальные переменные из event_handlers.py для предотвращения проблем с выбором
            from ..core.utils.event_handlers import _last_selection_time, _last_selected_object
            import sys
            # Безопасно сбрасываем значения переменных в модуле
            try:
                mod = sys.modules["advanced_cloners.core.utils.event_handlers"]
                if hasattr(mod, "_last_selection_time"):
                    setattr(mod, "_last_selection_time", 0)
                if hasattr(mod, "_last_selected_object"):
                    setattr(mod, "_last_selected_object", None)
            except (KeyError, AttributeError) as e:
                print(f"[DEBUG] Ошибка при сбросе глобальных переменных: {e}")
            
            # Ищем предыдущий объект до удаления текущего
            previous_obj_name = None
            try:
                # Ищем предыдущий объект в метаданных
                modifier = obj.modifiers[self.modifier_name]
                if "previous_cloner_object" in modifier and modifier["previous_cloner_object"] in bpy.data.objects:
                    previous_obj_name = modifier["previous_cloner_object"]
                    print(f"[OPERATOR] Найден предыдущий объект: {previous_obj_name}")
            except:
                pass
                
            # Запоминаем имя объекта до удаления
            obj_name = obj.name
            
            # Вызываем функцию удаления клонера
            print(f"[OPERATOR] Вызываем функцию delete_cloner для {obj.name}.{self.modifier_name}")
            try:
                result = delete_cloner(context, obj, self.modifier_name)
                
                # Проверяем тип результата
                if isinstance(result, tuple) and len(result) == 2:
                    success, found_prev_obj_name = result
                    # Если функция нашла предыдущий объект, обновляем наш найденный
                    if found_prev_obj_name:
                        previous_obj_name = found_prev_obj_name
                else:
                    # Для обратной совместимости
                    success = bool(result)
            except Exception as e:
                print(f"[OPERATOR] Ошибка при вызове delete_cloner: {e}")
                success = False
                
            if success:
                self.report({'INFO'}, f"Deleted cloner: {self.modifier_name}")
                print(f"[OPERATOR] Клонер успешно удален")
                
                # Выбираем предыдущий объект в цепочке, если он существует
                if previous_obj_name and previous_obj_name in bpy.data.objects:
                    # Используем новую функцию для гарантированного выделения
                    force_select_object(context, previous_obj_name)
                    print(f"[OPERATOR] Вызвана функция форсированного выделения для {previous_obj_name}")
                
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to delete cloner: {self.modifier_name}")
                print(f"[OPERATOR] Ошибка при удалении клонера {self.modifier_name}")
                return {'CANCELLED'}
                
        self.report({'ERROR'}, "No active object with the specified modifier")
        return {'CANCELLED'}

class CLONER_OT_move_modifier(bpy.types.Operator):
    """Move modifier up or down"""
    bl_idname = "object.move_cloner"
    bl_label = "Move Cloner"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty()
    direction: bpy.props.EnumProperty(
        items=[
            ('UP', 'Up', 'Move up'),
            ('DOWN', 'Down', 'Move down')
        ]
    )

    def execute(self, context):
        obj = context.active_object
        if obj and self.modifier_name in obj.modifiers:
            success = move_cloner_modifier(context, obj, self.modifier_name, self.direction)
            if success:
                return {'FINISHED'}
        
        return {'CANCELLED'}

# Список классов для регистрации
classes = (
    CLONER_OT_create_cloner,
    CLONER_OT_delete_cloner,
    CLONER_OT_move_modifier
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Регистрация обработчика цепочки клонеров уже выполняется в __init__.py
    print("Зарегистрирован обработчик цепочки клонеров")

def unregister():
    # Отмена регистрации обработчика цепочки клонеров уже выполняется в __init__.py
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 