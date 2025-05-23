import bpy

def find_socket_by_name(modifier, socket_name):
    """Находит сокет в интерфейсе модификатора по имени"""
    if not modifier or not modifier.node_group:
        return None

    # Получаем информацию о стековом клонере
    is_stacked, cloner_type = get_stacked_cloner_info(modifier)

    # Полное соответствие по имени - всегда ищем сначала точное соответствие
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == socket_name:
            return socket.identifier

    # Для стековых клонеров LINEAR и CIRCLE мапинг имен
    # Важно! Порядок имеет значение, так как мы сначала проверяем точное соответствие выше
    if is_stacked:
        if cloner_type == "LINEAR":
            # Для LINEAR клонера: Count ↔ Count Z, Offset ↔ Spacing
            param_mapping = {
                "Count": "Count Z",
                "Count Z": "Count",
                "Offset": "Spacing",
                "Spacing": "Offset"
            }

            if socket_name in param_mapping:
                mapped_name = param_mapping[socket_name]
                for socket in modifier.node_group.interface.items_tree:
                    if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == mapped_name:
                        return socket.identifier

        elif cloner_type == "CIRCLE":
            # Для CIRCLE клонера: Count ↔ Count Z, Radius ↔ Spacing
            param_mapping = {
                "Count": "Count Z",
                "Count Z": "Count",
                "Radius": "Spacing",
                "Spacing": "Radius"
            }

            if socket_name in param_mapping:
                mapped_name = param_mapping[socket_name]
                for socket in modifier.node_group.interface.items_tree:
                    if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == mapped_name:
                        return socket.identifier

    # Для стековых клонеров дополнительно ищем по частичному совпадению
    if socket_name in ["Count", "Radius", "Offset", "Height", "Center Grid"]:
        if is_stacked:
            for socket in modifier.node_group.interface.items_tree:
                if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
                    # Частичное соответствие для основных параметров клонеров
                    if socket_name == "Count" and socket.name in ["Count", "Count X", "Count Z"]:
                        return socket.identifier
                    elif socket_name == "Radius" and socket.name in ["Radius", "Spacing"]:
                        return socket.identifier
                    elif socket_name == "Offset" and socket.name in ["Offset", "Spacing"]:
                        return socket.identifier
                    elif socket_name == "Height" and socket.name == "Height":
                        return socket.identifier
                    elif socket_name == "Center Grid" and socket.name == "Center Grid":
                        return socket.identifier

    # Прямой поиск по socket_ID для стековых клонеров
    # Это необходимо, если имена не совпадают с идентификаторами
    socket_id_map = {
        "Count": ["Socket_0", "Socket_1", "Socket_2"], # Частые сокеты для Count
        "Count X": ["Socket_0"],
        "Count Y": ["Socket_1"],
        "Count Z": ["Socket_2"],
        "Spacing": ["Socket_3"],
        "Radius": ["Socket_3"],
        "Offset": ["Socket_3"],
        "Height": ["Socket_4"],
        "Instance Rotation": ["Socket_5"],
        "Instance Scale": ["Socket_6"],
        "Global Position": ["Socket_7"],
        "Global Rotation": ["Socket_8"],
        "Random Seed": ["Socket_9"],
        "Random Position": ["Socket_10"],
        "Random Rotation": ["Socket_11"],
        "Random Scale": ["Socket_12"],
        "Use Effector": ["Socket_13"],
        "Center Grid": ["Socket_14"],
        "Scale Start": ["Socket_15"],
        "Scale End": ["Socket_16"],
        "Rotation Start": ["Socket_17"],
        "Rotation End": ["Socket_18"],
        "Realize Instances": ["Socket_19", "Socket_20"], # Новый параметр для предотвращения проблем с рекурсией
    }

    if is_stacked and socket_name in socket_id_map:
        # Проверяем, существует ли для этого модификатора сокет с таким идентификатором
        socket_ids = socket_id_map[socket_name]
        if isinstance(socket_ids, str):  # Если один идентификатор
            if socket_ids in modifier:
                return socket_ids
        else:  # Если несколько идентификаторов
            for socket_id in socket_ids:
                if socket_id in modifier:
                    return socket_id

    return None

def display_socket_prop(layout, modifier, socket_name, text=None, **kwargs):
    """Безопасно отображает свойство сокета модификатора"""
    socket_id = find_socket_by_name(modifier, socket_name)
    if socket_id:
        if text is None:
            text = socket_name

        layout.prop(modifier, f'["{socket_id}"]', text=text, **kwargs)
        return True
    return False

