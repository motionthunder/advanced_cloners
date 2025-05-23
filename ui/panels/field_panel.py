import bpy
from bpy.types import Panel
from ..common.ui_utils import display_socket_prop, is_element_expanded
from ..common.ui_constants import (
    UI_CLONER_PANEL_CATEGORY,
    UI_SCALE_Y_LARGE,
    ICON_FIELD, ICON_ADD, ICON_REMOVE, ICON_EXPAND, ICON_COLLAPSE,
    ICON_SPHERE_FIELD
)
from ...models.fields import FIELD_TYPES, FIELD_NODE_GROUP_PREFIXES

class FIELD_PT_main_panel(Panel):
    """Panel for fields"""
    bl_label = "Fields"
    bl_idname = "FIELD_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UI_CLONER_PANEL_CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Кнопки создания полей
        grid = layout.grid_flow(columns=2, even_columns=True)
        grid.scale_y = UI_SCALE_Y_LARGE
        for field_id, field_name, _, field_icon in FIELD_TYPES:
            op = grid.operator("object.create_field", text=field_name, icon=field_icon)
            op.field_type = field_id

        # Отобразим активные поля, если есть
        obj = context.active_object
        if not obj:
            layout.label(text="Select an object")
            return

        # Находим все поля на объекте
        fields = []
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group and any(mod.node_group.name.startswith(p) for p in FIELD_NODE_GROUP_PREFIXES):
                fields.append(mod)

        # Отображаем поля только если они есть
        if fields:
            layout.separator()
            layout.label(text=f"Fields: {len(fields)}", icon=ICON_FIELD)

            # Отображаем каждое поле
            for mod in fields:
                self.draw_field_ui(context, layout, obj, mod)

    def draw_field_ui(self, context, layout, obj, mod):
        # Создаем бокс для каждого поля
        box = layout.box()
        row = box.row()

        # Получаем состояние раскрытия из нашей системы
        expanded = is_element_expanded(context, obj.name, mod.name, "field_expanded_states")

        # Кнопка раскрытия/сворачивания
        op = row.operator("object.toggle_field_expanded", text="", icon=ICON_EXPAND if expanded else ICON_COLLAPSE, emboss=False)
        op.obj_name = obj.name
        op.modifier_name = mod.name

        # Название поля
        row.label(text=f"{mod.name}", icon=ICON_FIELD)

        # Кнопка видимости
        row.prop(mod, "show_viewport", text="", icon='HIDE_OFF' if mod.show_viewport else 'HIDE_ON', emboss=False)

        # Кнопки управления
        ctrl_row = row.row(align=True)

        # Кнопки перемещения вверх/вниз
        op = ctrl_row.operator("object.move_field", text="", icon="TRIA_UP")
        op.modifier_name = mod.name
        op.direction = 'UP'

        op = ctrl_row.operator("object.move_field", text="", icon="TRIA_DOWN")
        op.modifier_name = mod.name
        op.direction = 'DOWN'

        # Кнопка удаления
        op = ctrl_row.operator("object.delete_field", text="", icon=ICON_REMOVE)
        op.modifier_name = mod.name

        # Если поле развернуто, показываем его параметры
        if expanded and mod.node_group and hasattr(mod.node_group, 'interface'):
            content_col = box.column(align=True)

            # Проверяем, есть ли у поля привязанный гизмо
            gizmo_box = content_col.box()
            gizmo_box.label(text="Field Gizmo:", icon=ICON_SPHERE_FIELD)

            has_gizmo = False
            try:
                sphere_obj = mod.get("Sphere")
                if sphere_obj:
                    has_gizmo = True
                    gizmo_row = gizmo_box.row(align=True)
                    gizmo_row.label(text=sphere_obj.name)
                    select_op = gizmo_row.operator("object.select_field_gizmo", text="Select Gizmo", icon='RESTRICT_SELECT_OFF')
                    select_op.field_name = mod.name

                    # Подсказка для пользователя
                    gizmo_box.label(text="Move the gizmo to change the field position")
            except:
                pass

            if not has_gizmo:
                create_op = gizmo_box.operator("object.create_field_gizmo", text="Create Gizmo")
                create_op.field_name = mod.name

            # Параметры силы поля
            strength_box = content_col.box()
            strength_box.label(text="Field Strength:", icon='FORCE_FORCE')

            # Быстрые кнопки для регулировки силы
            strength_row = strength_box.row(align=True)
            decrease = strength_row.operator("object.adjust_field_strength", text="", icon=ICON_REMOVE)
            decrease.field_name = mod.name
            decrease.action = 'DECREASE'

            # Отображаем Inner Strength
            display_socket_prop(strength_row, mod, "Inner Strength", text="")

            increase = strength_row.operator("object.adjust_field_strength", text="", icon=ICON_ADD)
            increase.field_name = mod.name
            increase.action = 'INCREASE'

            reset = strength_row.operator("object.adjust_field_strength", text="", icon='LOOP_BACK')
            reset.field_name = mod.name
            reset.action = 'RESET'



            # Сортировка параметров полей
            falloff = content_col.box()
            falloff.label(text="Field Falloff:", icon='GRAPH')
            display_socket_prop(falloff, mod, "Falloff", text="Falloff Distance")
            display_socket_prop(falloff, mod, "Outer Strength", text="Outer Value")
            display_socket_prop(falloff, mod, "Mode", text="Curve Type")
            display_socket_prop(falloff, mod, "Strength", text="Effect Strength")

# Функции регистрации и отмены регистрации
def register():
    bpy.utils.register_class(FIELD_PT_main_panel)

def unregister():
    bpy.utils.unregister_class(FIELD_PT_main_panel)
