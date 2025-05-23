import bpy
from ..common.ui_utils import display_socket_prop, find_socket_by_name, get_stacked_cloner_info

# Moved from cloner_settings_panel.py
def draw_collection_cloner_settings(layout, modifier, cloner_type):
    """Отображает настройки клонера коллекций"""
    col = layout.column(align=True)

    # Получаем информацию о стековом клонере
    is_stacked_cloner, stacked_type = get_stacked_cloner_info(modifier)

    # Для стековых клонеров сначала проверяем поле cloner_display_type
    if is_stacked_cloner:
        display_type = modifier.get("cloner_display_type", "")
        if display_type == "Linear":
            cloner_type = "LINEAR"
        elif display_type == "Grid":
            cloner_type = "GRID"
        elif display_type == "Circle":
            cloner_type = "CIRCLE"
        # Затем проверяем имя модификатора
        elif "Linear" in modifier.name:
            cloner_type = "LINEAR"
        elif "Circle" in modifier.name:
            cloner_type = "CIRCLE"
        elif "Grid" in modifier.name:
            cloner_type = "GRID"
        # Если имя не помогло, используем тип из метаданных
        elif stacked_type:
            cloner_type = stacked_type

    # Determine what header to display based on cloner type
    is_object_cloner = modifier.node_group.name.startswith("ObjectCloner_")
    is_collection_cloner = modifier.node_group.name.startswith("CollectionCloner_")

    # If neither a collection nor an ObjectCloner_, it's a standard object cloner
    is_standard_object_cloner = not (is_object_cloner or is_collection_cloner)

    if is_standard_object_cloner:
        cloner_label = "Object"
    else:
        cloner_label = "Object" if is_object_cloner else "Collection"

    # Для стековых клонеров добавляем индикатор в заголовок
    if is_stacked_cloner:
        # Заголовок с актуальным типом клонера
        # Дополнительно проверяем, что все совпадает
        title_prefix = {
            "LINEAR": "Linear",
            "GRID": "Grid",
            "CIRCLE": "Circle"
        }.get(cloner_type, cloner_type.title())
        col.label(text=f"{title_prefix} {cloner_label} Stacked Settings", icon='LINKED')
    else:
        col.label(text=f"{cloner_type.title()} {cloner_label} Settings")

    col.separator(factor=0.5)

    # Display settings based on cloner type
    if cloner_type == "GRID":
        # Grid-specific settings for collection cloner
        if is_stacked_cloner:
            # Для грид клонера нет специальной секции, но добавим заголовок для согласованности
            col.label(text="Grid Settings")
            display_socket_prop(col, modifier, "Count X")
            display_socket_prop(col, modifier, "Count Y")
            display_socket_prop(col, modifier, "Count Z")
            display_socket_prop(col, modifier, "Spacing")
        else:
            # Для обычных клонеров показываем все параметры + Center Grid
            display_socket_prop(col, modifier, "Count X")
            display_socket_prop(col, modifier, "Count Y")
            display_socket_prop(col, modifier, "Count Z")
            display_socket_prop(col, modifier, "Spacing")
            display_socket_prop(col, modifier, "Center Grid")
    elif cloner_type == "LINEAR":
        # Linear-specific settings for collection cloner - use Count and Offset
        # Для стековых клонеров тоже нужно обязательно показывать базовые параметры
        if is_stacked_cloner:
            # Отображаем CountOffset для стековых клонеров LINEAR вместо базовых настроек
            has_count_offset = modifier.node_group.get("has_count_offset", False)
            if has_count_offset:
                col.label(text="Count Offset")

                # Находим сокет Count и отображаем его
                count_id = find_socket_by_name(modifier, "Count")
                if not count_id:
                    # Запасной вариант: ищем Count Z
                    count_id = find_socket_by_name(modifier, "Count Z")

                if count_id:
                    col.prop(modifier, f'["{count_id}"]', text="Count")

                # Создаем поля для отображения компонентов Offset в столбец
                col.label(text="Offset:")

                # Находим сокет Offset для отображения компонентов
                offset_socket_id = find_socket_by_name(modifier, "Offset")
                if not offset_socket_id:
                    offset_socket_id = find_socket_by_name(modifier, "Spacing")

                if offset_socket_id:
                    # X компонент
                    row = col.row(align=True)
                    row.prop(modifier, f'["{offset_socket_id}"]', index=0, text="X")

                    # Y компонент
                    row = col.row(align=True)
                    row.prop(modifier, f'["{offset_socket_id}"]', index=1, text="Y")

                    # Z компонент
                    row = col.row(align=True)
                    row.prop(modifier, f'["{offset_socket_id}"]', index=2, text="Z")
            else:
                # Стандартное отображение базовых настроек, если не используется CountOffset
                col.label(text="Base Settings")

                # Для стековых LINEAR клонеров используем правильные имена Count и Offset
                count_id = find_socket_by_name(modifier, "Count")
                if count_id:
                    col.prop(modifier, f'["{count_id}"]', text="Count")
                else:
                    # Запасной вариант: ищем Count Z
                    count_z_id = find_socket_by_name(modifier, "Count Z")
                    if count_z_id:
                        col.prop(modifier, f'["{count_z_id}"]', text="Count")
                    else:
                        display_socket_prop(col, modifier, "Count")

                offset_id = find_socket_by_name(modifier, "Offset")
                if offset_id:
                    col.prop(modifier, f'["{offset_id}"]', text="Offset")
                else:
                    # Запасной вариант: ищем Spacing
                    spacing_id = find_socket_by_name(modifier, "Spacing")
                    if spacing_id:
                        col.prop(modifier, f'["{spacing_id}"]', text="Offset")
                    else:
                        display_socket_prop(col, modifier, "Offset")
        else:
            display_socket_prop(col, modifier, "Count")
            display_socket_prop(col, modifier, "Offset")
    elif cloner_type == "CIRCLE":
        # Circle-specific settings for collection/object cloner
        # Для стековых клонеров тоже нужно обязательно показывать базовые параметры
        if is_stacked_cloner:
            # Отображаем CountRadius для стековых клонеров CIRCLE вместо базовых настроек
            has_count_radius = modifier.node_group.get("has_count_radius", False)
            if has_count_radius:
                col.label(text="Count Radius")

                # Создаем поля для отображения Count и Radius в столбец
                count_socket_id = find_socket_by_name(modifier, "Count")
                if not count_socket_id:
                    count_socket_id = find_socket_by_name(modifier, "Count Z")

                radius_socket_id = find_socket_by_name(modifier, "Radius")
                if not radius_socket_id:
                    radius_socket_id = find_socket_by_name(modifier, "Spacing")

                if count_socket_id and radius_socket_id:
                    # Отображение Count и Radius в столбец
                    col.prop(modifier, f'["{count_socket_id}"]', text="Count")
                    col.prop(modifier, f'["{radius_socket_id}"]', text="Radius")

                # Отображаем Height сразу после CountRadius
                display_socket_prop(col, modifier, "Height")
            else:
                # Стандартное отображение базовых настроек, если не используется CountRadius
                col.label(text="Base Settings")

                # Для стековых CIRCLE клонеров используем правильные имена Count и Radius
                count_id = find_socket_by_name(modifier, "Count")
                if count_id:
                    col.prop(modifier, f'["{count_id}"]', text="Count")
                else:
                    # Запасной вариант: ищем Count Z
                    count_z_id = find_socket_by_name(modifier, "Count Z")
                    if count_z_id:
                        col.prop(modifier, f'["{count_z_id}"]', text="Count")
                    else:
                        count_found = display_socket_prop(col, modifier, "Count", text="Count")
                        if not count_found:
                            display_socket_prop(col, modifier, "Count X", text="Count")

                radius_id = find_socket_by_name(modifier, "Radius")
                if radius_id:
                    col.prop(modifier, f'["{radius_id}"]', text="Radius")
                else:
                    # Запасной вариант: ищем Spacing
                    spacing_id = find_socket_by_name(modifier, "Spacing")
                    if spacing_id:
                        col.prop(modifier, f'["{spacing_id}"]', text="Radius")
                    else:
                        radius_found = display_socket_prop(col, modifier, "Radius", text="Radius")
                        if not radius_found:
                            display_socket_prop(col, modifier, "Spacing", text="Radius")
        else:
            # Для обычных клонеров коллекций проверяем, есть ли параметры Count и Radius
            count_found = display_socket_prop(col, modifier, "Count")
            if not count_found:
                # Если Count не найден, пробуем Count X (для совместимости со старыми клонерами)
                display_socket_prop(col, modifier, "Count X", text="Count")

            radius_found = display_socket_prop(col, modifier, "Radius")
            if not radius_found:
                # Если Radius не найден, пробуем Spacing (для совместимости со старыми клонерами)
                display_socket_prop(col, modifier, "Spacing", text="Radius")

            display_socket_prop(col, modifier, "Height", text="Height")