def get_stacked_cloner_info(modifier):
    """Получает информацию о стековом клонере - тип и флаги"""
    is_stacked = False
    cloner_type = ""

    # Сначала проверяем поле cloner_display_type
    display_type = modifier.get("cloner_display_type", "")
    if display_type:
        is_stacked = True
        if display_type == "Linear":
            cloner_type = "LINEAR"
        elif display_type == "Grid":
            cloner_type = "GRID"
        elif display_type == "Circle":
            cloner_type = "CIRCLE"

    # Затем проверяем имя модификатора, если ещё не определили тип
    if not cloner_type and modifier.name:
        if "Linear_Cloner" in modifier.name:
            is_stacked = True
            cloner_type = "LINEAR"
        elif "Grid_Cloner" in modifier.name:
            is_stacked = True
            cloner_type = "GRID"
        elif "Circle_Cloner" in modifier.name:
            is_stacked = True
            cloner_type = "CIRCLE"

    # Проверяем флаг стекового клонера в модификаторе
    if not is_stacked and modifier.get("is_stacked_cloner", False):
        is_stacked = True
        if not cloner_type:  # Только если еще не определили тип
            cloner_type = modifier.get("cloner_type", "")

    # Проверяем флаг стекового клонера в ноде
    if not is_stacked and modifier.node_group and modifier.node_group.get("is_stacked_cloner", False):
        is_stacked = True
        if not cloner_type:  # Только если еще не определили тип
            cloner_type = modifier.node_group.get("cloner_type", "")

    # Если тип не определен, пытаемся определить по префиксу нод-группы
    if is_stacked and not cloner_type and modifier.node_group:
        node_group_name = modifier.node_group.name
        if "Grid" in node_group_name:
            cloner_type = "GRID"
        elif "Linear" in node_group_name:
            cloner_type = "LINEAR"
        elif "Circle" in node_group_name:
            cloner_type = "CIRCLE"

    return is_stacked, cloner_type

# Функции для состояний раскрытия (expanded states)
def get_expanded_states_key(obj_name, modifier_name):
    """Создает ключ для хранения состояния раскрытия модификатора"""
    # Ограничиваем длину ключа до 60 символов (63 - максимум для IDProperty)
    # Используем хеш для длинных имен
    if len(obj_name) + len(modifier_name) + 1 > 60:
        # Используем первые 30 символов имени объекта и хеш для остальной части
        obj_hash = str(hash(obj_name) % 10000).zfill(4)
        mod_hash = str(hash(modifier_name) % 10000).zfill(4)
        return f"{obj_name[:25]}_{obj_hash}_{mod_hash}"
    else:
        return f"{obj_name}_{modifier_name}"

def is_element_expanded(context, obj_name, modifier_name, state_property="cloner_expanded_states"):
    """Проверяет, развернут ли элемент в UI"""
    key = get_expanded_states_key(obj_name, modifier_name)
    expanded_states = context.scene.get(state_property, {})
    return expanded_states.get(key, False)

def set_element_expanded(context, obj_name, modifier_name, state, state_property="cloner_expanded_states"):
    """Устанавливает состояние раскрытия элемента в UI"""
    key = get_expanded_states_key(obj_name, modifier_name)
    expanded_states = context.scene.get(state_property, {})
    expanded_states[key] = state
    context.scene[state_property] = expanded_states

    # Принудительное обновление UI
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

# Обратная совместимость с операторами
def is_cloner_expanded(obj_name, modifier_name):
    """Обратная совместимость для cloner - делегирует к is_element_expanded"""
    return is_element_expanded(bpy.context, obj_name, modifier_name, "cloner_expanded_states")

def set_cloner_expanded(obj_name, modifier_name, state):
    """Обратная совместимость для cloner - делегирует к set_element_expanded"""
    set_element_expanded(bpy.context, obj_name, modifier_name, state, "cloner_expanded_states")

def is_effector_expanded(obj_name, modifier_name):
    """Обратная совместимость для effector - делегирует к is_element_expanded"""
    return is_element_expanded(bpy.context, obj_name, modifier_name, "effector_expanded_states")

def set_effector_expanded(obj_name, modifier_name, state):
    """Обратная совместимость для effector - делегирует к set_element_expanded"""
    set_element_expanded(bpy.context, obj_name, modifier_name, state, "effector_expanded_states")

def is_field_expanded(obj_name, modifier_name):
    """Обратная совместимость для field - делегирует к is_element_expanded"""
    return is_element_expanded(bpy.context, obj_name, modifier_name, "field_expanded_states")

def set_field_expanded(obj_name, modifier_name, state):
    """Обратная совместимость для field - делегирует к set_element_expanded"""
    set_element_expanded(bpy.context, obj_name, modifier_name, state, "field_expanded_states")

# Регистрация свойств для хранения состояний раскрытия
def register_expanded_states_property(property_name="cloner_expanded_states"):
    """Регистрирует свойство для хранения состояний раскрытия"""
    if not hasattr(bpy.types.Scene, property_name):
        setattr(bpy.types.Scene, property_name, {})

def unregister_expanded_states_property(property_name="cloner_expanded_states"):
    """Удаляет свойство для хранения состояний раскрытия"""
    if hasattr(bpy.types.Scene, property_name):
        delattr(bpy.types.Scene, property_name)
