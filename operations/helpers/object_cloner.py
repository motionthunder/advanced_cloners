import bpy
import bmesh
from ...core.common.constants import CLONER_MOD_NAMES
from ...models.cloners.grid_cloner import GridCloner
from ...models.cloners.linear_cloner import LinearCloner
from ...models.cloners.circle_cloner import CircleCloner
from ...core.utils.cloner_utils import get_cloner_chain_for_object
from ...core.utils.node_utils import find_socket_by_name

from .common_utils import find_layer_collection
from .params_utils import (
    setup_grid_cloner_params,
    setup_linear_cloner_params,
    setup_circle_cloner_params
)
from .stacked_cloner import create_stacked_cloner

def create_object_cloner(context, cloner_type, orig_obj, use_stacked_modifiers=False, use_custom_group=True):
    """
    Создает клонер для объекта.

    Args:
        context: Контекст Blender
        cloner_type: Тип клонера (GRID, LINEAR, CIRCLE)
        orig_obj: Исходный объект для клонирования
        use_stacked_modifiers: Использовать стековые модификаторы
        use_custom_group: Использовать кастомную группу узлов

    Returns:
        bool: True если клонер успешно создан, False в случае ошибки
    """
    # Проверяем режим работы - стековые модификаторы или обычные клонеры
    is_stacked_mode = use_stacked_modifiers
    print(f"DEBUG: use_stacked_modifiers = {use_stacked_modifiers}, is_stacked_mode = {is_stacked_mode}")

    # В зависимости от режима вызываем соответствующую функцию
    if is_stacked_mode:
        # Создаем стековый клонер на том же объекте
        modifier, success = create_stacked_cloner(context, cloner_type, orig_obj)
        return success
    else:
        # Создаем обычный клонер (новый объект с модификатором)
        success = create_standard_object_cloner(context, cloner_type, orig_obj, use_custom_group)
        return success

def create_standard_object_cloner(context, cloner_type, orig_obj, use_custom_group=True):
    """
    Создает обычный (не стековый) клонер для объекта.

    Args:
        context: Контекст Blender
        cloner_type: Тип клонера (GRID, LINEAR, CIRCLE)
        orig_obj: Исходный объект для клонирования
        use_custom_group: Использовать кастомную группу узлов

    Returns:
        bool: True если клонер успешно создан, False в случае ошибки
    """
    try:
        # Получаем базовое имя модификатора
        base_mod_name = CLONER_MOD_NAMES[cloner_type]

        # Создаем уникальное имя для клонер-объекта
        cloner_name = f"Cloner_{orig_obj.name}_{cloner_type}"
        counter = 1
        while cloner_name in bpy.data.objects:
            cloner_name = f"Cloner_{orig_obj.name}_{cloner_type}_{counter:03d}"
            counter += 1

        # Создаем пустой объект для клонера
        mesh = bpy.data.meshes.new(f"{cloner_name}_Mesh")
        cloner_obj = bpy.data.objects.new(cloner_name, mesh)

        # Создаем коллекцию для клонера
        cloner_collection_name = f"cloner_{cloner_type.lower()}_{orig_obj.name}"
        counter = 1
        while cloner_collection_name in bpy.data.collections:
            cloner_collection_name = f"cloner_{cloner_type.lower()}_{orig_obj.name}_{counter:03d}"
            counter += 1

        cloner_collection = bpy.data.collections.new(cloner_collection_name)
        bpy.context.scene.collection.children.link(cloner_collection)

        # Добавляем клонер-объект в коллекцию
        cloner_collection.objects.link(cloner_obj)

                # Функция find_layer_collection импортирована из common_utils

        # Убеждаемся, что коллекция клонера видима
        layer_collection = context.view_layer.layer_collection
        layer_coll = find_layer_collection(layer_collection, cloner_collection.name)
        if layer_coll:
            # Всегда делаем коллекцию клонера видимой
            layer_coll.exclude = False

            # Гарантируем, что созданный клонер видим
            if cloner_obj:
                cloner_obj.hide_viewport = False
                cloner_obj.hide_render = False

                # Гарантируем, что объект имеет вершины
                if cloner_obj.type == 'MESH' and len(cloner_obj.data.vertices) == 0:
                    # Создаем простую геометрию, чтобы объект был видим
                    bm = bmesh.new()
                    bm.verts.new((0, 0, 0))
                    bm.to_mesh(cloner_obj.data)
                    bm.free()

        # Проверяем и обеспечиваем видимость всех коллекций клонеров в цепочке
        if orig_obj.name.startswith("Cloner_"):
            for mod in orig_obj.modifiers:
                if mod.type == 'NODES' and mod.get("cloner_collection"):
                    prev_collection_name = mod.get("cloner_collection")
                    prev_layer_coll = find_layer_collection(layer_collection, prev_collection_name)
                    if prev_layer_coll:
                        prev_layer_coll.exclude = False

        # Создаем уникальное имя для модификатора
        modifier_name = base_mod_name
        counter = 1
        while modifier_name in cloner_obj.modifiers:
            modifier_name = f"{base_mod_name}.{counter:03d}"
            counter += 1

        # Создаем модификатор на клонер-объекте
        modifier = cloner_obj.modifiers.new(name=modifier_name, type='NODES')

        # Создаем node группу для клонирования объекта
        node_group_name = f"ObjectCloner_{cloner_type}_{orig_obj.name}"
        counter = 1
        while node_group_name in bpy.data.node_groups:
            node_group_name = f"ObjectCloner_{cloner_type}_{orig_obj.name}_{counter:03d}"
            counter += 1

        # Создаем новую node группу
        node_group = bpy.data.node_groups.new(node_group_name, 'GeometryNodeTree')

        # Настраиваем базовую структуру узлов
        setup_basic_node_structure(node_group, orig_obj, cloner_type)

        # Применяем анти-рекурсию, если включена соответствующая опция
        if context.scene.use_anti_recursion:
            from ...operations.fix_recursion import apply_anti_recursion_to_cloner
            apply_anti_recursion_to_cloner(node_group)

        # Устанавливаем свойства для клонера
        modifier["is_chained_cloner"] = True
        modifier["source_type"] = "OBJECT"
        modifier["cloner_collection"] = cloner_collection.name

        # Устанавливаем группу узлов для модификатора
        modifier.node_group = node_group

        # Инициализируем список эффекторов
        node_group["linked_effectors"] = []

        # Сохраняем тип источника и другие метаданные
        modifier["source_type"] = "OBJECT"
        modifier["original_object"] = orig_obj.name
        modifier["cloner_collection"] = cloner_collection.name

        # Сохраняем состояние видимости оригинального объекта
        modifier["original_hide_viewport"] = orig_obj.hide_viewport
        modifier["original_hide_render"] = orig_obj.hide_render

        # Скрываем оригинальный объект только если это не клонер
        if not orig_obj.name.startswith("Cloner_"):
            orig_obj.hide_viewport = True
            orig_obj.hide_render = True

        # Устанавливаем параметры клонера
        if cloner_type == "GRID":
            setup_grid_cloner_params(modifier)
        elif cloner_type == "LINEAR":
            setup_linear_cloner_params(modifier)
        elif cloner_type == "CIRCLE":
            setup_circle_cloner_params(modifier)

        # Делаем клонер-объект активным
        for obj in context.selected_objects:
            obj.select_set(False)
        cloner_obj.select_set(True)
        context.view_layer.objects.active = cloner_obj

        # Обрабатываем связь для цепочки клонеров
        if "original_obj" in orig_obj or orig_obj.name.startswith("Cloner_"):
            # Это означает, что текущий объект уже является результатом клонирования
            modifier["is_object_chain"] = True
            modifier["previous_cloner_object"] = orig_obj.name
            modifier["is_chained_cloner"] = True

            # Сохраняем источник цепочки
            if "chain_source_object" in orig_obj:
                modifier["chain_source_object"] = orig_obj["chain_source_object"]
            else:
                modifier["chain_source_object"] = orig_obj.name

                                    # Регистрируем обновление цепочки            if hasattr(bpy.app, "timers"):                # Используем функцию register_chain_update из common_utils                # но эта функция сделана под другой контекст, поэтому лучше оставить оригинал                def register_chain_update_local():                    try:                        # Находим все предыдущие клонеры в цепочке                        chain = get_cloner_chain_for_object(orig_obj)                                                # Обновляем связи для всей цепочки                        for chain_obj in chain:                            if hasattr(chain_obj, 'name') and chain_obj.name != cloner_obj.name:                                for mod in chain_obj.modifiers:                                    if mod.type == 'NODES' and mod.get("is_chained_cloner"):                                        if "next_cloners" not in mod:                                            mod["next_cloners"] = []                                        if cloner_obj.name not in mod["next_cloners"]:                                            mod["next_cloners"].append(cloner_obj.name)                    except Exception as e:                        print(f"Ошибка при обновлении цепочки клонеров: {e}")                                        # Принудительное обновление                    bpy.context.view_layer.update()                    return None  # Запуск только один раз                                # Регистрируем обновление с небольшой задержкой
                # Используем функцию register_chain_update из common_utils                bpy.app.timers.register(lambda: register_chain_update(orig_obj, cloner_obj), first_interval=0.2)
        else:
            # Если это первый клонер, сохраняем ссылку на источник
            modifier["chain_source_object"] = orig_obj.name

        # Инициализируем список следующих клонеров
        modifier["next_cloners"] = []

        # Обновляем UI
        context.view_layer.update()

        return True

    except Exception as e:
        print(f"Error creating object cloner: {e}")
        return False

