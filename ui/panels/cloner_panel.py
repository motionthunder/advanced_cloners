import bpy
from bpy.types import Panel
from bpy.props import StringProperty, BoolProperty, EnumProperty

from ..common.ui_utils import is_element_expanded
from ..common.cloner_utils import (
    draw_grid_cloner_settings,
    draw_linear_cloner_settings,
    draw_circle_cloner_settings,
    draw_collection_cloner_settings,
    draw_common_cloner_settings
)
from ..common.ui_constants import (
    UI_SCALE_Y_LARGE, UI_SCALE_Y_XLARGE,
    UI_STACKED_LABEL_TEXT, UI_STACKED_CHECKBOX_SCALE_Y,
    UI_STACK_PADDING, UI_STACK_RIGHT_PADDING, UI_STACK_ALIGNMENT,
    UI_CLONER_PANEL_CATEGORY,
    ICON_LINK, ICON_CLONER,
    ICON_GRID_CLONER, ICON_LINEAR_CLONER, ICON_CIRCLE_CLONER
)

from ...models.cloners import CLONER_GROUP_NAMES, CLONER_TYPES, CLONER_NODE_GROUP_PREFIXES
from ...core.utils.cloner_utils import get_cloner_chain_for_object
from ...core.common.constants import CLONER_MOD_NAMES

# Обработчик изменения типа источника клонирования
def update_source_type(self, context):
    """Обработчик изменения типа источника клонирования"""
    obj = context.active_object
    if not obj:
        return

    # Находим активный модификатор клонера
    from ...core.utils.cloner_utils import get_active_cloner
    active_cloner = get_active_cloner(obj)
    if not active_cloner:
        return

    # Получаем текущий тип
    new_type = context.scene.source_type_for_cloner
    old_type = active_cloner.get("source_type", "OBJECT")

    # Обрабатываем переключение типа
    # Используем заглушку - в дальнейшем функция будет перенесена в core.constants
    success = True

    # Обрабатываем результат
    if not success:
        # Восстанавливаем предыдущий тип
        context.scene.source_type_for_cloner = old_type
        return

    # Сохраняем новый тип в модификаторе
    active_cloner["source_type"] = new_type

