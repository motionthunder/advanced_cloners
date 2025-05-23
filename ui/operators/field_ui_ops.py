import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, FloatProperty, BoolProperty

from ..common.ui_utils import is_element_expanded, set_element_expanded
from ...operations.helpers.field_params_utils import setup_field_params

class FIELD_OT_toggle_expanded(Operator):
    """Toggle expanded state of a field"""
    bl_idname = "object.toggle_field_expanded"
    bl_label = "Toggle Field Expanded"

    obj_name: StringProperty()
    modifier_name: StringProperty()

    def execute(self, context):
        current = is_element_expanded(context, self.obj_name, self.modifier_name, "field_expanded_states")
        set_element_expanded(context, self.obj_name, self.modifier_name, not current, "field_expanded_states")
        return {'FINISHED'}

class FIELD_OT_create_field(Operator):
    """Create a new field"""
    bl_idname = "object.create_field"
    bl_label = "Create Field"
    bl_options = {'REGISTER', 'UNDO'}

    field_type: StringProperty(default="SPHERE")

    def execute(self, context):
        print("Создание сферического поля...")

        if not context.active_object:
            self.report({'ERROR'}, "Пожалуйста, выберите объект")
            return {'CANCELLED'}

        obj = context.active_object
        print(f"Создание поля на объекте: {obj.name}")

        try:
            # Создаем уникальное имя для модификатора
            modifier_name = "Sphere Field"
            counter = 1
            while modifier_name in obj.modifiers:
                modifier_name = f"Sphere Field.{counter:03d}"
                counter += 1

            # Добавляем модификатор геометрических нодов
            mod = obj.modifiers.new(name=modifier_name, type='NODES')

            # Используем готовую функцию вместо создания своей группы нодов
            from ...models.fields.sphere_field import spherefield_node_group
            node_group = spherefield_node_group()

            # Устанавливаем группу нодов в модификатор
            mod.node_group = node_group

            # Создаем пустой объект для визуализации поля
            field_empty = bpy.data.objects.new(f"{modifier_name}_Gizmo", None)
            field_empty.empty_display_type = 'SPHERE'
            field_empty.empty_display_size = 1.0
            # Ставим гизмо на позицию объекта
            field_empty.location = obj.location.copy()
            bpy.context.collection.objects.link(field_empty)

            # Привязываем пустой объект к полю
            try:
                mod["Sphere"] = field_empty
                print(f"Создан пустой объект {field_empty.name} для визуализации поля")

                # Настраиваем размер гизмо в зависимости от параметров поля
                field_empty.empty_display_size = 2.0  # Базовый размер

                # Добавляем пользовательские свойства для легкого доступа
                field_empty["field_name"] = modifier_name
                field_empty["field_owner"] = obj.name
            except Exception as e:
                print(f"Ошибка привязки пустого объекта к полю: {e}")

            # Устанавливаем параметры поля из конфигурационного файла
            try:
                setup_field_params(mod, self.field_type)
            except Exception as e:
                print(f"Ошибка установки параметров поля: {e}")

            # Перемещаем модификатор поля перед эффекторами
            # для правильного порядка выполнения
            # Находим первый эффектор
            effector_index = -1
            for i, modifier in enumerate(obj.modifiers):
                if modifier.type == 'NODES' and modifier.node_group and "Effector" in modifier.node_group.name:
                    effector_index = i
                    break

            # Если есть эффектор, перемещаем поле перед ним
            if effector_index > 0:
                # В Blender перемещение происходит последовательно на одну позицию
                current_index = len(obj.modifiers) - 1  # индекс нового модификатора (последний)
                while current_index > effector_index:
                    bpy.ops.object.modifier_move_up(modifier=mod.name)
                    current_index -= 1

            # Выбираем созданный гизмо для удобства
            bpy.ops.object.select_all(action='DESELECT')
            field_empty.select_set(True)
            bpy.context.view_layer.objects.active = field_empty

            self.report({'INFO'}, f"Field '{modifier_name}' created. You can move the field by moving its gizmo.")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error creating field: {str(e)}")
            print(f"ERROR: {str(e)}")
            return {'CANCELLED'}