# Moved from cloner_settings_panel.py
def draw_grid_cloner_settings(layout, modifier):
    """Отображает настройки для Grid клонера"""
    col = layout.column(align=True)
    display_socket_prop(col, modifier, "Count X")
    display_socket_prop(col, modifier, "Count Y")
    display_socket_prop(col, modifier, "Count Z")
    display_socket_prop(col, modifier, "Spacing")
    display_socket_prop(col, modifier, "Center Grid")

# Moved from cloner_settings_panel.py
def draw_linear_cloner_settings(layout, modifier):
    """Отображает настройки для Linear клонера"""
    col = layout.column(align=True)
    display_socket_prop(col, modifier, "Count")
    display_socket_prop(col, modifier, "Offset")

# Moved from cloner_settings_panel.py
def draw_circle_cloner_settings(layout, modifier):
    """Отображает настройки для Circle клонера"""
    col = layout.column(align=True)
    display_socket_prop(col, modifier, "Count")
    display_socket_prop(col, modifier, "Radius")
    display_socket_prop(col, modifier, "Height")

# Moved from cloner_settings_panel.py
def draw_common_cloner_settings(layout, modifier, context, is_chain_menu=False):
    """Отображает общие настройки для всех типов клонеров

    Args:
        layout: UI layout для отрисовки
        modifier: Модификатор клонера
        context: Контекст Blender
        is_chain_menu: Если True, ограничивает некоторые элементы UI для безопасной работы в цепочке клонеров
    """
    col = layout.column(align=True)

    # Группа трансформаций
    transform_box = layout.box()
    transform_box.label(text="Transform", icon='ORIENTATION_GLOBAL')
    transform_col = transform_box.column(align=True)
    display_socket_prop(transform_col, modifier, "Instance Rotation", text="Rotation")
    display_socket_prop(transform_col, modifier, "Instance Scale", text="Scale")

    # Для Circle клонера дополнительные параметры вращения экземпляров вдоль окружности
    if modifier.node_group and (
        modifier.node_group.name.startswith("CircleCloner") or
        "Circle_Cloner" in modifier.name or
        modifier.node_group.get("cloner_type") == "CIRCLE"
    ):
        display_socket_prop(transform_col, modifier, "Rotation Start", text="Start")
        display_socket_prop(transform_col, modifier, "Rotation End", text="End")

    # Группа позиционирования
    position_box = layout.box()
    position_box.label(text="Position", icon='EMPTY_AXIS')
    position_col = position_box.column(align=True)

    # Для Linear и Circle клонеров показываем градиент масштаба
    if modifier.node_group and (
        modifier.node_group.name.startswith("LinearCloner") or
        modifier.node_group.name.startswith("CircleCloner") or
        "Linear_Cloner" in modifier.name or
        "Circle_Cloner" in modifier.name or
        modifier.node_group.get("cloner_type") == "LINEAR" or
        modifier.node_group.get("cloner_type") == "CIRCLE"
    ):
        display_socket_prop(position_col, modifier, "Scale Start")
        display_socket_prop(position_col, modifier, "Scale End")
        position_col.separator()

    display_socket_prop(position_col, modifier, "Global Position", text="Global Position")
    display_socket_prop(position_col, modifier, "Global Rotation", text="Global Rotation")

    # Группа рандомизации
    random_box = layout.box()
    random_box.label(text="Random", icon='RNDCURVE')
    random_col = random_box.column(align=True)
    display_socket_prop(random_col, modifier, "Random Seed", text="Seed")
    display_socket_prop(random_col, modifier, "Random Position", text="Position")
    display_socket_prop(random_col, modifier, "Random Rotation", text="Rotation")
    display_socket_prop(random_col, modifier, "Random Scale", text="Scale")



    # Группа эффекторов
    effector_box = layout.box()
    effector_box.label(text="Effectors", icon='FORCE_FORCE')

    # Получаем информацию о стековом клонере
    is_stacked_cloner, _ = get_stacked_cloner_info(modifier)

    # Переключатель для использования эффекторов - только для не-стековых клонеров
    if not is_stacked_cloner:
        display_socket_prop(effector_box, modifier, "Use Effector", text="Enable Effectors")

    # Список подключенных эффекторов
    row = effector_box.row()

    # Получаем информацию о подключенных эффекторах
    if modifier.node_group and "linked_effectors" in modifier.node_group:
        linked_effectors = list(modifier.node_group["linked_effectors"])

        if linked_effectors:
            effector_box.label(text="Linked Effectors:")

            # Создаем список эффекторов
            for eff_name in linked_effectors:
                row = effector_box.row()
                # Используем split для выравнивания и добавления кнопки удаления справа
                split = row.split(factor=0.85)
                split.label(text=eff_name, icon='FORCE_FORCE')

                # Кнопка для отвязки эффектора
                unlink_op = split.operator("object.unlink_effector", text="", icon='X')
                unlink_op.effector_name = eff_name
                unlink_op.cloner_name = modifier.name

        # В меню цепочки клонеров не отображаем создание новых эффекторов
        # Это предотвратит проблемы с созданием эффекторов для неактивных объектов
        if is_chain_menu:
            # Показываем сообщение о том, что нужно создавать эффекторы через обычное меню
            effector_box.label(text="Use main panel to add/link effectors", icon='INFO')
        else:
            # Collect all effector modifiers
            obj = context.active_object
            available_effectors = []

            # Collect all NODE modifiers with "Effector" in their name
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group and "Effector" in mod.node_group.name:
                    # Skip effectors that are already linked
                    if mod.name in linked_effectors:
                        continue
                    available_effectors.append(mod.name)

            # Show linking option only if there are available effectors
            if available_effectors:
                effector_box.separator()
                effector_box.label(text="Link Effector:")

                # Create a row for the dropdown and button
                row = effector_box.row(align=True)

                # Use prop_search for selecting an effector
                row.prop_search(
                    context.scene,
                    "effector_to_link",
                    obj,
                    "modifiers",
                    text=""
                )

                # Add button to link the selected effector (if one is selected)
                if context.scene.effector_to_link and context.scene.effector_to_link in available_effectors:
                    op = row.operator("object.cloner_link_effector", text="Link", icon="LINKED")
                    op.cloner_name = modifier.name
                    op.effector_name = context.scene.effector_to_link
    else:
        effector_box.label(text="No effector support")

def force_select_object(context, obj_name):
    """
    Принудительно устанавливает объект активным и выделенным.
    Обновляет интерфейс после выбора.

    Args:
        context: Контекст Blender
        obj_name: Имя объекта для выбора

    Returns:
        bool: True если объект выбран успешно
    """
    if not obj_name or obj_name not in bpy.data.objects:
        print(f"[SELECT] Ошибка: объект '{obj_name}' не найден")
        return False

    try:
        # Очищаем текущее выделение
        bpy.ops.object.select_all(action='DESELECT')

        # Выбираем нужный объект
        obj = bpy.data.objects[obj_name]
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Обновляем view_layer
        context.view_layer.update()

        # Обновляем интерфейс
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        print(f"[SELECT] Объект '{obj_name}' успешно выбран и установлен активным")
        return True
    except Exception as e:
        print(f"[SELECT] Ошибка при выборе объекта '{obj_name}': {e}")
        import traceback
        traceback.print_exc()
        return False