def setup_basic_node_structure(node_group, orig_obj, cloner_type):

    """
    Настраивает базовую структуру узлов для клонера объекта.

    Args:
        node_group: Группа узлов для настройки
        orig_obj: Исходный объект для клонирования
        cloner_type: Тип клонера (GRID, LINEAR, CIRCLE)
    """
    # Объявляем переменные на уровне функции для всех типов клонеров
    has_z_instances = False
    instances_on_z = None

    # Настраиваем интерфейс node группы
    node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Добавляем основные входные сокеты в зависимости от типа клонера
    if cloner_type == "LINEAR":
        count_socket = node_group.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_socket.default_value = 5

        offset_socket = node_group.interface.new_socket("Offset", in_out='INPUT', socket_type='NodeSocketVector')
        offset_socket.default_value = (3.0, 0.0, 0.0)
    elif cloner_type == "GRID":
        # Используем готовую логику из класса GridCloner
        print(f"Создание Grid клонера с использованием логики из GridCloner для объекта {orig_obj.name}")

        # Создаем logic_group с основной логикой клонера
        logic_group = GridCloner.create_logic_group(f"_{orig_obj.name}")

        # Очищаем текущую группу узлов и добавляем только необходимые интерфейсные сокеты
        for socket in list(node_group.interface.items_tree):
            node_group.interface.remove(socket)

        # Добавляем базовый выходной сокет
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # Основные параметры для Grid
        count_x_socket = node_group.interface.new_socket("Count X", in_out='INPUT', socket_type='NodeSocketInt')
        count_x_socket.default_value = 3

        count_y_socket = node_group.interface.new_socket("Count Y", in_out='INPUT', socket_type='NodeSocketInt')
        count_y_socket.default_value = 3

        count_z_socket = node_group.interface.new_socket("Count Z", in_out='INPUT', socket_type='NodeSocketInt')
        count_z_socket.default_value = 1

        spacing_socket = node_group.interface.new_socket("Spacing", in_out='INPUT', socket_type='NodeSocketVector')
        spacing_socket.default_value = (3.0, 3.0, 3.0)

        # Добавляем общие сокеты как в оригинальной функции
        rotation_socket = node_group.interface.new_socket("Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_socket.default_value = (0.0, 0.0, 0.0)
        rotation_socket.subtype = 'EULER'

        scale_socket = node_group.interface.new_socket("Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')
        scale_socket.default_value = (1.0, 1.0, 1.0)

        # Global transform
        global_pos_socket = node_group.interface.new_socket("Global Position", in_out='INPUT', socket_type='NodeSocketVector')
        global_pos_socket.default_value = (0.0, 0.0, 0.0)

        global_rot_socket = node_group.interface.new_socket("Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        global_rot_socket.default_value = (0.0, 0.0, 0.0)
        global_rot_socket.subtype = 'EULER'

        # Random parameters
        random_seed_socket = node_group.interface.new_socket("Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        random_seed_socket.default_value = 0

        random_pos_socket = node_group.interface.new_socket("Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_pos_socket.default_value = (0.0, 0.0, 0.0)

        random_rot_socket = node_group.interface.new_socket("Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rot_socket.default_value = (0.0, 0.0, 0.0)

        random_scale_socket = node_group.interface.new_socket("Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_socket.default_value = 0.0

        # Extra options
        center_grid_socket = node_group.interface.new_socket("Center Grid", in_out='INPUT', socket_type='NodeSocketBool')
        center_grid_socket.default_value = True

        pick_instance_socket = node_group.interface.new_socket("Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
        pick_instance_socket.default_value = False

        # Построение основной структуры узлов
        nodes = node_group.nodes
        links = node_group.links

        # Очищаем существующие узлы
        for node in list(nodes):
            nodes.remove(node)

        # Группы ввода/вывода
        group_in = nodes.new('NodeGroupInput')
        group_out = nodes.new('NodeGroupOutput')
        group_in.location = (-800, 0)
        group_out.location = (800, 0)

        # Узел для получения инстансов объекта
        object_info = nodes.new('GeometryNodeObjectInfo')
        object_info.transform_space = 'RELATIVE'
        if hasattr(object_info, 'instance_mode'):
            object_info.instance_mode = True
        object_info.location = (-600, 200)

        # Устанавливаем оригинальный объект как источник
        object_info.inputs['Object'].default_value = orig_obj

        # Определяем сокет вывода для разных версий Blender
        output_socket = 'Instances' if 'Instances' in object_info.outputs else 'Geometry'

        # Добавляем узел с логикой клонера
        cloner_logic_node = nodes.new('GeometryNodeGroup')
        cloner_logic_node.node_tree = logic_group
        cloner_logic_node.name = "Grid Cloner Logic"
        cloner_logic_node.location = (0, 0)

        # Соединяем инстансы объекта с инстансами клонера
        links.new(object_info.outputs[output_socket], cloner_logic_node.inputs['Instance Source'])

        # Соединяем основные параметры
        links.new(group_in.outputs['Count X'], cloner_logic_node.inputs['Count X'])
        links.new(group_in.outputs['Count Y'], cloner_logic_node.inputs['Count Y'])
        links.new(group_in.outputs['Count Z'], cloner_logic_node.inputs['Count Z'])
        links.new(group_in.outputs['Spacing'], cloner_logic_node.inputs['Spacing'])
        links.new(group_in.outputs['Instance Scale'], cloner_logic_node.inputs['Instance Scale'])
        links.new(group_in.outputs['Instance Rotation'], cloner_logic_node.inputs['Instance Rotation'])
        links.new(group_in.outputs['Random Position'], cloner_logic_node.inputs['Random Position'])
        links.new(group_in.outputs['Random Rotation'], cloner_logic_node.inputs['Random Rotation'])
        links.new(group_in.outputs['Random Scale'], cloner_logic_node.inputs['Random Scale'])
        links.new(group_in.outputs['Random Seed'], cloner_logic_node.inputs['Random Seed'])
        links.new(group_in.outputs['Pick Random Instance'], cloner_logic_node.inputs['Pick Random Instance'])
        links.new(group_in.outputs['Center Grid'], cloner_logic_node.inputs['Center Grid'])

        # Добавляем соединение для параметра Realize Instances
        if 'Realize Instances' in group_in.outputs and 'Realize Instances' in cloner_logic_node.inputs:
            links.new(group_in.outputs['Realize Instances'], cloner_logic_node.inputs['Realize Instances'])
            print("Connected Realize Instances parameter to Grid Cloner Logic")

        # Глобальные трансформации
        transform = nodes.new('GeometryNodeTransform')
        transform.location = (400, 0)

        # Соединяем трансформацию напрямую
        links.new(cloner_logic_node.outputs['Geometry'], transform.inputs['Geometry'])
        links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
        links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

        # Проверяем, включена ли анти-рекурсия для создания соответствующих узлов
        use_anti_recursion = False
        if hasattr(bpy.context.scene, "use_anti_recursion"):
            use_anti_recursion = bpy.context.scene.use_anti_recursion

        if use_anti_recursion:
            # Создаем узел Realize Instances для финального выхода
            final_realize = nodes.new('GeometryNodeRealizeInstances')
            final_realize.name = "Final Realize Instances"
            final_realize.location = (600, 0)

            # Создаем узел Switch для финального выхода
            final_switch = nodes.new('GeometryNodeSwitch')
            final_switch.input_type = 'GEOMETRY'
            final_switch.name = "Final Realize Switch"
            final_switch.location = (700, 0)

            # Соединяем трансформ с финальным Realize Instances
            links.new(transform.outputs['Geometry'], final_realize.inputs['Geometry'])

            # Настраиваем финальный переключатель
            if 'Realize Instances' in group_in.outputs:
                links.new(group_in.outputs['Realize Instances'], final_switch.inputs['Switch'])
            else:
                final_switch.inputs['Switch'].default_value = False

            links.new(transform.outputs['Geometry'], final_switch.inputs[False])  # Обычный выход
            links.new(final_realize.outputs['Geometry'], final_switch.inputs[True])  # "Реализованный" выход

            # Соединяем выход переключателя с выходом группы
            links.new(final_switch.outputs[0], group_out.inputs['Geometry'])
        else:
            # Если анти-рекурсия выключена, просто соединяем трансформ с выходом
            links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

        print(f"Grid клонер создан успешно с параметрами: Count X={count_x_socket.default_value}, Count Y={count_y_socket.default_value}, Count Z={count_z_socket.default_value}")

    elif cloner_type == "CIRCLE":
        count_socket = node_group.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_socket.default_value = 8

        radius_socket = node_group.interface.new_socket("Radius", in_out='INPUT', socket_type='NodeSocketFloat')
        radius_socket.default_value = 5.0

    # Добавляем общие сокеты
    rotation_socket = node_group.interface.new_socket("Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
    rotation_socket.default_value = (0.0, 0.0, 0.0)
    rotation_socket.subtype = 'EULER'

    scale_socket = node_group.interface.new_socket("Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')
    scale_socket.default_value = (1.0, 1.0, 1.0)

    # Global transform
    global_pos_socket = node_group.interface.new_socket("Global Position", in_out='INPUT', socket_type='NodeSocketVector')
    global_pos_socket.default_value = (0.0, 0.0, 0.0)

    global_rot_socket = node_group.interface.new_socket("Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
    global_rot_socket.default_value = (0.0, 0.0, 0.0)
    global_rot_socket.subtype = 'EULER'

    # Random parameters
    random_seed_socket = node_group.interface.new_socket("Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
    random_seed_socket.default_value = 0

    random_pos_socket = node_group.interface.new_socket("Random Position", in_out='INPUT', socket_type='NodeSocketVector')
    random_pos_socket.default_value = (0.0, 0.0, 0.0)

    random_rot_socket = node_group.interface.new_socket("Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
    random_rot_socket.default_value = (0.0, 0.0, 0.0)

    random_scale_socket = node_group.interface.new_socket("Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    random_scale_socket.default_value = 0.0

    # Extra options
    center_grid_socket = node_group.interface.new_socket("Center Grid", in_out='INPUT', socket_type='NodeSocketBool')
    center_grid_socket.default_value = True

    pick_instance_socket = node_group.interface.new_socket("Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
    pick_instance_socket.default_value = False

    # Add parameter for enabling/disabling instance realization only if anti-recursion is enabled
    use_anti_recursion = False
    if hasattr(bpy.context.scene, "use_anti_recursion"):
        use_anti_recursion = bpy.context.scene.use_anti_recursion

    if use_anti_recursion:
        realize_instances_input = node_group.interface.new_socket(name="Realize Instances", in_out='INPUT', socket_type='NodeSocketBool')
        realize_instances_input.default_value = use_anti_recursion
        realize_instances_input.description = "Enable to prevent recursion depth issues when creating chains of cloners"

    # Построение основной структуры узлов
    nodes = node_group.nodes
    links = node_group.links

    # Группы ввода/вывода
    group_in = nodes.new('NodeGroupInput')
    group_out = nodes.new('NodeGroupOutput')
    group_in.location = (-800, 0)
    group_out.location = (800, 0)

    # Узел для получения инстансов объекта
    object_info = nodes.new('GeometryNodeObjectInfo')
    object_info.transform_space = 'RELATIVE'
    if hasattr(object_info, 'instance_mode'):
        object_info.instance_mode = True
    object_info.location = (-600, 200)

    # Устанавливаем оригинальный объект как источник
    object_info.inputs['Object'].default_value = orig_obj

    # Определяем сокет вывода для разных версий Blender
    output_socket = 'Instances' if 'Instances' in object_info.outputs else 'Geometry'

    # Создаем узлы в зависимости от типа клонера
    if cloner_type == "LINEAR":
        # Создаем узлы для линейного клонера
        line_node = nodes.new('GeometryNodeMeshLine')
        if hasattr(line_node, "mode"):
            line_node.mode = 'OFFSET'
        if hasattr(line_node, "count_mode"):
            line_node.count_mode = 'TOTAL'
        line_node.location = (-400, 200)

        # Выводим доступные входы для отладки
        print("Available inputs for MeshLine node:")
        for input_name in line_node.inputs.keys():
            print(f"  - {input_name}")

        # Соединяем параметры Count и Offset
        links.new(group_in.outputs['Count'], line_node.inputs['Count'])

        # Используем универсальный подход для подключения вектора смещения
        offset_input = None
        for name in ['Offset', 'End Point', 'Length']:
            if name in line_node.inputs:
                offset_input = name
                print(f"Using '{offset_input}' as offset input for MeshLine")
                break

        if offset_input:
            links.new(group_in.outputs['Offset'], line_node.inputs[offset_input])
        else:
            print("WARNING: Could not find appropriate offset input for MeshLine.")

        # Преобразуем меш в точки
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.location = (-200, 200)
        links.new(line_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

        # Инстансирование на точках
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        instance_on_points.location = (0, 200)
        links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
        links.new(object_info.outputs[output_socket], instance_on_points.inputs['Instance'])
        links.new(group_in.outputs['Instance Rotation'], instance_on_points.inputs['Rotation'])
        links.new(group_in.outputs['Instance Scale'], instance_on_points.inputs['Scale'])

        # Используем специальные ноды FunctionNodeRandomValue для случайных значений
        # Добавляем индексы для случайных значений
        index_node = nodes.new('GeometryNodeInputIndex')
        index_node.location = (-300, -100)

        # Случайная позиция
        random_pos_node = nodes.new('FunctionNodeRandomValue')
        random_pos_node.data_type = 'FLOAT_VECTOR'
        random_pos_node.location = (-200, -150)

        # Настраиваем диапазон для случайных позиций
        vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_pos.operation = 'MULTIPLY'
        vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_pos.location = (-300, -150)
        links.new(group_in.outputs['Random Position'], vector_math_neg_pos.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_pos_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_pos_node.inputs['ID'])
        links.new(vector_math_neg_pos.outputs['Vector'], random_pos_node.inputs['Min'])
        links.new(group_in.outputs['Random Position'], random_pos_node.inputs['Max'])

        # Случайное вращение
        random_rot_node = nodes.new('FunctionNodeRandomValue')
        random_rot_node.data_type = 'FLOAT_VECTOR'
        random_rot_node.location = (-200, -250)

        # Настраиваем диапазон для случайных вращений
        vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_rot.operation = 'MULTIPLY'
        vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_rot.location = (-300, -250)
        links.new(group_in.outputs['Random Rotation'], vector_math_neg_rot.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_rot_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_rot_node.inputs['ID'])
        links.new(vector_math_neg_rot.outputs['Vector'], random_rot_node.inputs['Min'])
        links.new(group_in.outputs['Random Rotation'], random_rot_node.inputs['Max'])

        # Случайный масштаб
        random_scale_node = nodes.new('FunctionNodeRandomValue')
        random_scale_node.data_type = 'FLOAT'  # Единое значение для равномерного масштабирования
        random_scale_node.location = (-200, -350)

        # Настраиваем диапазон для случайного масштаба
        math_neg_scale = nodes.new('ShaderNodeMath')
        math_neg_scale.operation = 'MULTIPLY'
        math_neg_scale.inputs[1].default_value = -1.0
        math_neg_scale.location = (-300, -350)
        links.new(group_in.outputs['Random Scale'], math_neg_scale.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_scale_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_scale_node.inputs['ID'])
        links.new(math_neg_scale.outputs['Value'], random_scale_node.inputs['Min'])
        links.new(group_in.outputs['Random Scale'], random_scale_node.inputs['Max'])

        # Создаем узлы для преобразования случайного масштаба в вектор
        combine_scale = nodes.new('ShaderNodeCombineXYZ')
        combine_scale.location = (100, -350)
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['X'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Y'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Z'])

        # Создаем узел для комбинирования базового и случайного масштаба
        add_random_scale = nodes.new('ShaderNodeVectorMath')
        add_random_scale.operation = 'ADD'
        add_random_scale.location = (150, -300)
        links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
        links.new(combine_scale.outputs[0], add_random_scale.inputs[1])

        # Создаем узел для комбинирования базового и случайного вращения
        add_random_rotation = nodes.new('ShaderNodeVectorMath')
        add_random_rotation.operation = 'ADD'
        add_random_rotation.location = (150, -200)
        links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
        links.new(random_rot_node.outputs['Value'], add_random_rotation.inputs[1])

        # Применяем трансформации к инстансам
        # 1. Случайные позиции
        translate_instances = nodes.new('GeometryNodeTranslateInstances')
        translate_instances.location = (100, 200)

        # Выбираем правильный источник инстансов для трансформации
        if has_z_instances:
            # Если у нас есть 3D-инстансы для Grid клонера, используем их
            links.new(instances_on_z.outputs['Instances'], translate_instances.inputs['Instances'])
        else:
            # В противном случае используем обычные инстансы
            links.new(instance_on_points.outputs['Instances'], translate_instances.inputs['Instances'])

        links.new(random_pos_node.outputs['Value'], translate_instances.inputs['Translation'])

        # 2. Применяем вращение (базовое + случайное)
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        rotate_instances.location = (200, 200)
        links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
        links.new(add_random_rotation.outputs['Vector'], rotate_instances.inputs['Rotation'])

        # 3. Применяем масштаб (базовый + случайный)
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        scale_instances.location = (300, 200)
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
        links.new(add_random_scale.outputs['Vector'], scale_instances.inputs['Scale'])

        # Добавляем глобальные трансформации
        transform = nodes.new('GeometryNodeTransform')
        transform.location = (400, 200)
        links.new(scale_instances.outputs['Instances'], transform.inputs['Geometry'])
        links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
        links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

        # Не создаем узлы анти-рекурсии здесь - они будут созданы в конце функции
        # для обеспечения совместимости с эффекторами
        links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

    elif cloner_type == "GRID":
        # Создаем узлы для сетки точек
        grid_node = nodes.new('GeometryNodeMeshGrid')
        grid_node.location = (-400, 200)

        # Выводим доступные входы для отладки
        print("Available inputs for MeshGrid node:")
        for input_name in grid_node.inputs.keys():
            print(f"  - {input_name}")

        # Соединяем сокеты группы с узлами сетки
        links.new(group_in.outputs['Count X'], grid_node.inputs['Vertices X'])
        links.new(group_in.outputs['Count Y'], grid_node.inputs['Vertices Y'])

        # Создаем узел для разделения вектора spacing на компоненты
        separate_xyz = nodes.new('ShaderNodeSeparateXYZ')
        separate_xyz.location = (-600, -100)
        links.new(group_in.outputs['Spacing'], separate_xyz.inputs['Vector'])

        # Узлы для вычисления размеров
        math_x = nodes.new('ShaderNodeMath')
        math_x.location = (-500, -50)
        math_x.operation = 'MULTIPLY'

        math_y = nodes.new('ShaderNodeMath')
        math_y.location = (-500, -150)
        math_y.operation = 'MULTIPLY'

        # Соединяем расчеты
        links.new(group_in.outputs['Count X'], math_x.inputs[0])
        links.new(separate_xyz.outputs['X'], math_x.inputs[1])

        links.new(group_in.outputs['Count Y'], math_y.inputs[0])
        links.new(separate_xyz.outputs['Y'], math_y.inputs[1])

        # Находим правильные входы для размеров
        size_x_name = None
        size_y_name = None

        for name in ['Size X', 'Width']:
            if name in grid_node.inputs:
                size_x_name = name
                break

        for name in ['Size Y', 'Height']:
            if name in grid_node.inputs:
                size_y_name = name
                break

        if size_x_name and size_y_name:
            print(f"Using '{size_x_name}' and '{size_y_name}' as size inputs for MeshGrid")
            links.new(math_x.outputs[0], grid_node.inputs[size_x_name])
            links.new(math_y.outputs[0], grid_node.inputs[size_y_name])
        else:
            print("WARNING: Could not find appropriate size inputs for MeshGrid")

        # Преобразуем сетку в точки для базового использования
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.location = (-200, 200)
        links.new(grid_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

        # Инстансирование на точках
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        instance_on_points.location = (0, 200)

        # Соединяем узлы с точками, а не с мешем!
        links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
        links.new(object_info.outputs[output_socket], instance_on_points.inputs['Instance'])

        # Соединяем параметры трансформации
        links.new(group_in.outputs['Instance Rotation'], instance_on_points.inputs['Rotation'])
        links.new(group_in.outputs['Instance Scale'], instance_on_points.inputs['Scale'])

        # Объявляем переменные на уровне функции, а не внутри if-блока
        has_count_z = 'Count Z' in group_in.outputs
        has_z_instances = False
        instances_on_z = None  # Добавляем переменную на уровне функции

        if has_count_z and group_in.outputs['Count Z'].default_value > 1:
            # Создаем линию точек по оси Z
            line_z = nodes.new('GeometryNodeMeshLine')
            line_z.name = "Z Points Line"
            if hasattr(line_z, "mode"):
                line_z.mode = 'OFFSET'
            if hasattr(line_z, "count_mode"):
                line_z.count_mode = 'TOTAL'
            line_z.location = (-400, -300)

            # Подключаем число точек
            links.new(group_in.outputs['Count Z'], line_z.inputs['Count'])

            # Создаем вектор смещения для Z (0, 0, Spacing Z)
            combine_z_offset = nodes.new('ShaderNodeCombineXYZ')
            combine_z_offset.location = (-500, -300)
            combine_z_offset.inputs['X'].default_value = 0.0
            combine_z_offset.inputs['Y'].default_value = 0.0
            links.new(separate_xyz.outputs['Z'], combine_z_offset.inputs['Z'])

            # Подключаем смещение
            if "Offset" in line_z.inputs:
                links.new(combine_z_offset.outputs['Vector'], line_z.inputs['Offset'])
                print("Подключен вектор смещения к линии Z")

            # Преобразуем линию Z в точки
            line_z_to_points = nodes.new('GeometryNodeMeshToPoints')
            line_z_to_points.location = (-300, -300)
            links.new(line_z.outputs['Mesh'], line_z_to_points.inputs['Mesh'])

            # Инстансируем сетку на линии Z
            instances_on_z = nodes.new('GeometryNodeInstanceOnPoints')
            instances_on_z.location = (-200, -300)

            # Соединяем точки Z с инстансами
            links.new(line_z_to_points.outputs['Points'], instances_on_z.inputs['Points'])
            links.new(instance_on_points.outputs['Instances'], instances_on_z.inputs['Instance'])

            # Подключаем параметры трансформации к z-инстансам
            links.new(group_in.outputs['Instance Rotation'], instances_on_z.inputs['Rotation'])
            links.new(group_in.outputs['Instance Scale'], instances_on_z.inputs['Scale'])

            has_z_instances = True

        # Добавляем индексы для случайных значений
        index_node = nodes.new('GeometryNodeInputIndex')
        index_node.location = (-300, -100)

        # Случайная позиция
        random_pos_node = nodes.new('FunctionNodeRandomValue')
        random_pos_node.data_type = 'FLOAT_VECTOR'
        random_pos_node.location = (-200, -150)

        # Настраиваем диапазон для случайных позиций
        vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_pos.operation = 'MULTIPLY'
        vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_pos.location = (-300, -150)
        links.new(group_in.outputs['Random Position'], vector_math_neg_pos.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_pos_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_pos_node.inputs['ID'])
        links.new(vector_math_neg_pos.outputs['Vector'], random_pos_node.inputs['Min'])
        links.new(group_in.outputs['Random Position'], random_pos_node.inputs['Max'])

        # Случайное вращение
        random_rot_node = nodes.new('FunctionNodeRandomValue')
        random_rot_node.data_type = 'FLOAT_VECTOR'
        random_rot_node.location = (-200, -250)

        # Настраиваем диапазон для случайных вращений
        vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_rot.operation = 'MULTIPLY'
        vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_rot.location = (-300, -250)
        links.new(group_in.outputs['Random Rotation'], vector_math_neg_rot.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_rot_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_rot_node.inputs['ID'])
        links.new(vector_math_neg_rot.outputs['Vector'], random_rot_node.inputs['Min'])
        links.new(group_in.outputs['Random Rotation'], random_rot_node.inputs['Max'])

        # Случайный масштаб
        random_scale_node = nodes.new('FunctionNodeRandomValue')
        random_scale_node.data_type = 'FLOAT'  # Единое значение для равномерного масштабирования
        random_scale_node.location = (-200, -350)

        # Настраиваем диапазон для случайного масштаба
        math_neg_scale = nodes.new('ShaderNodeMath')
        math_neg_scale.operation = 'MULTIPLY'
        math_neg_scale.inputs[1].default_value = -1.0
        math_neg_scale.location = (-300, -350)
        links.new(group_in.outputs['Random Scale'], math_neg_scale.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_scale_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_scale_node.inputs['ID'])
        links.new(math_neg_scale.outputs['Value'], random_scale_node.inputs['Min'])
        links.new(group_in.outputs['Random Scale'], random_scale_node.inputs['Max'])

        # Создаем узлы для преобразования случайного масштаба в вектор
        combine_scale = nodes.new('ShaderNodeCombineXYZ')
        combine_scale.location = (100, -350)
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['X'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Y'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Z'])

        # Создаем узел для комбинирования базового и случайного масштаба
        add_random_scale = nodes.new('ShaderNodeVectorMath')
        add_random_scale.operation = 'ADD'
        add_random_scale.location = (150, -300)
        links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
        links.new(combine_scale.outputs[0], add_random_scale.inputs[1])

        # Создаем узел для комбинирования базового и случайного вращения
        add_random_rotation = nodes.new('ShaderNodeVectorMath')
        add_random_rotation.operation = 'ADD'
        add_random_rotation.location = (150, -200)
        links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
        links.new(random_rot_node.outputs['Value'], add_random_rotation.inputs[1])

        # Применяем трансформации к инстансам
        # 1. Случайные позиции
        translate_instances = nodes.new('GeometryNodeTranslateInstances')
        translate_instances.location = (100, 200)

        # Выбираем правильный источник инстансов для трансформации
        if has_z_instances:
            # Если у нас есть 3D-инстансы для Grid клонера, используем их
            links.new(instances_on_z.outputs['Instances'], translate_instances.inputs['Instances'])
            print("Подключены 3D инстансы для Grid Cloner")
        else:
            # В противном случае используем обычные инстансы
            links.new(instance_on_points.outputs['Instances'], translate_instances.inputs['Instances'])
            print("Подключены 2D инстансы для Grid Cloner")

        links.new(random_pos_node.outputs['Value'], translate_instances.inputs['Translation'])

        # 2. Применяем вращение (базовое + случайное)
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        rotate_instances.location = (200, 200)
        links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
        links.new(add_random_rotation.outputs['Vector'], rotate_instances.inputs['Rotation'])

        # 3. Применяем масштаб (базовый + случайный)
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        scale_instances.location = (300, 200)
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
        links.new(add_random_scale.outputs['Vector'], scale_instances.inputs['Scale'])

        # Добавляем глобальные трансформации
        transform = nodes.new('GeometryNodeTransform')
        transform.location = (400, 200)
        links.new(scale_instances.outputs['Instances'], transform.inputs['Geometry'])
        links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
        links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

        # Не создаем узлы анти-рекурсии здесь - они будут созданы в конце функции
        # для обеспечения совместимости с эффекторами
        links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

        # Добавляем диагностические сообщения для отладки
        if has_z_instances and instances_on_z is not None:
            print(f"Создана 3D сетка с параметрами: Count X={count_x_socket.default_value}, Count Y={count_y_socket.default_value}, Count Z={count_z_socket.default_value}")
        else:
            print(f"Создана 2D сетка с параметрами: Count X={count_x_socket.default_value}, Count Y={count_y_socket.default_value}")

    elif cloner_type == "CIRCLE":
        # Создаем узлы для окружности
        circle_node = nodes.new('GeometryNodeMeshCircle')
        circle_node.location = (-400, 200)

        # Выводим доступные входы для отладки
        print("Available inputs for MeshCircle node:")
        for input_name in circle_node.inputs.keys():
            print(f"  - {input_name}")

        # Соединяем сокеты группы с узлами
        links.new(group_in.outputs['Count'], circle_node.inputs['Vertices'])
        links.new(group_in.outputs['Radius'], circle_node.inputs['Radius'])

        # Преобразуем меш в точки
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.location = (-200, 200)
        links.new(circle_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

        # Инстансирование на точках
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        instance_on_points.location = (0, 200)
        links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
        links.new(object_info.outputs[output_socket], instance_on_points.inputs['Instance'])
        links.new(group_in.outputs['Instance Rotation'], instance_on_points.inputs['Rotation'])
        links.new(group_in.outputs['Instance Scale'], instance_on_points.inputs['Scale'])

        # Используем специальные ноды FunctionNodeRandomValue для случайных значений
        # Добавляем индексы для случайных значений
        index_node = nodes.new('GeometryNodeInputIndex')
        index_node.location = (-300, -100)

        # Случайная позиция
        random_pos_node = nodes.new('FunctionNodeRandomValue')
        random_pos_node.data_type = 'FLOAT_VECTOR'
        random_pos_node.location = (-200, -150)

        # Настраиваем диапазон для случайных позиций
        vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_pos.operation = 'MULTIPLY'
        vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_pos.location = (-300, -150)
        links.new(group_in.outputs['Random Position'], vector_math_neg_pos.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_pos_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_pos_node.inputs['ID'])
        links.new(vector_math_neg_pos.outputs['Vector'], random_pos_node.inputs['Min'])
        links.new(group_in.outputs['Random Position'], random_pos_node.inputs['Max'])

        # Случайное вращение
        random_rot_node = nodes.new('FunctionNodeRandomValue')
        random_rot_node.data_type = 'FLOAT_VECTOR'
        random_rot_node.location = (-200, -250)

        # Настраиваем диапазон для случайных вращений
        vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_rot.operation = 'MULTIPLY'
        vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
        vector_math_neg_rot.location = (-300, -250)
        links.new(group_in.outputs['Random Rotation'], vector_math_neg_rot.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_rot_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_rot_node.inputs['ID'])
        links.new(vector_math_neg_rot.outputs['Vector'], random_rot_node.inputs['Min'])
        links.new(group_in.outputs['Random Rotation'], random_rot_node.inputs['Max'])

        # Случайный масштаб
        random_scale_node = nodes.new('FunctionNodeRandomValue')
        random_scale_node.data_type = 'FLOAT'  # Единое значение для равномерного масштабирования
        random_scale_node.location = (-200, -350)

        # Настраиваем диапазон для случайного масштаба
        math_neg_scale = nodes.new('ShaderNodeMath')
        math_neg_scale.operation = 'MULTIPLY'
        math_neg_scale.inputs[1].default_value = -1.0
        math_neg_scale.location = (-300, -350)
        links.new(group_in.outputs['Random Scale'], math_neg_scale.inputs[0])

        # Соединяем с нодой случайных значений
        links.new(group_in.outputs['Random Seed'], random_scale_node.inputs['Seed'])
        links.new(index_node.outputs['Index'], random_scale_node.inputs['ID'])
        links.new(math_neg_scale.outputs['Value'], random_scale_node.inputs['Min'])
        links.new(group_in.outputs['Random Scale'], random_scale_node.inputs['Max'])

        # Создаем узлы для преобразования случайного масштаба в вектор
        combine_scale = nodes.new('ShaderNodeCombineXYZ')
        combine_scale.location = (100, -350)
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['X'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Y'])
        links.new(random_scale_node.outputs['Value'], combine_scale.inputs['Z'])

        # Создаем узел для комбинирования базового и случайного масштаба
        add_random_scale = nodes.new('ShaderNodeVectorMath')
        add_random_scale.operation = 'ADD'
        add_random_scale.location = (150, -300)
        links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
        links.new(combine_scale.outputs[0], add_random_scale.inputs[1])

        # Создаем узел для комбинирования базового и случайного вращения
        add_random_rotation = nodes.new('ShaderNodeVectorMath')
        add_random_rotation.operation = 'ADD'
        add_random_rotation.location = (150, -200)
        links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
        links.new(random_rot_node.outputs['Value'], add_random_rotation.inputs[1])

        # Применяем трансформации к инстансам
        # 1. Случайные позиции
        translate_instances = nodes.new('GeometryNodeTranslateInstances')
        translate_instances.location = (100, 200)
        links.new(instance_on_points.outputs['Instances'], translate_instances.inputs['Instances'])
        links.new(random_pos_node.outputs['Value'], translate_instances.inputs['Translation'])

        # 2. Применяем вращение (базовое + случайное)
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        rotate_instances.location = (200, 200)
        links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
        links.new(add_random_rotation.outputs['Vector'], rotate_instances.inputs['Rotation'])

        # 3. Применяем масштаб (базовый + случайный)
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        scale_instances.location = (300, 200)
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
        links.new(add_random_scale.outputs['Vector'], scale_instances.inputs['Scale'])

        # Добавляем глобальные трансформации
        transform = nodes.new('GeometryNodeTransform')
        transform.location = (400, 200)
        links.new(scale_instances.outputs['Instances'], transform.inputs['Geometry'])
        links.new(group_in.outputs['Global Position'], transform.inputs['Translation'])
        links.new(group_in.outputs['Global Rotation'], transform.inputs['Rotation'])

        # Не создаем узлы анти-рекурсии здесь - они будут созданы в конце функции
        # для обеспечения совместимости с эффекторами
        links.new(transform.outputs['Geometry'], group_out.inputs['Geometry'])

    # Удаляем заглушку прямого соединения
    for link in list(links):
        if link.from_socket == object_info.outputs[output_socket] and link.to_socket == group_out.inputs['Geometry']:
            links.remove(link)

    # Находим узел, который подключен к выходу
    output_node = None
    output_socket_name = None
    for link in links:
        if link.to_node == group_out and link.to_socket.name == 'Geometry':
            output_node = link.from_node
            output_socket_name = link.from_socket.name
            links.remove(link)
            break

    if output_node:
        # Проверяем, включена ли опция анти-рекурсии
        use_anti_recursion = False
        if hasattr(bpy.context.scene, "use_anti_recursion"):
            use_anti_recursion = bpy.context.scene.use_anti_recursion

        # Всегда создаем узлы для поддержки эффекторов, но используем их по-разному
        # в зависимости от настройки анти-рекурсии

        # Создаем специальный узел для подключения эффекторов
        effector_input_node = nodes.new('GeometryNodeGroup')
        effector_input_node.name = "Effector_Input"
        effector_input_node.location = (output_node.location.x + 50, output_node.location.y - 150)

        # Создаем пустую группу узлов для этого узла
        if not bpy.data.node_groups.get("EffectorInputGroup"):
            effector_group = bpy.data.node_groups.new(name="EffectorInputGroup", type='GeometryNodeTree')
            # Создаем входы и выходы
            effector_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
            effector_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

            # Создаем узлы внутри группы
            group_in_node = effector_group.nodes.new('NodeGroupInput')
            group_out_node = effector_group.nodes.new('NodeGroupOutput')
            group_in_node.location = (-200, 0)
            group_out_node.location = (200, 0)

            # Соединяем вход с выходом
            effector_group.links.new(group_in_node.outputs['Geometry'], group_out_node.inputs['Geometry'])

        # Устанавливаем группу узлов
        effector_input_node.node_tree = bpy.data.node_groups.get("EffectorInputGroup")

        if use_anti_recursion:
            # Создаем узел Realize Instances для финального выхода
            final_realize = nodes.new('GeometryNodeRealizeInstances')
            final_realize.name = "Final Realize Instances"
            final_realize.location = (output_node.location.x + 100, output_node.location.y)

            # Создаем узел Switch для финального выхода (используем имя, которое ищут эффекторы)
            switch_node = nodes.new('GeometryNodeSwitch')
            switch_node.input_type = 'GEOMETRY'
            switch_node.name = "Final Realize Switch"
            switch_node.location = (output_node.location.x + 200, output_node.location.y)

            # Соединяем трансформ с финальным Realize Instances
            links.new(output_node.outputs[output_socket_name], final_realize.inputs['Geometry'])

            # Настраиваем финальный переключатель
            if 'Realize Instances' in group_in.outputs:
                links.new(group_in.outputs['Realize Instances'], switch_node.inputs['Switch'])
            else:
                switch_node.inputs['Switch'].default_value = use_anti_recursion

            links.new(output_node.outputs[output_socket_name], switch_node.inputs[False])  # Обычный выход
            links.new(final_realize.outputs['Geometry'], switch_node.inputs[True])  # "Реализованный" выход

            # Соединяем переключатель с выходом
            links.new(switch_node.outputs[0], group_out.inputs['Geometry'])
        else:
            # Если анти-рекурсия выключена, создаем простой Switch узел для совместимости с эффекторами
            switch_node = nodes.new('GeometryNodeSwitch')
            switch_node.input_type = 'GEOMETRY'
            switch_node.name = "Final Realize Switch"  # Используем то же имя для совместимости
            switch_node.location = (output_node.location.x + 200, output_node.location.y)

            # Устанавливаем Switch в режим False (без анти-рекурсии)
            switch_node.inputs['Switch'].default_value = False

            # Подключаем исходный узел к обоим входам Switch (False и True одинаковы)
            links.new(output_node.outputs[output_socket_name], switch_node.inputs[False])
            links.new(output_node.outputs[output_socket_name], switch_node.inputs[True])

            # Соединяем переключатель с выходом
            links.new(switch_node.outputs[0], group_out.inputs['Geometry'])

    # Возвращаем созданный node_group
    return node_group