class CLONERS_PT_Main(Panel):
    """Cloners main panel"""
    bl_label = "Cloners"
    bl_idname = "CLONERS_PT_Main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UI_CLONER_PANEL_CATEGORY

    def draw(self, context):
        layout = self.layout

        obj = context.active_object

        if obj is None:
            layout.label(text="No active object")
            return

        # Check if this object has a cloner chain
        cloner_chain = get_cloner_chain_for_object(obj)

        # Add panel for creating new cloners
        creation_box = layout.box()

        # Object/Collection selection as radio buttons
        source_row = creation_box.row(align=True)
        source_row.scale_y = UI_SCALE_Y_LARGE
        source_row.label(text="Clone Source:")
        source_row.prop(context.scene, "source_type_for_cloner", expand=True)

        # Collection selector (only visible when Collection is selected)
        if context.scene.source_type_for_cloner == 'COLLECTION':
            coll_row = creation_box.row(align=True)
            coll_row.scale_y = UI_SCALE_Y_LARGE
            coll_row.label(text="Collection:")
            coll_row.prop_search(context.scene, "collection_to_clone", bpy.data, "collections", text="")

            # Добавляем чекбокс Anti-Recursion для коллекций
            anti_recursion_row = creation_box.row(align=True)
            anti_recursion_row.scale_y = UI_STACKED_CHECKBOX_SCALE_Y

            # Добавляем пустой элемент для смещения группы вправо (аналог CSS margin-left: auto)
            ar_spacer = anti_recursion_row.column()
            ar_spacer.alignment = 'EXPAND'
            ar_spacer.scale_x = UI_STACK_ALIGNMENT
            ar_spacer.label(text="")

            # Создаем подгруппу для текста и чекбокса с компактным выравниванием
            ar_group = anti_recursion_row.row(align=True)
            ar_group.alignment = 'RIGHT'

            # Добавляем текст с отступом справа (как CSS padding-right)
            ar_group.label(text="Anti-Recursion")

            # Добавляем чекбокс с прижатием к правому краю
            # Чекбокс всегда активен, независимо от состояния стековых модификаторов
            ar_checkbox = ar_group.row()
            ar_checkbox.enabled = True
            ar_checkbox.prop(context.scene, "use_anti_recursion", text="")

            # Добавляем небольшой отступ справа (как CSS padding-right)
            ar_right_padding = anti_recursion_row.column()
            ar_right_padding.scale_x = UI_STACK_RIGHT_PADDING / 100
            ar_right_padding.label(text="")

        # Add the stacked modifiers option for object cloners right after source selection
        if context.scene.source_type_for_cloner == 'OBJECT':
            # Создаем свойство в сцене, если его еще нет
            if not hasattr(context.scene, "use_stacked_modifiers"):
                bpy.types.Scene.use_stacked_modifiers = bpy.props.BoolProperty(
                    default=False,
                    name="Use Stacked Modifiers",
                    description="Create all cloners as modifiers on a single object instead of creating a chain of objects. This allows you to reorder cloners by moving modifiers up/down."
                )

            # Создаем чистую современную компоновку в стиле CSS для чекбокса Stack
            stack_row = creation_box.row(align=True)
            stack_row.scale_y = UI_STACKED_CHECKBOX_SCALE_Y

            # Добавляем пустой элемент для смещения группы вправо (аналог CSS margin-left: auto)
            spacer = stack_row.column()
            spacer.alignment = 'EXPAND'
            spacer.scale_x = UI_STACK_ALIGNMENT
            spacer.label(text="")

            # Создаем подгруппу для текста и чекбокса с компактным выравниванием
            stack_group = stack_row.row(align=True)
            stack_group.alignment = 'RIGHT'

            # Добавляем текст с отступом справа (как CSS padding-right)
            text_label = stack_group.label(text=UI_STACKED_LABEL_TEXT)

            # Добавляем чекбокс с прижатием к правому краю
            checkbox = stack_group.prop(context.scene, "use_stacked_modifiers", text="")

            # Добавляем небольшой отступ справа (как CSS padding-right)
            right_padding = stack_row.column()
            right_padding.scale_x = UI_STACK_RIGHT_PADDING / 100
            right_padding.label(text="")

            # Добавляем чекбокс Anti-Recursion под Stacking Cloners
            anti_recursion_row = creation_box.row(align=True)
            anti_recursion_row.scale_y = UI_STACKED_CHECKBOX_SCALE_Y

            # Добавляем пустой элемент для смещения группы вправо (аналог CSS margin-left: auto)
            ar_spacer = anti_recursion_row.column()
            ar_spacer.alignment = 'EXPAND'
            ar_spacer.scale_x = UI_STACK_ALIGNMENT
            ar_spacer.label(text="")

            # Создаем подгруппу для текста и чекбокса с компактным выравниванием
            ar_group = anti_recursion_row.row(align=True)
            ar_group.alignment = 'RIGHT'

            # Добавляем текст с отступом справа (как CSS padding-right)
            ar_group.label(text="Anti-Recursion")

            # Добавляем чекбокс с прижатием к правому краю
            # Чекбокс всегда активен, независимо от состояния стековых модификаторов
            ar_checkbox = ar_group.row()
            ar_checkbox.enabled = True
            ar_checkbox.prop(context.scene, "use_anti_recursion", text="")

            # Добавляем небольшой отступ справа (как CSS padding-right)
            ar_right_padding = anti_recursion_row.column()
            ar_right_padding.scale_x = UI_STACK_RIGHT_PADDING / 100
            ar_right_padding.label(text="")

        # Cloner type selection with prominent buttons
        creation_box.separator()

        # Label for cloner types
        cloner_label_row = creation_box.row()
        cloner_label_row.label(text="Cloner Type:", icon=ICON_CLONER)

        # Big buttons for cloner types
        type_grid = creation_box.grid_flow(columns=3, even_columns=True, even_rows=True)
        type_grid.scale_y = UI_SCALE_Y_XLARGE  # Make buttons larger and more prominent

        for cloner_type, details in [
            ("GRID", {"icon": ICON_GRID_CLONER, "label": "Grid"}),
            ("LINEAR", {"icon": ICON_LINEAR_CLONER, "label": "Linear"}),
            ("CIRCLE", {"icon": ICON_CIRCLE_CLONER, "label": "Circle"})
        ]:
            # Create button with depress=True to make it more obvious it's a button
            button = type_grid.operator(
                "object.create_cloner",
                text=details["label"],
                icon=details["icon"],
                depress=False
            )
            button.cloner_type = cloner_type
            button.source_type = context.scene.source_type_for_cloner

            # If collection is selected, pass the collection name
            if context.scene.source_type_for_cloner == 'COLLECTION' and context.scene.collection_to_clone:
                button.target_collection = context.scene.collection_to_clone

            button.use_custom_group = True  # Always use custom groups

            # Важно: устанавливаем параметр stacked_modifiers здесь
            if context.scene.source_type_for_cloner == 'OBJECT':
                button.use_stacked_modifiers = context.scene.use_stacked_modifiers

        # НОВЫЙ РАЗДЕЛ: Диагностика и исправление клонеров
        layout.separator()
        
        # Добавляем заголовок для утилит
        utils_box = layout.box()
        utils_header = utils_box.row()
        utils_header.label(text="Anti-Recursion Tools", icon="TOOL_SETTINGS")
        
        # Кнопка диагностики
        diag_row = utils_box.row()
        diag_row.scale_y = UI_SCALE_Y_LARGE
        diag_row.operator("object.diagnose_cloners", text="Diagnose Cloners", icon="VIEWZOOM")
        
        # Кнопка исправления (с улучшенным алгоритмом)
        fix_row = utils_box.row()
        fix_row.scale_y = UI_SCALE_Y_LARGE
        
        # Проверяем наличие улучшенного оператора
        try:
            # Пытаемся получить улучшенный оператор
            from ...operations.fix_recursion_improved import CLONER_OT_fix_recursion_depth_improved
            # Если успешно, используем улучшенную версию
            fix_row.operator("object.fix_cloner_recursion_improved", text="Fix All Issues (Improved)", icon="CHECKMARK")
        except ImportError:
            # Если улучшенный оператор недоступен, используем стандартный
            fix_row.operator("object.fix_cloner_recursion", text="Fix Recursion Issues", icon="FILE_REFRESH")

        # Add button for updating all cloners with effectors if there are any cloners with anti-recursion
        has_cloners_with_anti_recursion = False
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for modifier in obj.modifiers:
                if modifier.type != 'NODES' or not modifier.node_group:
                    continue
                node_group = modifier.node_group
                # Check if this is a cloner node group
                is_cloner = False
                for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner", "ObjectCloner"]:
                    if prefix in node_group.name:
                        is_cloner = True
                        break
                if not is_cloner:
                    continue
                # Check if the cloner has anti-recursion
                for node in node_group.nodes:
                    if node.name == "Anti-Recursion Switch":
                        has_cloners_with_anti_recursion = True
                        break
                if has_cloners_with_anti_recursion:
                    break
            if has_cloners_with_anti_recursion:
                break

        if has_cloners_with_anti_recursion:
            effector_row = utils_box.row()
            effector_row.scale_y = UI_SCALE_Y_LARGE
            effector_row.operator("object.update_all_cloner_effectors", text="Update Effectors", icon="FILE_REFRESH")

        # Add toggle for showing cloner chain
        if cloner_chain:
            layout.separator()
            chain_row = layout.row()
            chain_row.scale_y = UI_SCALE_Y_LARGE
            chain_row.prop(context.scene, "show_cloner_chain",
                         text="Edit Cloner Chain",
                         toggle=True,
                         icon=ICON_LINK)

            # Show cloner chain if toggled on
            if context.scene.show_cloner_chain:
                self.draw_cloner_chain(context, layout, obj, cloner_chain)

        # List existing cloners on this object
        self.draw_cloners_list(context, layout)

    def draw_cloner_chain(self, context, layout, obj, cloner_chain):
        """Draw the UI for the cloner chain"""
        if not cloner_chain:
            return

        # Create a compact box for the chain
        box = layout.box()

        # Compact header
        header_row = box.row(align=True)
        header_row.scale_y = 1.1
        header_row.label(text="Cloner Chain", icon="LINKED")
        header_row.label(text=f"({len(cloner_chain)})", icon="DECORATE_OVERRIDE")

        # Create a more compact UI for the chain
        # Get the active cloner in the chain from scene property
        active_in_chain = context.scene.active_cloner_in_chain

        # If chain is short (1-2 items), use a row, otherwise use a column
        is_short_chain = len(cloner_chain) <= 3
        if is_short_chain:
            # Horizontal layout for short chains
            chain_row = box.row(align=True)
            chain_row.scale_y = 1.0

            for i, link in enumerate(cloner_chain):
                obj_name = link["object"]
                mod_name = link["modifier"]

                # Check if this is the active cloner in chain
                is_active = active_in_chain == f"{obj_name}|{mod_name}"

                # Add separator between items
                if i > 0:
                    chain_row.label(text="→", icon="BLANK1")

                # Button to activate this cloner
                button = chain_row.operator(
                    "object.set_cloner_active_in_chain",
                    text=f"{mod_name.split('.')[0]}" if "." in mod_name else mod_name,
                    icon="RADIOBUT_ON" if is_active else "RADIOBUT_OFF",
                    depress=is_active
                )
                button.object_name = obj_name
                button.modifier_name = mod_name
        else:
            # Vertical layout with compact buttons for longer chains
            chain_col = box.column(align=True)

            for i, link in enumerate(cloner_chain):
                obj_name = link["object"]
                mod_name = link["modifier"]

                # Check if this is the active cloner in chain
                is_active = active_in_chain == f"{obj_name}|{mod_name}"

                # Определяем тип клонера
                is_collection = False
                is_object_cloner = False

                # Проверить тип клонера по имени группы узлов и свойствам
                if obj_name in bpy.data.objects and mod_name in bpy.data.objects[obj_name].modifiers:
                    mod = bpy.data.objects[obj_name].modifiers[mod_name]
                    if mod.node_group:
                        if "CollectionCloner_" in mod.node_group.name or "original_collection" in mod:
                            is_collection = True
                        elif "ObjectCloner_" in mod.node_group.name:
                            is_object_cloner = True
                        # Treat standard object cloners as object cloners too
                        # Check node_group_name for cloner prefixes
                        elif any(prefix in mod.node_group.name for prefix in CLONER_NODE_GROUP_PREFIXES):
                            is_object_cloner = True
                # Также проверить по свойству из цепочки
                elif link.get("is_collection_cloner", False):
                    is_collection = True
                elif link.get("is_chained_cloner", False) and not link.get("is_collection_cloner", False):
                    is_object_cloner = True
                # Если не определен конкретный тип, но есть в цепочке - считаем объектным клонером по умолчанию
                elif not is_collection and not is_object_cloner:
                    is_object_cloner = True

                row = chain_col.row(align=True)

                # Show index number and icon
                icon = "OUTLINER_COLLECTION" if is_collection else "OBJECT_DATA" if is_object_cloner else "OUTLINER_OB_MESH"
                prefix = f"{i+1}."
                row.label(text=prefix, icon=icon)

                # Button to activate this cloner - simplified text
                cloner_name = f"{mod_name.split('.')[0]}" if "." in mod_name else mod_name
                if is_collection:
                    cloner_name += " (Collection)"
                elif is_object_cloner:
                    cloner_name += " (Object)"

                op = row.operator(
                    "object.set_cloner_active_in_chain",
                    text=cloner_name,
                    icon="RADIOBUT_ON" if is_active else "RADIOBUT_OFF",
                    depress=is_active
                )
                op.object_name = obj_name
                op.modifier_name = mod_name

        # If there's an active cloner in the chain, draw its settings
        if active_in_chain:
            parts = active_in_chain.split("|")
            if len(parts) == 2:
                active_obj_name, active_mod_name = parts

                # Only proceed if the object and modifier exist
                if active_obj_name in bpy.data.objects:
                    active_obj = bpy.data.objects[active_obj_name]
                    if active_mod_name in active_obj.modifiers:
                        active_mod = active_obj.modifiers[active_mod_name]

                        # Draw a separator
                        box.separator()

                        # Draw the settings for this cloner
                        settings_box = box.box()
                        col = settings_box.column()

                        # Compact header showing what we're editing
                        header_row = col.row()
                        header_row.label(text=f"Editing: {active_mod_name}", icon="TOOL_SETTINGS")

                        # Determine cloner type
                        if active_mod.node_group:
                            node_group_name = active_mod.node_group.name
                            cloner_type = None
                            is_collection_cloner = False

                            # Check if this is a collection cloner
                            if "CollectionCloner_" in node_group_name:
                                is_collection_cloner = True
                                # Extract type (format: CollectionCloner_TYPE_name...)
                                parts = node_group_name.split('_')
                                if len(parts) > 1:
                                    cloner_type = parts[1]  # GRID, LINEAR, CIRCLE
                            # Check if this is an object cloner - обрабатываем Object клонеры так же, как Collection
                            elif "ObjectCloner_" in node_group_name:
                                is_collection_cloner = True  # используем тот же вид UI, что и для коллекций
                                # Extract type (format: ObjectCloner_TYPE_name...)
                                parts = node_group_name.split('_')
                                if len(parts) > 1:
                                    cloner_type = parts[1]  # GRID, LINEAR, CIRCLE
                            else:
                                # Check node_group_name for cloner prefixes
                                for c_type, prefix in CLONER_GROUP_NAMES.items():
                                    parts = node_group_name.split('.')
                                    if parts[0] == prefix:
                                        cloner_type = c_type
                                        break

                            # Draw appropriate settings based on cloner type
                            if cloner_type:
                                col.separator()

                                # Determine the correct settings function to call
                                if is_collection_cloner:
                                    draw_collection_cloner_settings(col, active_mod, cloner_type)
                                else:
                                    if cloner_type == "GRID":
                                        draw_grid_cloner_settings(col, active_mod)
                                    elif cloner_type == "LINEAR":
                                        draw_linear_cloner_settings(col, active_mod)
                                    elif cloner_type == "CIRCLE":
                                        draw_circle_cloner_settings(col, active_mod)

                                # Common settings for all cloners
                                col.separator()
                                draw_common_cloner_settings(col, active_mod, context, is_chain_menu=True)

    def draw_cloners_list(self, context, layout):
        obj = context.active_object

        cloner_count = 0
        cloners_found = []
        collection_cloners_found = []
        stacked_cloners_found = []

        # Check if there are any cloners to display
        for modifier in obj.modifiers:
            if not (modifier.type == 'NODES' and modifier.node_group):
                continue

            # Check if this is a cloner - modified logic to support custom groups
            is_cloner = False
            is_collection_cloner = False
            is_stacked_cloner = modifier.get("is_stacked_cloner", False)  # Добавляем проверку стековых клонеров
            node_group_name = modifier.node_group.name
            cloner_type = None

            # Проверяем тип клонера
            # Стековые клонеры
            if is_stacked_cloner:
                is_cloner = True
                cloner_type = modifier.get("cloner_type", "GRID")  # Получаем тип из свойства
                cloner_count += 1
                stacked_cloners_found.append((modifier.name, node_group_name, cloner_type))
            # Клонеры коллекций
            elif "CollectionCloner_" in node_group_name:
                is_cloner = True
                is_collection_cloner = True

                # Extract cloner type from the name (format: CollectionCloner_TYPE_name...)
                parts = node_group_name.split('_')
                if len(parts) > 1:
                    cloner_type = parts[1]  # Extract type (GRID, LINEAR, CIRCLE)
                    cloner_count += 1
                    collection_cloners_found.append((modifier.name, node_group_name, cloner_type))
            # Проверка объектных клонеров
            elif "ObjectCloner_" in node_group_name:
                is_cloner = True
                is_collection_cloner = True  # используем тот же вид UI, что и для коллекций

                # Extract cloner type from the name (format: ObjectCloner_TYPE_name...)
                parts = node_group_name.split('_')
                if len(parts) > 1:
                    cloner_type = parts[1]  # Extract type (GRID, LINEAR, CIRCLE)
                    cloner_count += 1
                    collection_cloners_found.append((modifier.name, node_group_name, cloner_type))
            else:
                # Check if node_group_name contains any of the cloner prefixes
                for c_type, prefix in CLONER_GROUP_NAMES.items():
                    # Get the first part of the name (before any dots)
                    parts = node_group_name.split('.')
                    if parts[0] == prefix:
                        is_cloner = True
                        cloner_type = c_type
                        cloner_count += 1
                        # Treat standard cloners the same as collection cloners for UI purposes
                        is_collection_cloner = True
                        collection_cloners_found.append((modifier.name, node_group_name, cloner_type))
                        break

            if not is_cloner:
                continue

        # Show the cloners found if any
        if cloners_found or collection_cloners_found or stacked_cloners_found:
            layout.separator()
            layout.label(text=f"Cloners: {cloner_count}")

            # Draw each regular cloner
            for modifier_name, node_group_name, cloner_type in cloners_found:
                self.draw_cloner_box(context, layout, obj, modifier_name, node_group_name, cloner_type, False)

            # Draw each collection cloner
            for modifier_name, node_group_name, cloner_type in collection_cloners_found:
                self.draw_cloner_box(context, layout, obj, modifier_name, node_group_name, cloner_type, True)

            # Draw each stacked cloner
            for modifier_name, node_group_name, cloner_type in stacked_cloners_found:
                self.draw_stacked_cloner_box(context, layout, obj, modifier_name, node_group_name, cloner_type)

    def draw_cloner_box(self, context, layout, obj, modifier_name, node_group_name, cloner_type, is_collection_cloner):
        modifier = obj.modifiers.get(modifier_name)
        if not modifier:
            return

        # Get icon based on type
        icon = "MESH_GRID"  # default
        if cloner_type == "LINEAR":
            icon = "SORTSIZE"
        elif cloner_type == "CIRCLE":
            icon = "MESH_CIRCLE"

        # Create box for each cloner
        box = layout.box()
        row = box.row()

        # Get expanded state from our property system
        expanded = is_element_expanded(context, obj.name, modifier_name, "cloner_expanded_states")

        # Cloner label + expand button
        # First expansion button
        op = row.operator("object.toggle_cloner_expanded", text="", icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT', emboss=False)
        op.obj_name = obj.name
        op.modifier_name = modifier_name

        # Then cloner name
        main_label = f"{modifier.name} [{node_group_name}]"
        if is_collection_cloner:
            if "CollectionCloner_" in node_group_name:
                main_label += " (Collection)"
            elif "ObjectCloner_" in node_group_name:
                main_label += " (Object)"
        row.label(text=main_label, icon=icon)

        # Visibility toggle
        row.prop(modifier, "show_viewport", text="", icon='HIDE_OFF' if modifier.show_viewport else 'HIDE_ON', emboss=False)

        # Up/Down/Delete buttons
        row = row.row(align=True)
        op = row.operator("object.move_cloner", text="", icon="TRIA_UP")
        op.modifier_name = modifier.name
        op.direction = 'UP'

        op = row.operator("object.move_cloner", text="", icon="TRIA_DOWN")
        op.modifier_name = modifier.name
        op.direction = 'DOWN'

        op = row.operator("object.delete_cloner", text="", icon="X")
        op.modifier_name = modifier.name

        # Draw expanded modifier properties
        if expanded:
            # Check if this is a standard object cloner (not a collection or object cloner)
            is_standard_object_cloner = not is_collection_cloner

            # Update: Treat standard object cloners just like collection cloners
            if is_collection_cloner or is_standard_object_cloner:
                draw_collection_cloner_settings(box, modifier, cloner_type)
            else:
                # This code branch should never be reached now
                if cloner_type == "GRID":
                    draw_grid_cloner_settings(box, modifier)
                elif cloner_type == "LINEAR":
                    draw_linear_cloner_settings(box, modifier)
                elif cloner_type == "CIRCLE":
                    draw_circle_cloner_settings(box, modifier)


            # Common settings for all cloners
            draw_common_cloner_settings(box, modifier, context)

    def draw_stacked_cloner_box(self, context, layout, obj, modifier_name, node_group_name, cloner_type):
        """Отображение специального UI для стековых клонеров"""
        from ..common.ui_utils import get_stacked_cloner_info
        modifier = obj.modifiers.get(modifier_name)
        if not modifier:
            return

        # Получаем информацию о стековом клонере
        is_stacked, stacked_type = get_stacked_cloner_info(modifier)

        # Если тип определен в стековом клонере, используем его
        if is_stacked and stacked_type:
            cloner_type = stacked_type

        # Get icon based on type
        icon = "MESH_GRID"  # default
        if cloner_type == "LINEAR":
            icon = "SORTSIZE"
        elif cloner_type == "CIRCLE":
            icon = "MESH_CIRCLE"

        # Create box for each cloner
        box = layout.box()
        row = box.row()

        # Get expanded state from our property system
        expanded = is_element_expanded(context, obj.name, modifier_name, "cloner_expanded_states")

        # Cloner label + expand button
        # First expansion button
        op = row.operator("object.toggle_cloner_expanded", text="", icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT', emboss=False)
        op.obj_name = obj.name
        op.modifier_name = modifier_name

        # Используем такой же формат названия, как у обычных клонеров
        main_label = f"{cloner_type.title()} Object Cloner"
        row.label(text=main_label, icon=icon)

        # Visibility toggle
        row.prop(modifier, "show_viewport", text="", icon='HIDE_OFF' if modifier.show_viewport else 'HIDE_ON', emboss=False)

        # Up/Down/Delete buttons
        row = row.row(align=True)
        op = row.operator("object.move_cloner", text="", icon="TRIA_UP")
        op.modifier_name = modifier.name
        op.direction = 'UP'

        op = row.operator("object.move_cloner", text="", icon="TRIA_DOWN")
        op.modifier_name = modifier.name
        op.direction = 'DOWN'

        op = row.operator("object.delete_cloner", text="", icon="X")
        op.modifier_name = modifier.name

        # Draw expanded modifier properties
        if expanded:
            # Используем тот же формат отображения, что и для обычных клонеров
            if cloner_type == "GRID":
                draw_grid_cloner_settings(box, modifier)
            elif cloner_type == "LINEAR":
                draw_linear_cloner_settings(box, modifier)
            elif cloner_type == "CIRCLE":
                draw_circle_cloner_settings(box, modifier)

            # Common settings for all cloners
            draw_common_cloner_settings(box, modifier, context)

# Регистрация свойств для кастомных групп и состояний UI
def register_cloner_properties():
    # Keep the property for backwards compatibility, but make it True by default
    # and hide it from the UI
    bpy.types.Scene.custom_groups = bpy.props.BoolProperty(
        name="Use Custom Groups",
        description="Create cloners in custom node groups (enabled by default)",
        default=True,
        options={'HIDDEN'}  # Hide from UI
    )

    # Add an expanded state collection to track UI state
    bpy.types.Scene.cloner_expanded_states = {}

    # Add property to store selected effector for each cloner
    bpy.types.Scene.effector_to_link = StringProperty(
        name="Effector to Link",
        description="Selected effector to link to the cloner",
        default=""
    )

    # Add property to track the currently selected cloner in chain
    bpy.types.Scene.active_cloner_in_chain = StringProperty(
        name="Active Cloner in Chain",
        description="Currently active cloner in the cloner chain",
        default=""
    )

    # Add property to toggle showing cloner chain
    bpy.types.Scene.show_cloner_chain = BoolProperty(
        name="Show Cloner Chain",
        description="Show the full chain of cloners",
        default=True
    )

    # Add property for source type selection (Object/Collection)
    bpy.types.Scene.source_type_for_cloner = EnumProperty(
        name="Clone Source",
        description="What to clone: object or collection",
        items=[
            ('OBJECT', "Object", "Clone selected object"),
            ('COLLECTION', "Collection", "Clone selected collection")
        ],
        default='OBJECT',
        update=update_source_type
    )

    # Add property for collection selection
    bpy.types.Scene.collection_to_clone = StringProperty(
        name="Collection to Clone",
        description="The collection to be cloned"
    )

    # Add property to track last cloned collection
    bpy.types.Scene.last_cloned_collection = StringProperty(
        name="Last Cloned Collection",
        description="The last collection that was cloned",
        default=""
    )

# Функции регистрации и отмены регистрации
def register():
    bpy.utils.register_class(CLONERS_PT_Main)
    register_cloner_properties()

def unregister():
    bpy.utils.unregister_class(CLONERS_PT_Main)

    # Удаление свойств при отмене регистрации
    if hasattr(bpy.types.Scene, "custom_groups"):
        del bpy.types.Scene.custom_groups
    if hasattr(bpy.types.Scene, "cloner_expanded_states"):
        del bpy.types.Scene.cloner_expanded_states
    if hasattr(bpy.types.Scene, "effector_to_link"):
        del bpy.types.Scene.effector_to_link
    if hasattr(bpy.types.Scene, "active_cloner_in_chain"):
        del bpy.types.Scene.active_cloner_in_chain
    if hasattr(bpy.types.Scene, "show_cloner_chain"):
        del bpy.types.Scene.show_cloner_chain
    if hasattr(bpy.types.Scene, "source_type_for_cloner"):
        del bpy.types.Scene.source_type_for_cloner
    if hasattr(bpy.types.Scene, "collection_to_clone"):
        del bpy.types.Scene.collection_to_clone
    if hasattr(bpy.types.Scene, "last_cloned_collection"):
        del bpy.types.Scene.last_cloned_collection
