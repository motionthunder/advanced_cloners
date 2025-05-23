import bpy
from bpy.types import Panel
from ...models.effectors import EFFECTOR_TYPES
from ...core.common.constants import EFFECTOR_NODE_GROUP_PREFIXES
from ..common.ui_utils import is_element_expanded, display_socket_prop
from ..common.effector_utils import draw_effector_ui
from ..common.ui_constants import (
    UI_EFFECTOR_PANEL_CATEGORY, UI_EFFECTOR_PANEL_REGION,
    ICON_ADD, ICON_REMOVE,
    UI_SCALE_Y_LARGE
)

class EFFECTOR_PT_main_panel(Panel):
    """Panel for effectors"""
    bl_label = "Effectors"
    bl_idname = "EFFECTOR_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_EFFECTOR_PANEL_REGION
    bl_category = UI_EFFECTOR_PANEL_CATEGORY

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Кнопки создания эффекторов
        grid = layout.grid_flow(columns=2, even_columns=True)
        grid.scale_y = UI_SCALE_Y_LARGE
        
        for eff_id, eff_name, _, eff_icon in EFFECTOR_TYPES:
            # Убираем слово "Effector" из названия кнопки
            button_name = eff_name.replace(" Effector", "")
            op = grid.operator("object.create_effector", text=button_name, icon=eff_icon)
            op.effector_type = eff_id

        if not obj:
            layout.label(text="Select an object")
            return

        # Находим все эффекторы на объекте
        eff_mods = []
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                if any(mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES):
                    eff_mods.append(mod)
        
        # Если есть эффекторы, показываем их количество
        if eff_mods:
            layout.separator()
            layout.label(text=f"Effectors: {len(eff_mods)}")
            
            # Отображаем каждый эффектор используя функцию из effector_utils
            for mod in eff_mods:
                draw_effector_ui(context, layout, obj, mod)
                
    def draw_field_ui(self, context, box, obj, mod, socket):
        """Отрисовка UI для поля эффектора - перенесено из effector_panels.py"""
        row = box.row(align=True)
        row.use_property_split = True
        row.use_property_decorate = False
        
        # Определяем, использует ли эффектор поле
        use_field = mod.get("Use Field", False)
        
        # Если есть Use Field, включаем/отключаем его
        if "Use Field" in [s.name for s in mod.node_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']:
            row.prop(mod, f'["{socket.identifier}"]', text=socket.name)
            
            # Чекбокс для Use Field
            for s in mod.node_group.interface.items_tree:
                if s.item_type == 'SOCKET' and s.in_out == 'INPUT' and s.name == 'Use Field':
                    row.prop(mod, f'["{s.identifier}"]', text="")
                    use_field = mod[s.identifier]
                    break
        else:
            row.prop(mod, f'["{socket.identifier}"]', text=socket.name)
        
        # Если поле используется, предлагаем возможность отключить его
        if use_field:
            remove_row = box.row()
            op = remove_row.operator("object.effector_remove_field", text="Disconnect Field", icon=ICON_REMOVE)
            op.effector_name = mod.name
        else:
            # Если поле не используется, предлагаем возможность подключить его
            add_row = box.row()
            op = add_row.operator("object.effector_add_field", text="Connect Field", icon=ICON_ADD)
            op.effector_name = mod.name

# Функции регистрации и отмены регистрации
def register():
    bpy.utils.register_class(EFFECTOR_PT_main_panel)

def unregister():
    bpy.utils.unregister_class(EFFECTOR_PT_main_panel)