class FIELD_OT_select_gizmo(Operator):
    """Select field gizmo"""
    bl_idname = "object.select_field_gizmo"
    bl_label = "Select Field Gizmo"
    bl_options = {'REGISTER', 'UNDO'}

    field_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.field_name)

        if not mod or not mod.node_group:
            return {'CANCELLED'}

        # Получаем объект-гизмо из параметра Sphere
        gizmo_obj = None
        try:
            gizmo_obj = mod.get("Sphere")
        except:
            pass

        if gizmo_obj:
            # Выбираем только гизмо
            bpy.ops.object.select_all(action='DESELECT')
            gizmo_obj.select_set(True)
            bpy.context.view_layer.objects.active = gizmo_obj
            self.report({'INFO'}, f"Выбран гизмо поля {gizmo_obj.name}. Перемещайте его для изменения положения поля.")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Гизмо поля не найден")
            return {'CANCELLED'}


class FIELD_OT_create_sphere_gizmo(Operator):
    """Create a sphere gizmo for this field"""
    bl_idname = "object.create_field_gizmo"
    bl_label = "Create Field Gizmo"
    bl_options = {'REGISTER', 'UNDO'}

    field_name: StringProperty()

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.field_name)

        if not mod or not mod.node_group:
            return {'CANCELLED'}

        # Создаем пустой объект для визуализации поля
        field_empty = bpy.data.objects.new(f"{mod.name}_Gizmo", None)
        field_empty.empty_display_type = 'SPHERE'
        field_empty.empty_display_size = 1.0
        # Размещаем на позиции объекта
        field_empty.location = obj.location.copy()
        bpy.context.collection.objects.link(field_empty)

        # Добавляем пользовательские свойства
        field_empty["field_name"] = mod.name
        field_empty["field_owner"] = obj.name

        # Привязываем пустой объект к полю
        try:
            mod["Sphere"] = field_empty

            # Выбираем созданный гизмо
            bpy.ops.object.select_all(action='DESELECT')
            field_empty.select_set(True)
            bpy.context.view_layer.objects.active = field_empty

            self.report({'INFO'}, f"Создан гизмо поля {field_empty.name}. Перемещайте его для управления полем.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка привязки гизмо к полю: {str(e)}")
            return {'CANCELLED'}


class FIELD_OT_adjust_field_strength(Operator):
    """Adjust field strength"""
    bl_idname = "object.adjust_field_strength"
    bl_label = "Adjust Field"
    bl_options = {'REGISTER', 'UNDO'}

    field_name: StringProperty()
    action: EnumProperty(
        items=[
            ('INCREASE', 'Increase', 'Increase field strength'),
            ('DECREASE', 'Decrease', 'Decrease field strength'),
            ('RESET', 'Reset', 'Reset to default')
        ],
        default='INCREASE'
    )

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get(self.field_name)

        if not mod or not mod.node_group:
            return {'CANCELLED'}

        try:
            # Получаем текущее значение силы поля
            current_inner = mod.get("Inner Strength", 1.0)

            # Изменяем в зависимости от действия
            if self.action == 'INCREASE':
                # Увеличиваем на 25%
                mod["Inner Strength"] = min(current_inner + 0.25, 1.0)
                self.report({'INFO'}, f"Сила поля увеличена до {mod['Inner Strength']:.2f}")
            elif self.action == 'DECREASE':
                # Уменьшаем на 25%
                mod["Inner Strength"] = max(current_inner - 0.25, 0.0)
                self.report({'INFO'}, f"Сила поля уменьшена до {mod['Inner Strength']:.2f}")
            else:  # RESET
                # Сбрасываем параметры поля к значениям из конфигурационного файла
                setup_field_params(mod, "SPHERE")
                self.report({'INFO'}, "Параметры поля сброшены к значениям по умолчанию")

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка изменения параметров поля: {str(e)}")
            return {'CANCELLED'}

# Список классов для регистрации
classes = (
    FIELD_OT_toggle_expanded,
    FIELD_OT_create_field,
    FIELD_OT_select_gizmo,
    FIELD_OT_create_sphere_gizmo,
    FIELD_OT_adjust_field_strength
)

# Функции регистрации и отмены регистрации
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
