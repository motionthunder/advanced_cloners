import bpy
from ..common.ui_utils import display_socket_prop, is_element_expanded

def draw_effector_ui(context, layout, obj, mod):
    """
    Отображает интерфейс для эффектора

    Перемещен из effector_panel.py
    """
    # Создаем бокс для каждого эффектора
    box = layout.box()
    row = box.row()

    # Иконка на основе типа эффектора
    icon = 'FORCE_FORCE'
    if mod.node_group.name.startswith("RandomEffector"):
        icon = 'RNDCURVE'
    elif mod.node_group.name.startswith("NoiseEffector"):
        icon = 'FORCE_TURBULENCE'

    # Получаем состояние раскрытия из нашей системы
    expanded = is_element_expanded(context, obj.name, mod.name, "effector_expanded_states")

    # Кнопка раскрытия/сворачивания (как у клонеров)
    op = row.operator("object.toggle_effector_expanded", text="", icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT', emboss=False)
    op.obj_name = obj.name
    op.modifier_name = mod.name

    # Название эффектора
    row.label(text=f"{mod.name}", icon=icon)

    # Кнопка видимости
    row.prop(mod, "show_viewport", text="", icon='HIDE_OFF' if mod.show_viewport else 'HIDE_ON', emboss=False)

    # Кнопки управления
    ctrl_row = row.row(align=True)

    # Кнопки перемещения вверх/вниз
    op = ctrl_row.operator("object.move_effector", text="", icon="TRIA_UP")
    op.modifier_name = mod.name
    op.direction = 'UP'

    op = ctrl_row.operator("object.move_effector", text="", icon="TRIA_DOWN")
    op.modifier_name = mod.name
    op.direction = 'DOWN'

    # Кнопка удаления
    op = ctrl_row.operator("object.delete_effector", text="", icon="X")
    op.modifier_name = mod.name

    # Если эффектор развернут, показываем его параметры
    if expanded and mod.node_group and hasattr(mod.node_group, 'interface'):
        draw_effector_expanded_ui(context, box, obj, mod)

def draw_effector_expanded_ui(context, box, obj, mod):
    """
    Отображает расширенный интерфейс для развернутого эффектора

    Перемещен из effector_panel.py
    """
    # --- Показываем связи с клонерами ---
    # Находим обычные клонеры, связанные с этим эффектором
    linked_cloners = []
    for cloner_mod in obj.modifiers:
        if cloner_mod.type == 'NODES' and cloner_mod.node_group and cloner_mod.node_group.get("linked_effectors") is not None:
            if mod.name in cloner_mod.node_group.get("linked_effectors", []):
                linked_cloners.append(cloner_mod)

    # Находим стековые клонеры, связанные с этим эффектором
    stacked_linked_cloners = []
    for cloner_mod in obj.modifiers:
        if (cloner_mod.type == 'NODES' and cloner_mod.node_group and
            (cloner_mod.get("is_stacked_cloner") or
             (cloner_mod.node_group and cloner_mod.node_group.get("is_stacked_cloner"))) and
            cloner_mod.node_group.get("linked_effectors") is not None):

            # Преобразуем значение linked_effectors в список Python
            linked_effectors = list(cloner_mod.node_group.get("linked_effectors", []))

            if mod.name in linked_effectors:
                stacked_linked_cloners.append(cloner_mod)

    # Информация о связанных клонерах
    if linked_cloners or stacked_linked_cloners:
        link_box = box.box()
        row = link_box.row()
        row.label(text="Linked to:", icon='LINKED')

        # Список обычных клонеров
        if linked_cloners:
            links_text = ", ".join([cloner.name for cloner in linked_cloners])
            row = link_box.row()
            row.label(text=f"Regular: {links_text}")

        # Список стековых клонеров
        if stacked_linked_cloners:
            links_text = ", ".join([cloner.name for cloner in stacked_linked_cloners])
            row = link_box.row()
            row.label(text=f"Stacked: {links_text}")

            # Убрали кнопку обновления стековых клонеров, так как они обновляются автоматически

    # Кнопка автопривязки
    if not linked_cloners and not stacked_linked_cloners:
        # Проверяем наличие клонеров, к которым можно привязаться
        cloner_mods = [m for m in obj.modifiers if m.type == 'NODES' and
                      m.node_group and (m.node_group.get("linked_effectors") is not None or
                                      m.node_group.get("is_stacked_cloner") or
                                      m.get("is_stacked_cloner"))]

        if cloner_mods:
            link_op = box.operator("object.auto_link_effector", text="Link to Cloners", icon='LINKED')
            link_op.effector_name = mod.name

    # Организуем параметры по категориям
    draw_effector_socket_parameters(box, mod)

def draw_effector_socket_parameters(layout, mod):
    """
    Отображает сокеты эффектора, организованные по категориям

    Перемещен из effector_panel.py
    """
    # Сначала собираем сокеты по категориям
    enable_strength = []
    transform = []
    field = []
    other = []

    for socket in mod.node_group.interface.items_tree:
        if socket.item_type != 'SOCKET' or socket.in_out != 'INPUT' or socket.name == "Geometry":
            continue

        name = socket.name
        # Распределяем параметры по категориям
        if name in ["Enable", "Strength"]:
            enable_strength.append(socket.name)
        elif name in ["Position", "Rotation", "Scale", "Uniform Scale"]:
            transform.append(socket.name)
        elif name in ["Field", "Use Field"]:
            field.append(socket.name)
        else:
            other.append(socket.name)



    # Отображаем параметры по категориям
    # 1. Включение/сила
    if enable_strength:
        effect_box = layout.box()
        effect_box.label(text="Effect:", icon='FORCE_FORCE')
        for socket_name in enable_strength:
            display_socket_prop(effect_box, mod, socket_name)

    # 2. Трансформации
    if transform:
        transform_box = layout.box()
        transform_box.label(text="Transform:", icon='ORIENTATION_GLOBAL')
        for socket_name in transform:
            display_socket_prop(transform_box, mod, socket_name)

    # 3. Поля
    if field:
        field_box = layout.box()
        field_box.label(text="Field:", icon='OUTLINER_OB_FORCE_FIELD')

        # Параметры полей
        for socket_name in field:
            display_socket_prop(field_box, mod, socket_name)

        # Проверяем, использует ли эффектор поле
        using_field = mod.get("Use Field", False)

        if using_field:
            # Кнопка отключения поля
            field_box.operator("object.effector_remove_field", text="Disconnect Field", icon='X').effector_name = mod.name
        else:
            # Кнопка подключения поля
            field_box.operator("object.effector_add_field", text="Connect Field", icon='ADD').effector_name = mod.name

    # 4. Другие параметры
    if other:
        other_box = layout.box()
        other_box.label(text="Other:", icon='PREFERENCES')
        for socket_name in other:
            display_socket_prop(other_box, mod, socket_name)