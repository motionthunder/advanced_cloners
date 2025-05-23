import bpy
from ...core.common.constants import CLONER_MOD_NAMES
from ...core.utils.node_utils import find_socket_by_name
from ...core.utils.cloner_effector_utils import update_cloner_with_effectors
from ...core.factories.component_factory import ComponentFactory
from ...models.cloners.grid_cloner import GridCloner
from ...models.cloners.linear_cloner import LinearCloner
from ...models.cloners.circle_cloner import CircleCloner

from .params_utils import (
    setup_grid_cloner_params,
    setup_linear_cloner_params,
    setup_circle_cloner_params
)

def create_stacked_cloner(context, cloner_type, orig_obj):
    """
    Создает стековый клонер на том же объекте с улучшенной обработкой параметров.
    """
    print(f"=== СОЗДАНИЕ УЛУЧШЕННОГО СТЕКОВОГО КЛОНЕРА ===")
    print(f"Тип: {cloner_type}, Объект: {orig_obj.name}")

    # Получаем базовое имя модификатора
    base_mod_name = CLONER_MOD_NAMES[cloner_type]

    # Целевой объект такой же как и исходный
    target_obj = orig_obj

    # Соответствие типов клонеров классам
    CLONER_CLASSES = {
        "GRID": GridCloner,
        "LINEAR": LinearCloner,
        "CIRCLE": CircleCloner,
    }

    # Проверяем тип клонера
    if cloner_type not in CLONER_CLASSES:
        print(f"Unknown cloner type: {cloner_type}")
        return None, False

    # Создаем уникальное имя для модификатора, сохраняя тип в имени
    # Это важно для корректного определения типа в UI
    modifier_name = f"{base_mod_name}_Cloner"
    counter = 1
    while modifier_name in target_obj.modifiers:
        modifier_name = f"{base_mod_name}_Cloner_{counter:03d}"
        counter += 1

    print(f"Имя модификатора: {modifier_name}")

    # Получаем класс клонера
    cloner_class = CLONER_CLASSES[cloner_type]

    try:
        # Создаем ОТДЕЛЬНУЮ ГЕО НОД-ГРУППУ для стекового клонера
        # Здесь критическое отличие: нам нужна нод-группа старого типа с Geometry входом вместо Object
        # Создаем специальную нод-группу с указанием типа клонера в имени
        type_name = {
            "GRID": "Grid",
            "LINEAR": "Linear",
            "CIRCLE": "Circle"
        }.get(cloner_type, base_mod_name)

        node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"{type_name}_Stack_{orig_obj.name}")
        print(f"Создана нод-группа: {node_group.name}")

        # --- ПРОСТАЯ СТРУКТУРА ДЛЯ ОБЪЕКТНОГО СТЕКОВОГО КЛОНЕРА ---
        # Выход геометрии
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        # Вход геометрии - ключевое отличие от обычного клонера
        node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')

        # Добавляем параметр для включения/выключения "реализации" инстансов
        realize_instances_socket = node_group.interface.new_socket(
            name="Realize Instances",
            in_out='INPUT',
            socket_type='NodeSocketBool'
        )
        # Устанавливаем значение по умолчанию в соответствии с настройкой use_anti_recursion
        realize_instances_socket.default_value = context.scene.use_anti_recursion
        realize_instances_socket.description = "Enable to prevent recursion depth issues when creating chains of cloners"

        print("Добавлены входной и выходной сокеты для геометрии")

        # Копируем основные сокеты из класса клонера
        if cloner_type == "GRID":
            count_x_input = node_group.interface.new_socket(name="Count X", in_out='INPUT', socket_type='NodeSocketInt')
            count_x_input.default_value = 3

            count_y_input = node_group.interface.new_socket(name="Count Y", in_out='INPUT', socket_type='NodeSocketInt')
            count_y_input.default_value = 3

            count_z_input = node_group.interface.new_socket(name="Count Z", in_out='INPUT', socket_type='NodeSocketInt')
            count_z_input.default_value = 1

            spacing_input = node_group.interface.new_socket(name="Spacing", in_out='INPUT', socket_type='NodeSocketVector')
            spacing_input.default_value = (1.0, 1.0, 1.0)
            print("Добавлены параметры Grid клонера")

        elif cloner_type == "LINEAR":
            count_input = node_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
            count_input.default_value = 5

            offset_input = node_group.interface.new_socket(name="Offset", in_out='INPUT', socket_type='NodeSocketVector')
            offset_input.default_value = (1.0, 0.0, 0.0)
            print("Добавлены параметры Linear клонера")

        elif cloner_type == "CIRCLE":
            count_input = node_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
            count_input.default_value = 8

            radius_input = node_group.interface.new_socket(name="Radius", in_out='INPUT', socket_type='NodeSocketFloat')
            radius_input.default_value = 5.0
            print("Добавлены параметры Circle клонера")

        # Добавляем общие параметры
        global_pos_input = node_group.interface.new_socket(name="Global Position", in_out='INPUT', socket_type='NodeSocketVector')
        global_pos_input.default_value = (0.0, 0.0, 0.0)

        global_rot_input = node_group.interface.new_socket(name="Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        global_rot_input.default_value = (0.0, 0.0, 0.0)

        rotation_input = node_group.interface.new_socket(name="Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_input.default_value = (0.0, 0.0, 0.0)
        rotation_input.subtype = 'EULER'

        scale_input = node_group.interface.new_socket(name="Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')
        scale_input.default_value = (1.0, 1.0, 1.0)

        random_seed_input = node_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        random_seed_input.default_value = 0

        random_pos_input = node_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_pos_input.default_value = (0.0, 0.0, 0.0)

        random_rot_input = node_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rot_input.default_value = (0.0, 0.0, 0.0)

        random_scale_input = node_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0

        center_grid_input = node_group.interface.new_socket(name="Center Grid", in_out='INPUT', socket_type='NodeSocketBool')
        center_grid_input.default_value = False

        # Добавляем сокет для эффекторов и устанавливаем его в True для LINEAR клонера
        use_effector_socket = node_group.interface.new_socket(name="Use Effector", in_out='INPUT', socket_type='NodeSocketBool')
        use_effector_socket.default_value = True
        print("Добавлены общие параметры")

        # Построение базовой структуры узлов
        nodes = node_group.nodes
        links = node_group.links

        # Группы ввода/вывода
        group_in = nodes.new('NodeGroupInput')
        group_out = nodes.new('NodeGroupOutput')

        # ДОПОЛНИТЕЛЬНАЯ ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        print(f"=== АНАЛИЗ СОКЕТОВ ГРУППЫ ===")
        print(f"Интерфейс группы items_tree:")
        for i, item in enumerate(node_group.interface.items_tree):
            print(f"  [{i}] Имя: {item.name}, Тип: {item.socket_type}, Направление: {item.in_out}")

        print(f"Доступные выходы group_in:")
        for i, output_name in enumerate(group_in.outputs.keys()):
            print(f"  [{i}] {output_name}")

        if cloner_type == "GRID":
            # Создаем узлы для сетки точек
            # --- НОВАЯ ЛОГИКА ГРИД КЛОНЕРА, взятая из нестековой версии ---

            # --- Spacing Multiplier (для правильного масштабирования) ---
            spacing_multiplier = nodes.new('ShaderNodeVectorMath')
            spacing_multiplier.operation = 'MULTIPLY'
            # Используем множитель 1.0 для применения значений напрямую
            spacing_multiplier.inputs[1].default_value = (1.0, 1.0, 1.0)
            links.new(group_in.outputs['Spacing'], spacing_multiplier.inputs[0])

            # Разделяем умноженные значения отступов по компонентам
            separate_xyz_spacing = nodes.new('ShaderNodeSeparateXYZ')
            links.new(spacing_multiplier.outputs['Vector'], separate_xyz_spacing.inputs['Vector'])

            # --- Point Generation Logic ---
            # Шаг 1: Создаем линию точек по оси X с правильным отступом
            line_x = nodes.new('GeometryNodeMeshLine')
            line_x.name = "Line X Points"
            line_x.mode = 'OFFSET'  # Режим OFFSET для постоянного отступа
            line_x.count_mode = 'TOTAL'
            links.new(group_in.outputs['Count X'], line_x.inputs['Count'])

            # Создаем вектор отступа для оси X (Spacing X, 0, 0)
            combine_x_offset = nodes.new('ShaderNodeCombineXYZ')
            links.new(separate_xyz_spacing.outputs['X'], combine_x_offset.inputs['X'])
            combine_x_offset.inputs['Y'].default_value = 0.0
            combine_x_offset.inputs['Z'].default_value = 0.0
            links.new(combine_x_offset.outputs['Vector'], line_x.inputs['Offset'])

            # Шаг 2: Создаем линию точек по оси Y с правильным отступом
            line_y = nodes.new('GeometryNodeMeshLine')
            line_y.name = "Line Y Points"
            line_y.mode = 'OFFSET'
            line_y.count_mode = 'TOTAL'
            links.new(group_in.outputs['Count Y'], line_y.inputs['Count'])

            # Создаем вектор отступа для оси Y (0, Spacing Y, 0)
            combine_y_offset = nodes.new('ShaderNodeCombineXYZ')
            combine_y_offset.inputs['X'].default_value = 0.0
            links.new(separate_xyz_spacing.outputs['Y'], combine_y_offset.inputs['Y'])
            combine_y_offset.inputs['Z'].default_value = 0.0
            links.new(combine_y_offset.outputs['Vector'], line_y.inputs['Offset'])

            # Шаг 3: Инстансируем line_x вдоль line_y для создания 2D сетки
            instance_x_on_y = nodes.new('GeometryNodeInstanceOnPoints')
            instance_x_on_y.name = "Instance X on Y"

            # Используем mesh_to_points для конвертации линий в точки
            mesh_to_points_y = nodes.new('GeometryNodeMeshToPoints')
            links.new(line_y.outputs['Mesh'], mesh_to_points_y.inputs['Mesh'])
            links.new(mesh_to_points_y.outputs['Points'], instance_x_on_y.inputs['Points'])
            links.new(line_x.outputs['Mesh'], instance_x_on_y.inputs['Instance'])

            # Реализуем 2D сетку
            realize_2d_grid = nodes.new('GeometryNodeRealizeInstances')
            realize_2d_grid.name = "Realize 2D Grid"
            links.new(instance_x_on_y.outputs['Instances'], realize_2d_grid.inputs['Geometry'])

            # Шаг 4: Создаем линию по оси Z с правильным отступом
            line_z = nodes.new('GeometryNodeMeshLine')
            line_z.name = "Line Z Points"
            line_z.mode = 'OFFSET'
            line_z.count_mode = 'TOTAL'
            links.new(group_in.outputs['Count Z'], line_z.inputs['Count'])

            # Создаем вектор отступа для оси Z (0, 0, Spacing Z)
            combine_z_offset = nodes.new('ShaderNodeCombineXYZ')
            combine_z_offset.inputs['X'].default_value = 0.0
            combine_z_offset.inputs['Y'].default_value = 0.0
            links.new(separate_xyz_spacing.outputs['Z'], combine_z_offset.inputs['Z'])
            links.new(combine_z_offset.outputs['Vector'], line_z.inputs['Offset'])

            # Шаг 5: Инстансируем 2D сетку вдоль линии Z для создания 3D сетки
            instance_2d_on_z = nodes.new('GeometryNodeInstanceOnPoints')
            instance_2d_on_z.name = "Instance 2D on Z"
            mesh_to_points_z = nodes.new('GeometryNodeMeshToPoints')
            links.new(line_z.outputs['Mesh'], mesh_to_points_z.inputs['Mesh'])
            links.new(mesh_to_points_z.outputs['Points'], instance_2d_on_z.inputs['Points'])
            links.new(realize_2d_grid.outputs['Geometry'], instance_2d_on_z.inputs['Instance'])

            # Реализуем 3D сетку
            realize_3d_grid = nodes.new('GeometryNodeRealizeInstances')
            realize_3d_grid.name = "Realize 3D Grid"
            links.new(instance_2d_on_z.outputs['Instances'], realize_3d_grid.inputs['Geometry'])

            # Переключатель между 2D сеткой (если Count Z = 1) и 3D сеткой (если Count Z > 1)
            compare_z_count = nodes.new('FunctionNodeCompare')
            compare_z_count.data_type = 'INT'
            compare_z_count.operation = 'GREATER_THAN'
            compare_z_count.inputs[3].default_value = 1  # Сравниваем с 1
            links.new(group_in.outputs['Count Z'], compare_z_count.inputs[2])  # Input A

            switch_points = nodes.new('GeometryNodeSwitch')
            switch_points.name = "Switch 2D/3D Points"
            switch_points.input_type = 'GEOMETRY'
            links.new(compare_z_count.outputs['Result'], switch_points.inputs['Switch'])
            links.new(realize_2d_grid.outputs['Geometry'], switch_points.inputs[False])  # 2D если Count Z = 1
            links.new(realize_3d_grid.outputs['Geometry'], switch_points.inputs[True])  # 3D если Count Z > 1

            # --- Centering Logic ---
            # Рассчитываем смещение для центрирования сетки на основе общего размера

            # Рассчитываем размер X: (Count X - 1) * Spacing X
            count_x_minus_one = nodes.new('ShaderNodeMath')
            count_x_minus_one.operation = 'SUBTRACT'
            count_x_minus_one.inputs[1].default_value = 1.0
            links.new(group_in.outputs['Count X'], count_x_minus_one.inputs[0])

            total_size_x = nodes.new('ShaderNodeMath')
            total_size_x.operation = 'MULTIPLY'
            links.new(count_x_minus_one.outputs['Value'], total_size_x.inputs[0])
            links.new(separate_xyz_spacing.outputs['X'], total_size_x.inputs[1])

            # Рассчитываем размер Y: (Count Y - 1) * Spacing Y
            count_y_minus_one = nodes.new('ShaderNodeMath')
            count_y_minus_one.operation = 'SUBTRACT'
            count_y_minus_one.inputs[1].default_value = 1.0
            links.new(group_in.outputs['Count Y'], count_y_minus_one.inputs[0])

            total_size_y = nodes.new('ShaderNodeMath')
            total_size_y.operation = 'MULTIPLY'
            links.new(count_y_minus_one.outputs['Value'], total_size_y.inputs[0])
            links.new(separate_xyz_spacing.outputs['Y'], total_size_y.inputs[1])

            # Рассчитываем размер Z: (Count Z - 1) * Spacing Z
            count_z_minus_one = nodes.new('ShaderNodeMath')
            count_z_minus_one.operation = 'SUBTRACT'
            count_z_minus_one.inputs[1].default_value = 1.0
            links.new(group_in.outputs['Count Z'], count_z_minus_one.inputs[0])

            total_size_z = nodes.new('ShaderNodeMath')
            total_size_z.operation = 'MULTIPLY'
            links.new(count_z_minus_one.outputs['Value'], total_size_z.inputs[0])
            links.new(separate_xyz_spacing.outputs['Z'], total_size_z.inputs[1])

            # Рассчитываем смещение центра (половина общего размера)
            center_offset_x = nodes.new('ShaderNodeMath')
            center_offset_x.operation = 'DIVIDE'
            center_offset_x.inputs[1].default_value = 2.0
            links.new(total_size_x.outputs['Value'], center_offset_x.inputs[0])

            center_offset_y = nodes.new('ShaderNodeMath')
            center_offset_y.operation = 'DIVIDE'
            center_offset_y.inputs[1].default_value = 2.0
            links.new(total_size_y.outputs['Value'], center_offset_y.inputs[0])

            center_offset_z = nodes.new('ShaderNodeMath')
            center_offset_z.operation = 'DIVIDE'
            center_offset_z.inputs[1].default_value = 2.0
            links.new(total_size_z.outputs['Value'], center_offset_z.inputs[0])

            # Соединяем смещение центра
            center_offset = nodes.new('ShaderNodeCombineXYZ')
            links.new(center_offset_x.outputs['Value'], center_offset.inputs['X'])
            links.new(center_offset_y.outputs['Value'], center_offset.inputs['Y'])
            links.new(center_offset_z.outputs['Value'], center_offset.inputs['Z'])

            # Негатируем для правильного направления смещения
            negate_center = nodes.new('ShaderNodeVectorMath')
            negate_center.operation = 'MULTIPLY'
            negate_center.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(center_offset.outputs['Vector'], negate_center.inputs[0])

            # Создаем нулевой вектор для опции без центрирования
            zero_vector = nodes.new('ShaderNodeCombineXYZ')
            zero_vector.inputs[0].default_value = 0.0
            zero_vector.inputs[1].default_value = 0.0
            zero_vector.inputs[2].default_value = 0.0

            # Переключаем между центрированием и без центрирования на основе опции Center Grid
            center_switch = nodes.new('GeometryNodeSwitch')
            center_switch.input_type = 'VECTOR'
            links.new(group_in.outputs['Center Grid'], center_switch.inputs[0])  # Switch
            links.new(zero_vector.outputs['Vector'], center_switch.inputs[False])  # Без центрирования
            links.new(negate_center.outputs['Vector'], center_switch.inputs[True])  # С центрированием

            # Применяем смещение центрирования к точкам сетки
            center_geometry = nodes.new('GeometryNodeSetPosition')
            center_geometry.name = "Center Grid Points"
            links.new(switch_points.outputs['Output'], center_geometry.inputs['Geometry'])
            links.new(center_switch.outputs['Output'], center_geometry.inputs['Offset'])

            # Инстансирование на точках
            instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
            instance_on_points.name = "Instance Final Geometry"
            links.new(center_geometry.outputs['Geometry'], instance_on_points.inputs['Points'])

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные входные сокеты
            print("Доступные входы узла InstanceOnPoints для GRID клонера:")
            for input_name in instance_on_points.inputs.keys():
                print(f"  - {input_name}")

            # Соединяем входную геометрию с инстансами
            links.new(group_in.outputs[0], instance_on_points.inputs['Instance'])

            # --- Randomization and Transforms ---
            # Random values nodes
            index = nodes.new('GeometryNodeInputIndex')

            # Vector math для отрицательных диапазонов (для центрирования случайного диапазона около 0)
            vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
            vector_math_neg_pos.operation = 'MULTIPLY'
            vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Position'], vector_math_neg_pos.inputs[0])

            # Настройка случайности
            # Случайная позиция
            random_position = nodes.new('FunctionNodeRandomValue')
            random_position.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_position.inputs['Seed'])
            links.new(index.outputs['Index'], random_position.inputs['ID'])

            # Случайное вращение
            random_rotation = nodes.new('FunctionNodeRandomValue')
            random_rotation.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_rotation.inputs['Seed'])
            links.new(index.outputs['Index'], random_rotation.inputs['ID'])

            # Случайный масштаб
            random_scale = nodes.new('FunctionNodeRandomValue')
            random_scale.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_scale.inputs['Seed'])
            links.new(index.outputs['Index'], random_scale.inputs['ID'])

            # Настройка диапазона случайной позиции
            neg_random_pos = nodes.new('ShaderNodeVectorMath')
            neg_random_pos.operation = 'MULTIPLY'
            neg_random_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Position'], neg_random_pos.inputs[0])
            links.new(neg_random_pos.outputs['Vector'], random_position.inputs['Min'])
            links.new(group_in.outputs['Random Position'], random_position.inputs['Max'])

            # Настройка диапазона случайного вращения
            neg_random_rot = nodes.new('ShaderNodeVectorMath')
            neg_random_rot.operation = 'MULTIPLY'
            neg_random_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Rotation'], neg_random_rot.inputs[0])
            links.new(neg_random_rot.outputs['Vector'], random_rotation.inputs['Min'])
            links.new(group_in.outputs['Random Rotation'], random_rotation.inputs['Max'])

            # Настройка диапазона случайного масштаба
            # Создаем вектор из скалярного значения Random Scale
            combine_random_scale = nodes.new('ShaderNodeCombineXYZ')
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[0])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[1])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[2])

            # 1 - Random Scale для минимального значения
            vector_one_minus = nodes.new('ShaderNodeVectorMath')
            vector_one_minus.operation = 'SUBTRACT'
            vector_one_minus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_minus.inputs[1])

            # 1 + Random Scale для максимального значения
            vector_one_plus = nodes.new('ShaderNodeVectorMath')
            vector_one_plus.operation = 'ADD'
            vector_one_plus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_plus.inputs[1])

            # Устанавливаем диапазон для случайного масштаба
            links.new(vector_one_minus.outputs['Vector'], random_scale.inputs['Min'])
            links.new(vector_one_plus.outputs['Vector'], random_scale.inputs['Max'])

            # Смешиваем базовое вращение со случайным
            add_random_rotation = nodes.new('ShaderNodeVectorMath')
            add_random_rotation.operation = 'ADD'
            links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0]) # Используем вращение напрямую
            links.new(random_rotation.outputs['Value'], add_random_rotation.inputs[1])

            # Смешиваем базовое масштабирование со случайным
            add_random_scale = nodes.new('ShaderNodeVectorMath')
            add_random_scale.operation = 'MULTIPLY'
            links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0]) # Используем масштаб напрямую
            links.new(random_scale.outputs['Value'], add_random_scale.inputs[1])

            # Применяем случайное смещение
            set_position = nodes.new('GeometryNodeSetPosition')
            links.new(instance_on_points.outputs['Instances'], set_position.inputs['Geometry'])
            links.new(random_position.outputs['Value'], set_position.inputs['Offset'])

            # Применяем вращение (интерполированное + случайное)
            rotate_random = nodes.new('GeometryNodeRotateInstances')
            links.new(set_position.outputs['Geometry'], rotate_random.inputs['Instances'])
            links.new(add_random_rotation.outputs['Vector'], rotate_random.inputs['Rotation'])

            # Применяем масштаб (интерполированный * случайный)
            scale_random = nodes.new('GeometryNodeScaleInstances')
            links.new(rotate_random.outputs['Instances'], scale_random.inputs['Instances'])
            links.new(add_random_scale.outputs['Vector'], scale_random.inputs['Scale'])

            # Добавляем трансформацию
            transform = nodes.new('GeometryNodeTransform')
            links.new(scale_random.outputs['Instances'], transform.inputs['Geometry'])
            links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
            links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

            # Проверяем, включена ли опция анти-рекурсии
            use_anti_recursion = context.scene.use_anti_recursion

            if use_anti_recursion:
                # Создаем узлы анти-рекурсии
                # 1. Join Geometry node - это объединит всю геометрию и разорвет иерархию инстансов
                join_geometry = nodes.new('GeometryNodeJoinGeometry')
                join_geometry.name = "Anti-Recursion Join Geometry"
                join_geometry.location = (transform.location.x + 100, transform.location.y)

                # 2. Realize Instances node - это преобразует инстансы в реальную геометрию
                realize_instances = nodes.new('GeometryNodeRealizeInstances')
                realize_instances.name = "Anti-Recursion Realize"
                realize_instances.location = (transform.location.x + 200, transform.location.y)

                # 3. Switch node - для переключения между обычным и анти-рекурсивным режимом
                switch_node = nodes.new('GeometryNodeSwitch')
                switch_node.input_type = 'GEOMETRY'
                switch_node.name = "Anti-Recursion Switch"
                switch_node.location = (transform.location.x + 300, transform.location.y)

                # Соединяем узлы
                # Соединяем выход трансформации с Join Geometry
                links.new(transform.outputs['Geometry'], join_geometry.inputs[0])

                # Соединяем Join Geometry с Realize Instances
                links.new(join_geometry.outputs[0], realize_instances.inputs['Geometry'])

                # Соединяем переключатель
                links.new(group_in.outputs['Realize Instances'], switch_node.inputs['Switch'])
                links.new(transform.outputs['Geometry'], switch_node.inputs[False])  # Обычный режим
                links.new(realize_instances.outputs['Geometry'], switch_node.inputs[True])  # Анти-рекурсивный режим

                # Соединяем переключатель с выходом
                links.new(switch_node.outputs[0], group_out.inputs['Geometry'])
            else:
                # Если анти-рекурсия выключена, просто соединяем выход трансформации с выходом группы
                links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

        elif cloner_type == "LINEAR":
            # Создаем узлы для линейного клонера

            # Параметры интерполяции удалены для упрощения стекового LINEAR клонера

            # Offset Multiplier для правильного масштабирования
            offset_multiplier = nodes.new('ShaderNodeVectorMath')
            offset_multiplier.operation = 'MULTIPLY'
            # Используем множитель 1.0 для применения значений напрямую
            offset_multiplier.inputs[1].default_value = (1.0, 1.0, 1.0)
            links.new(group_in.outputs['Offset'], offset_multiplier.inputs[0])

            line_node = nodes.new('GeometryNodeMeshLine')
            if hasattr(line_node, "mode"):
                line_node.mode = 'OFFSET'
            if hasattr(line_node, "count_mode"):
                line_node.count_mode = 'TOTAL'

            # Соединяем параметры Count и Offset (используем множитель)
            links.new(group_in.outputs['Count'], line_node.inputs['Count'])

            # Используем умноженный offset для корректной работы
            if 'Offset' in line_node.inputs:
                links.new(offset_multiplier.outputs['Vector'], line_node.inputs['Offset'])
                # Создаем соединение для CountOffset (будет использоваться в UI)
                node_group["has_count_offset"] = True

            # Инстансирование на точках
            instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
            mesh_to_points = nodes.new('GeometryNodeMeshToPoints')

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные выходные сокеты mesh_to_points
            print("Доступные выходы узла MeshToPoints для LINEAR клонера:")
            for output_name in mesh_to_points.outputs.keys():
                print(f"  - {output_name}")

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные входные сокеты
            print("Доступные входы узла InstanceOnPoints для LINEAR клонера:")
            for input_name in instance_on_points.inputs.keys():
                print(f"  - {input_name}")

            # Соединяем линию с точками
            links.new(line_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

            # Безопасное соединение, проверяя наличие нужных сокетов
            if 'Points' in mesh_to_points.outputs and 'Points' in instance_on_points.inputs:
                links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
            elif 'Geometry' in mesh_to_points.outputs and 'Points' in instance_on_points.inputs:
                links.new(mesh_to_points.outputs['Geometry'], instance_on_points.inputs['Points'])
            else:
                print("ВНИМАНИЕ: Не найдены подходящие сокеты для соединения mesh_to_points с instance_on_points")
                # Перебираем доступные сочетания
                for out_name in mesh_to_points.outputs.keys():
                    for in_name in instance_on_points.inputs.keys():
                        if ('point' in out_name.lower() and 'point' in in_name.lower()) or \
                           ('geometry' in out_name.lower() and 'point' in in_name.lower()):
                            print(f"Пробуем соединить {out_name} -> {in_name}")
                            links.new(mesh_to_points.outputs[out_name], instance_on_points.inputs[in_name])
                            break

            # Соединяем входную геометрию с инстансами - ИСПОЛЬЗУЕМ ИНДЕКСЫ
            if 'Instance' in instance_on_points.inputs:
                # Используем индекс 0 вместо имени для доступа к сокету
                geometry_input_index = 0
                print(f"Используем индекс сокета geometry_input_index={geometry_input_index}")
                # Получаем полный список имен сокетов для отладки
                print(f"Индексы выходов group_in:")
                for i, name in enumerate(group_in.outputs):
                    print(f"  [{i}] {name}")

                # Пробуем использовать индекс вместо имени
                try:
                    links.new(group_in.outputs[geometry_input_index], instance_on_points.inputs['Instance'])
                    print(f"Успешно соединили сокеты по индексу {geometry_input_index}")
                except Exception as e:
                    print(f"Ошибка при соединении по индексу: {e}")
                    try:
                        # Альтернативный метод - через имя первого сокета в интерфейсе
                        first_socket_name = list(group_in.outputs.keys())[0]
                        print(f"Пробуем с именем первого сокета: {first_socket_name}")
                        links.new(group_in.outputs[first_socket_name], instance_on_points.inputs['Instance'])
                    except Exception as e2:
                        print(f"Вторая попытка тоже не удалась: {e2}")

            # Расчет интерполяции для Scale Start/End и Rotation Start/End удален
            # Но создаем узел индекса для генерации случайных значений
            index = nodes.new('GeometryNodeInputIndex')

            # Настройка случайности
            # Случайная позиция
            random_position = nodes.new('FunctionNodeRandomValue')
            random_position.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_position.inputs['Seed'])
            links.new(index.outputs['Index'], random_position.inputs['ID'])

            # Случайное вращение
            random_rotation = nodes.new('FunctionNodeRandomValue')
            random_rotation.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_rotation.inputs['Seed'])
            links.new(index.outputs['Index'], random_rotation.inputs['ID'])

            # Случайный масштаб
            random_scale = nodes.new('FunctionNodeRandomValue')
            random_scale.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_scale.inputs['Seed'])
            links.new(index.outputs['Index'], random_scale.inputs['ID'])

            # Настройка диапазона случайной позиции
            neg_random_pos = nodes.new('ShaderNodeVectorMath')
            neg_random_pos.operation = 'MULTIPLY'
            neg_random_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Position'], neg_random_pos.inputs[0])
            links.new(neg_random_pos.outputs['Vector'], random_position.inputs['Min'])
            links.new(group_in.outputs['Random Position'], random_position.inputs['Max'])

            # Настройка диапазона случайного вращения
            neg_random_rot = nodes.new('ShaderNodeVectorMath')
            neg_random_rot.operation = 'MULTIPLY'
            neg_random_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Rotation'], neg_random_rot.inputs[0])
            links.new(neg_random_rot.outputs['Vector'], random_rotation.inputs['Min'])
            links.new(group_in.outputs['Random Rotation'], random_rotation.inputs['Max'])

            # Настройка диапазона случайного масштаба
            # Создаем вектор из скалярного значения Random Scale
            combine_random_scale = nodes.new('ShaderNodeCombineXYZ')
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[0])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[1])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[2])

            # 1 - Random Scale для минимального значения
            vector_one_minus = nodes.new('ShaderNodeVectorMath')
            vector_one_minus.operation = 'SUBTRACT'
            vector_one_minus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_minus.inputs[1])

            # 1 + Random Scale для максимального значения
            vector_one_plus = nodes.new('ShaderNodeVectorMath')
            vector_one_plus.operation = 'ADD'
            vector_one_plus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_plus.inputs[1])

            # Устанавливаем диапазон для случайного масштаба
            links.new(vector_one_minus.outputs['Vector'], random_scale.inputs['Min'])
            links.new(vector_one_plus.outputs['Vector'], random_scale.inputs['Max'])

            # Смешиваем базовое вращение со случайным
            add_random_rotation = nodes.new('ShaderNodeVectorMath')
            add_random_rotation.operation = 'ADD'
            links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
            links.new(random_rotation.outputs['Value'], add_random_rotation.inputs[1])

            # Смешиваем базовое масштабирование со случайным
            add_random_scale = nodes.new('ShaderNodeVectorMath')
            add_random_scale.operation = 'MULTIPLY'
            links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
            links.new(random_scale.outputs['Value'], add_random_scale.inputs[1])

            # Применяем случайное смещение
            set_position = nodes.new('GeometryNodeSetPosition')
            links.new(instance_on_points.outputs['Instances'], set_position.inputs['Geometry'])
            links.new(random_position.outputs['Value'], set_position.inputs['Offset'])

            # Применяем вращение (интерполированное + случайное)
            rotate_random = nodes.new('GeometryNodeRotateInstances')
            links.new(set_position.outputs['Geometry'], rotate_random.inputs['Instances'])
            links.new(add_random_rotation.outputs['Vector'], rotate_random.inputs['Rotation'])

            # Применяем масштаб (интерполированный * случайный)
            scale_random = nodes.new('GeometryNodeScaleInstances')
            links.new(rotate_random.outputs['Instances'], scale_random.inputs['Instances'])
            links.new(add_random_scale.outputs['Vector'], scale_random.inputs['Scale'])

            # Добавляем трансформацию
            transform = nodes.new('GeometryNodeTransform')
            links.new(scale_random.outputs['Instances'], transform.inputs['Geometry'])
            links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
            links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

            # Проверяем, включена ли опция анти-рекурсии
            use_anti_recursion = context.scene.use_anti_recursion

            if use_anti_recursion:
                # Создаем узлы анти-рекурсии
                # 1. Join Geometry node - это объединит всю геометрию и разорвет иерархию инстансов
                join_geometry = nodes.new('GeometryNodeJoinGeometry')
                join_geometry.name = "Anti-Recursion Join Geometry"
                join_geometry.location = (transform.location.x + 100, transform.location.y)

                # 2. Realize Instances node - это преобразует инстансы в реальную геометрию
                realize_instances = nodes.new('GeometryNodeRealizeInstances')
                realize_instances.name = "Anti-Recursion Realize"
                realize_instances.location = (transform.location.x + 200, transform.location.y)

                # 3. Switch node - для переключения между обычным и анти-рекурсивным режимом
                switch_node = nodes.new('GeometryNodeSwitch')
                switch_node.input_type = 'GEOMETRY'
                switch_node.name = "Anti-Recursion Switch"
                switch_node.location = (transform.location.x + 300, transform.location.y)

                # Соединяем узлы
                # Соединяем выход трансформации с Join Geometry
                links.new(transform.outputs['Geometry'], join_geometry.inputs[0])

                # Соединяем Join Geometry с Realize Instances
                links.new(join_geometry.outputs[0], realize_instances.inputs['Geometry'])

                # Соединяем переключатель
                links.new(group_in.outputs['Realize Instances'], switch_node.inputs['Switch'])
                links.new(transform.outputs['Geometry'], switch_node.inputs[False])  # Обычный режим
                links.new(realize_instances.outputs['Geometry'], switch_node.inputs[True])  # Анти-рекурсивный режим

                # Соединяем переключатель с выходом
                links.new(switch_node.outputs[0], group_out.inputs['Geometry'])
            else:
                # Если анти-рекурсия выключена, просто соединяем выход трансформации с выходом группы
                links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные входные сокеты
            print("Доступные входы узла InstanceOnPoints для LINEAR клонера:")
            for input_name in instance_on_points.inputs.keys():
                print(f"  - {input_name}")

        elif cloner_type == "CIRCLE":
            # Создаем узлы для окружности

            # Добавляем параметр Height для 3D позиционирования
            height_input = node_group.interface.new_socket(name="Height", in_out='INPUT', socket_type='NodeSocketFloat')
            height_input.default_value = 0.0

            # Radius Multiplier для правильного масштабирования
            radius_multiplier = nodes.new('ShaderNodeMath')
            radius_multiplier.operation = 'MULTIPLY'
            # Используем множитель 1.0 для применения значений напрямую
            radius_multiplier.inputs[1].default_value = 1.0
            links.new(group_in.outputs['Radius'], radius_multiplier.inputs[0])

            # Height Multiplier для правильного масштабирования
            height_multiplier = nodes.new('ShaderNodeMath')
            height_multiplier.operation = 'MULTIPLY'
            # Используем множитель 1.0 для применения значений напрямую
            height_multiplier.inputs[1].default_value = 1.0
            links.new(group_in.outputs['Height'], height_multiplier.inputs[0])

            circle_node = nodes.new('GeometryNodeMeshCircle')
            circle_node.fill_type = 'NONE'  # Только вершины окружности для правильного клонирования

            # Соединяем сокеты группы с узлами
            links.new(group_in.outputs['Count'], circle_node.inputs['Vertices'])
            links.new(radius_multiplier.outputs['Value'], circle_node.inputs['Radius'])

            # Добавляем маркер для отображения CountRadius в UI
            node_group["has_count_radius"] = True

            # Создаем узел для установки высоты
            set_height = nodes.new('GeometryNodeSetPosition')
            combine_height = nodes.new('ShaderNodeCombineXYZ')
            combine_height.inputs[0].default_value = 0.0  # X остается без изменений
            combine_height.inputs[1].default_value = 0.0  # Y остается без изменений
            links.new(height_multiplier.outputs['Value'], combine_height.inputs[2])  # Z = Height * Multiplier

            # Инстансирование на точках
            instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
            mesh_to_points = nodes.new('GeometryNodeMeshToPoints')

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные выходные сокеты mesh_to_points
            print("Доступные выходы узла MeshToPoints для CIRCLE клонера:")
            for output_name in mesh_to_points.outputs.keys():
                print(f"  - {output_name}")

            # ОТЛАДОЧНЫЙ КОД: выводим все доступные входные сокеты
            print("Доступные входы узла InstanceOnPoints для CIRCLE клонера:")
            for input_name in instance_on_points.inputs.keys():
                print(f"  - {input_name}")

            # Соединяем окружность с точками
            links.new(circle_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

            # Безопасное соединение, проверяя наличие нужных сокетов
            if 'Points' in mesh_to_points.outputs and 'Geometry' in set_height.inputs:
                links.new(mesh_to_points.outputs['Points'], set_height.inputs['Geometry'])
            elif 'Geometry' in mesh_to_points.outputs and 'Geometry' in set_height.inputs:
                links.new(mesh_to_points.outputs['Geometry'], set_height.inputs['Geometry'])
            else:
                print("ВНИМАНИЕ: Не найдены подходящие сокеты для соединения mesh_to_points с set_height")
                # Перебираем доступные сочетания
                for out_name in mesh_to_points.outputs.keys():
                    if 'Geometry' in set_height.inputs:
                        print(f"Пробуем соединить {out_name} -> Geometry")
                        links.new(mesh_to_points.outputs[out_name], set_height.inputs['Geometry'])
                        break

            links.new(combine_height.outputs['Vector'], set_height.inputs['Offset'])

            # Соединяем с инстансированием
            if 'Geometry' in set_height.outputs and 'Points' in instance_on_points.inputs:
                links.new(set_height.outputs['Geometry'], instance_on_points.inputs['Points'])
            else:
                print("ВНИМАНИЕ: Не найдены подходящие сокеты для соединения set_height с instance_on_points")
                # Перебираем доступные сочетания
                for out_name in set_height.outputs.keys():
                    for in_name in instance_on_points.inputs.keys():
                        if ('point' in in_name.lower()):
                            print(f"Пробуем соединить {out_name} -> {in_name}")
                            links.new(set_height.outputs[out_name], instance_on_points.inputs[in_name])
                            break

            # Соединяем входную геометрию с инстансами - ИСПОЛЬЗУЕМ ИНДЕКСЫ
            if 'Instance' in instance_on_points.inputs:
                # Используем индекс 0 вместо имени для доступа к сокету
                geometry_input_index = 0
                print(f"Используем индекс сокета для CIRCLE: geometry_input_index={geometry_input_index}")
                # Получаем полный список имен сокетов для отладки
                print(f"Индексы выходов group_in для CIRCLE:")
                for i, name in enumerate(group_in.outputs):
                    print(f"  [{i}] {name}")

                # Пробуем использовать индекс вместо имени
                try:
                    links.new(group_in.outputs[geometry_input_index], instance_on_points.inputs['Instance'])
                    print(f"Успешно соединили сокеты CIRCLE по индексу {geometry_input_index}")
                except Exception as e:
                    print(f"Ошибка при соединении CIRCLE по индексу: {e}")
                    try:
                        # Альтернативный метод - через имя первого сокета в интерфейсе
                        first_socket_name = list(group_in.outputs.keys())[0]
                        print(f"Пробуем с именем первого сокета CIRCLE: {first_socket_name}")
                        links.new(group_in.outputs[first_socket_name], instance_on_points.inputs['Instance'])
                    except Exception as e2:
                        print(f"Вторая попытка для CIRCLE тоже не удалась: {e2}")

            # Добавляем поворот к центру (лицом внутрь)
            face_center = nodes.new('GeometryNodeRotateInstances')
            combine_face_center = nodes.new('ShaderNodeCombineXYZ')
            combine_face_center.inputs[0].default_value = 0.0   # X
            combine_face_center.inputs[1].default_value = 0.0   # Y
            combine_face_center.inputs[2].default_value = 90.0  # Z - поворот на 90 градусов

            links.new(instance_on_points.outputs['Instances'], face_center.inputs['Instances'])
            links.new(combine_face_center.outputs['Vector'], face_center.inputs['Rotation'])

            # Применяем пользовательское вращение после поворота к центру
            rotate_user = nodes.new('GeometryNodeRotateInstances')
            links.new(face_center.outputs['Instances'], rotate_user.inputs['Instances'])
            links.new(group_in.outputs['Instance Rotation'], rotate_user.inputs['Rotation'])

            # ОТЛАДКА ROTATE_USER
            print("Доступные входы узла rotate_user для CIRCLE клонера:")
            for i, input_name in enumerate(rotate_user.inputs.keys()):
                print(f"  [{i}] {input_name}")

            # Выводим информацию о сокетах group_in
            print("Доступные выходы узла group_in для CIRCLE клонера:")
            for i, output_name in enumerate(group_in.outputs.keys()):
                print(f"  [{i}] {output_name}")

            # Найдем индекс сокета Instance Scale в group_in
            scale_socket_index = None
            for i, name in enumerate(group_in.outputs.keys()):
                if name == "Instance Scale":
                    scale_socket_index = i
                    print(f"Найден сокет Instance Scale по индексу {i}")
                    break

            # Найдем индекс сокета Scale в rotate_user
            rotate_scale_index = None
            for i, name in enumerate(rotate_user.inputs.keys()):
                if name == "Scale":
                    rotate_scale_index = i
                    print(f"Найден сокет Scale в rotate_user по индексу {i}")
                    break

            # Пробуем соединить по индексам
            if scale_socket_index is not None and rotate_scale_index is not None:
                try:
                    links.new(group_in.outputs[scale_socket_index], rotate_user.inputs[rotate_scale_index])
                    print(f"Успешно соединили сокеты масштаба по индексам")
                except Exception as e:
                    print(f"Ошибка при соединении сокетов масштаба по индексам: {e}")
            else:
                print(f"ВНИМАНИЕ: Не найдены индексы для сокетов масштаба")

            # Прямое соединение по имени - более надежное решение
            if "Scale" in rotate_user.inputs and "Instance Scale" in [s.name for s in group_in.outputs]:
                try:
                    links.new(group_in.outputs["Instance Scale"], rotate_user.inputs["Scale"])
                    print(f"Успешно соединили сокеты масштаба по имени")
                except Exception as e:
                    print(f"Ошибка при соединении сокетов масштаба по имени: {e}")

            # Настройка случайности
            # Индекс для ID случайности
            index = nodes.new('GeometryNodeInputIndex')

            # Случайная позиция
            random_position = nodes.new('FunctionNodeRandomValue')
            random_position.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_position.inputs['Seed'])
            links.new(index.outputs['Index'], random_position.inputs['ID'])

            # Настройка диапазона случайной позиции
            neg_random_pos = nodes.new('ShaderNodeVectorMath')
            neg_random_pos.operation = 'MULTIPLY'
            neg_random_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Position'], neg_random_pos.inputs[0])
            links.new(neg_random_pos.outputs['Vector'], random_position.inputs['Min'])
            links.new(group_in.outputs['Random Position'], random_position.inputs['Max'])

            # Случайное вращение
            random_rotation = nodes.new('FunctionNodeRandomValue')
            random_rotation.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_rotation.inputs['Seed'])
            links.new(index.outputs['Index'], random_rotation.inputs['ID'])

            # Настройка диапазона случайного вращения
            neg_random_rot = nodes.new('ShaderNodeVectorMath')
            neg_random_rot.operation = 'MULTIPLY'
            neg_random_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
            links.new(group_in.outputs['Random Rotation'], neg_random_rot.inputs[0])
            links.new(neg_random_rot.outputs['Vector'], random_rotation.inputs['Min'])
            links.new(group_in.outputs['Random Rotation'], random_rotation.inputs['Max'])

            # Случайный масштаб
            random_scale = nodes.new('FunctionNodeRandomValue')
            random_scale.data_type = 'FLOAT_VECTOR'
            links.new(group_in.outputs['Random Seed'], random_scale.inputs['Seed'])
            links.new(index.outputs['Index'], random_scale.inputs['ID'])

            # Настройка диапазона случайного масштаба
            # Создаем вектор из скалярного значения Random Scale
            combine_random_scale = nodes.new('ShaderNodeCombineXYZ')
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[0])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[1])
            links.new(group_in.outputs['Random Scale'], combine_random_scale.inputs[2])

            # 1 - Random Scale для минимального значения
            vector_one_minus = nodes.new('ShaderNodeVectorMath')
            vector_one_minus.operation = 'SUBTRACT'
            vector_one_minus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_minus.inputs[1])

            # 1 + Random Scale для максимального значения
            vector_one_plus = nodes.new('ShaderNodeVectorMath')
            vector_one_plus.operation = 'ADD'
            vector_one_plus.inputs[0].default_value = (1.0, 1.0, 1.0)
            links.new(combine_random_scale.outputs['Vector'], vector_one_plus.inputs[1])

            # Устанавливаем диапазон для случайного масштаба
            links.new(vector_one_minus.outputs['Vector'], random_scale.inputs['Min'])
            links.new(vector_one_plus.outputs['Vector'], random_scale.inputs['Max'])

            # Смешиваем базовое (интерполированное) вращение со случайным
            add_random_rotation = nodes.new('ShaderNodeVectorMath')
            add_random_rotation.operation = 'ADD'
            links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
            links.new(random_rotation.outputs['Value'], add_random_rotation.inputs[1])

            # Смешиваем базовое (интерполированное) масштабирование со случайным
            add_random_scale = nodes.new('ShaderNodeVectorMath')
            add_random_scale.operation = 'MULTIPLY'
            links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
            links.new(random_scale.outputs['Value'], add_random_scale.inputs[1])

            # Применяем случайное смещение
            set_position = nodes.new('GeometryNodeSetPosition')
            links.new(rotate_user.outputs['Instances'], set_position.inputs['Geometry'])
            links.new(random_position.outputs['Value'], set_position.inputs['Offset'])

            # Применяем вращение (интерполированное + случайное)
            rotate_random = nodes.new('GeometryNodeRotateInstances')
            links.new(set_position.outputs['Geometry'], rotate_random.inputs['Instances'])
            links.new(add_random_rotation.outputs['Vector'], rotate_random.inputs['Rotation'])

            # Применяем масштаб (интерполированный * случайный)
            scale_random = nodes.new('GeometryNodeScaleInstances')
            links.new(rotate_random.outputs['Instances'], scale_random.inputs['Instances'])
            links.new(add_random_scale.outputs['Vector'], scale_random.inputs['Scale'])

            # Добавляем трансформацию
            transform = nodes.new('GeometryNodeTransform')
            links.new(scale_random.outputs['Instances'], transform.inputs['Geometry'])
            links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
            links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

            # Проверяем, включена ли опция анти-рекурсии
            use_anti_recursion = context.scene.use_anti_recursion

            if use_anti_recursion:
                # Создаем узлы анти-рекурсии
                # 1. Join Geometry node - это объединит всю геометрию и разорвет иерархию инстансов
                join_geometry = nodes.new('GeometryNodeJoinGeometry')
                join_geometry.name = "Anti-Recursion Join Geometry"
                join_geometry.location = (transform.location.x + 100, transform.location.y)

                # 2. Realize Instances node - это преобразует инстансы в реальную геометрию
                realize_instances = nodes.new('GeometryNodeRealizeInstances')
                realize_instances.name = "Anti-Recursion Realize"
                realize_instances.location = (transform.location.x + 200, transform.location.y)

                # 3. Switch node - для переключения между обычным и анти-рекурсивным режимом
                switch_node = nodes.new('GeometryNodeSwitch')
                switch_node.input_type = 'GEOMETRY'
                switch_node.name = "Anti-Recursion Switch"
                switch_node.location = (transform.location.x + 300, transform.location.y)

                # Соединяем узлы
                # Соединяем выход трансформации с Join Geometry
                links.new(transform.outputs['Geometry'], join_geometry.inputs[0])

                # Соединяем Join Geometry с Realize Instances
                links.new(join_geometry.outputs[0], realize_instances.inputs['Geometry'])

                # Соединяем переключатель
                links.new(group_in.outputs['Realize Instances'], switch_node.inputs['Switch'])
                links.new(transform.outputs['Geometry'], switch_node.inputs[False])  # Обычный режим
                links.new(realize_instances.outputs['Geometry'], switch_node.inputs[True])  # Анти-рекурсивный режим

                # Соединяем переключатель с выходом
                links.new(switch_node.outputs[0], group_out.inputs['Geometry'])
            else:
                # Если анти-рекурсия выключена, просто соединяем выход трансформации с выходом группы
                links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

        # Инициализируем список эффекторов
        node_group["linked_effectors"] = []

        # Добавляем флаг для идентификации стекового клонера
        node_group["is_stacked_cloner"] = True
        node_group["cloner_type"] = cloner_type

        # Создаем модификатор на целевом объекте
        modifier = target_obj.modifiers.new(name=modifier_name, type='NODES')

        # Устанавливаем флаги для идентификации стекового клонера
        modifier["is_stacked_cloner"] = True
        modifier["cloner_type"] = cloner_type

        # Дополнительные метаданные для корректной работы UI
        # Записываем в разных форматах для надежности
        if cloner_type == "GRID":
            modifier["cloner_display_type"] = "Grid"
        elif cloner_type == "LINEAR":
            modifier["cloner_display_type"] = "Linear"
            # Для LINEAR включаем Use Effector для работы интерполяции
            use_effector_id = find_socket_by_name(modifier, "Use Effector")
            if use_effector_id:
                try:
                    modifier[use_effector_id] = True
                except Exception as e:
                    print(f"Warning: Could not set Use Effector for LINEAR cloner: {e}")
        elif cloner_type == "CIRCLE":
            modifier["cloner_display_type"] = "Circle"

        # Теперь безопасно устанавливаем группу узлов
        modifier.node_group = node_group
        print(f"Установлена группа узлов {node_group.name} в модификатор {modifier_name}")

        # Обновляем с эффекторами (изначально пустой список)
        try:
            # В update_cloner_with_effectors тоже проверим использование имени 'Geometry'
            update_cloner_with_effectors(target_obj, modifier)
        except Exception as e:
            print(f"Ошибка при обновлении эффекторов: {e}")

        # Пытаемся установить параметры клонера на основе типа
        if cloner_type == "GRID":
            setup_grid_cloner_params(modifier)
        elif cloner_type == "LINEAR":
            setup_linear_cloner_params(modifier)
        elif cloner_type == "CIRCLE":
            setup_circle_cloner_params(modifier)

        print(f"Created {base_mod_name} using stacked modifiers")
        return modifier, True

    except Exception as e:
        print(f"Ошибка при создании стекового клонера: {e}")
        import traceback
        traceback.print_exc()
        return None, False