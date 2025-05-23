"""
Operators for creating and managing fields.
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty, BoolProperty

from ..models.fields import FIELD_TYPES
from ..core.common.constants import FIELD_MOD_NAMES
from ..core.factories.component_factory import ComponentFactory

class FIELD_OT_create_field(bpy.types.Operator):
    """Create a new field"""
    bl_idname = "object.create_field"
    bl_label = "Create Field"
    bl_options = {'REGISTER', 'UNDO'}
    
    field_type: bpy.props.StringProperty(default="SPHERE")
    use_custom_group: bpy.props.BoolProperty(default=True, 
                                          name="Use Custom Group",
                                          description="Create the field in a custom node group")

    def execute(self, context):
        if not context.active_object:
            self.report({'ERROR'}, "Please select an object")
            return {'CANCELLED'}
        
        obj = context.active_object
        
        # Используем фабрику для создания поля
        node_group = ComponentFactory.create_field(
            field_type=self.field_type, 
            use_custom_group=self.use_custom_group,
            obj=obj
        )
        
        if node_group is None:
            self.report({'ERROR'}, f"Failed to create node group for {self.field_type} field")
            return {'CANCELLED'}
        
        # Получаем базовое имя модификатора
        base_mod_name = FIELD_MOD_NAMES[self.field_type]
        
        # Создаем уникальное имя для модификатора
        modifier_name = base_mod_name
        counter = 1
        while modifier_name in obj.modifiers:
            modifier_name = f"{base_mod_name}.{counter:03d}"
            counter += 1
        
        # Добавляем модификатор
        modifier = obj.modifiers.new(name=modifier_name, type='NODES')
        
        # Теперь безопасно устанавливаем группу узлов
        modifier.node_group = node_group
        
        self.report({'INFO'}, f"{base_mod_name} '{modifier_name}' создан.")
        return {'FINISHED'}

class FIELD_OT_move_modifier(bpy.types.Operator):
    """Move field modifier up or down"""
    bl_idname = "object.move_field"
    bl_label = "Move Field"
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
            if self.direction == 'UP':
                bpy.ops.object.modifier_move_up(modifier=self.modifier_name)
            else:
                bpy.ops.object.modifier_move_down(modifier=self.modifier_name)
        return {'FINISHED'}


class FIELD_OT_delete_field(bpy.types.Operator):
    """Delete this field"""
    bl_idname = "object.delete_field"
    bl_label = "Delete Field"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.active_object
        if obj and self.modifier_name in obj.modifiers:
            modifier = obj.modifiers[self.modifier_name]
            node_group = modifier.node_group
            
            # Пытаемся удалить гизмо, если он есть
            try:
                sphere_obj = modifier.get("Sphere")
                if sphere_obj and hasattr(sphere_obj, 'users') and sphere_obj.users <= 1:
                    bpy.data.objects.remove(sphere_obj)
            except:
                pass
            
            # Удаляем модификатор
            obj.modifiers.remove(modifier)
            
            # Удаляем группу узлов, если она больше не используется
            if node_group and node_group.users == 0:
                bpy.data.node_groups.remove(node_group)
        
        return {'FINISHED'}
