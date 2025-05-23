import bpy
from ...core.utils.node_utils import find_socket_by_name
from ...core.utils.config_utils import apply_cloner_config, load_config

def setup_grid_cloner_params(modifier):
    """Устанавливает параметры для Grid клонера"""
    # Пытаемся применить конфигурацию из JSON файла
    if apply_cloner_config(modifier, "GRID"):
        print("Applied GRID cloner config from JSON file")
        return

    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default GRID cloner parameters")

    # Найдем и установим параметры для grid клонера
    count_x_id = find_socket_by_name(modifier, "Count X")
    count_y_id = find_socket_by_name(modifier, "Count Y")
    count_z_id = find_socket_by_name(modifier, "Count Z")
    spacing_id = find_socket_by_name(modifier, "Spacing")

    if count_x_id and count_y_id and count_z_id and spacing_id:
        modifier[count_x_id] = 3
        modifier[count_y_id] = 3
        modifier[count_z_id] = 1

        # Если есть информация об оригинальном объекте, учитываем его размеры
        if "original_object" in modifier and modifier["original_object"] in bpy.data.objects:
            orig_obj = bpy.data.objects[modifier["original_object"]]
            max_dim = max(orig_obj.dimensions)
            spacing = max(max_dim * 1.5, 2.0)

            # Используем значения напрямую без множителей
            modifier[spacing_id] = (spacing, spacing, spacing)
        else:
            # Стандартные значения без множителей
            modifier[spacing_id] = (3.0, 3.0, 3.0)

def setup_linear_cloner_params(modifier):
    """Устанавливает параметры для Linear клонера"""
    # Пытаемся применить конфигурацию из JSON файла
    if apply_cloner_config(modifier, "LINEAR"):
        print("Applied LINEAR cloner config from JSON file")
        return

    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default LINEAR cloner parameters")

    # Найдем и установим параметры для linear клонера
    count_id = find_socket_by_name(modifier, "Count")
    offset_id = find_socket_by_name(modifier, "Offset")

    if count_id and offset_id:
        modifier[count_id] = 5

        # Проверяем, является ли это стековым клонером
        is_stacked_cloner = modifier.get("is_stacked_cloner", False)

        # Если есть информация об оригинальном объекте, учитываем его размеры
        if "original_object" in modifier and modifier["original_object"] in bpy.data.objects:
            orig_obj = bpy.data.objects[modifier["original_object"]]
            max_dim = max(orig_obj.dimensions)
            offset = max(max_dim * 2.0, 3.0)

            # Используем значения напрямую без множителей
            modifier[offset_id] = (offset, 0.0, 0.0)
            print(f"LINEAR: устанавливаем offset {(offset, 0.0, 0.0)}")
        else:
            # Стандартные значения без множителей
            modifier[offset_id] = (3.0, 0.0, 0.0)
            print(f"LINEAR: устанавливаем стандартный offset {(3.0, 0.0, 0.0)}")

        # Устанавливаем Use Effector в True для стекового клонера
        if is_stacked_cloner:
            use_effector_id = find_socket_by_name(modifier, "Use Effector")
            if use_effector_id:
                modifier[use_effector_id] = True

def setup_circle_cloner_params(modifier):
    """Устанавливает параметры для Circle клонера"""
    # Пытаемся применить конфигурацию из JSON файла
    if apply_cloner_config(modifier, "CIRCLE"):
        print("Applied CIRCLE cloner config from JSON file")
        return

    # Если не удалось применить конфигурацию, используем стандартные значения
    print("Using default CIRCLE cloner parameters")

    # Найдем и установим параметры для circle клонера
    count_id = find_socket_by_name(modifier, "Count")
    if not count_id:
        count_id = find_socket_by_name(modifier, "Count X")

    radius_id = find_socket_by_name(modifier, "Radius")
    if not radius_id:
        radius_id = find_socket_by_name(modifier, "Spacing")

    # Переменная is_stacked_cloner больше не используется, так как мы применяем значения напрямую

    if count_id and radius_id:
        modifier[count_id] = 8

        # Если есть информация об оригинальном объекте, учитываем его размеры
        if "original_object" in modifier and modifier["original_object"] in bpy.data.objects:
            orig_obj = bpy.data.objects[modifier["original_object"]]
            max_dim = max(orig_obj.dimensions)
            radius = max(max_dim * 3.0, 5.0)

            # Используем значения напрямую без множителей
            if isinstance(modifier[radius_id], tuple):
                modifier[radius_id] = (radius, radius, radius)
                print(f"CIRCLE: устанавливаем radius (tuple) {(radius, radius, radius)}")
            else:
                modifier[radius_id] = radius
                print(f"CIRCLE: устанавливаем radius {radius}")
        else:
            # Стандартные значения без множителей
            if isinstance(modifier[radius_id], tuple):
                modifier[radius_id] = (4.0, 4.0, 4.0)
                print(f"CIRCLE: устанавливаем стандартный radius (tuple) {(4.0, 4.0, 4.0)}")
            else:
                modifier[radius_id] = 4.0
                print(f"CIRCLE: устанавливаем стандартный radius {4.0}")

        # Настраиваем параметр Height для 3D позиционирования
        height_id = find_socket_by_name(modifier, "Height")
        if height_id:
            print(f"CIRCLE: устанавливаем height {0.0}")
            modifier[height_id] = 0.0