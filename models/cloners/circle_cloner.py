import bpy
import math
from .base import ClonerBase

class CircleCloner(ClonerBase):
    """Circle Cloner implementation"""

    @classmethod
    def create_logic_group(cls, name_suffix=""):
        """Create a node group with the core circle cloner logic"""

        # Create new node group
        logic_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"CircleClonerLogic{name_suffix}")

        # --- Interface ---
        # Output
        logic_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # Changed: Removed direct Geometry input, added Instance Source input
        logic_group.interface.new_socket(name="Instance Source", in_out='INPUT', socket_type='NodeSocketGeometry')

        # Basic Settings
        count_input = logic_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_input.default_value = 8
        count_input.min_value = 3
        count_input.max_value = 1000

        radius_input = logic_group.interface.new_socket(name="Radius", in_out='INPUT', socket_type='NodeSocketFloat')
        radius_input.default_value = 1.0
        radius_input.min_value = 0.0

        height_input = logic_group.interface.new_socket(name="Height", in_out='INPUT', socket_type='NodeSocketFloat')
        height_input.default_value = 0.0

        # Instance Transform Settings
        scale_input = logic_group.interface.new_socket(name="Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')
        scale_input.default_value = (1.0, 1.0, 1.0)

        rotation_input = logic_group.interface.new_socket(name="Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_input.default_value = (0.0, 0.0, 0.0)
        rotation_input.subtype = 'EULER'

        # Random Settings
        random_position_input = logic_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_position_input.default_value = (0.0, 0.0, 0.0)

        random_rotation_input = logic_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rotation_input.default_value = (0.0, 0.0, 0.0)
        random_rotation_input.subtype = 'EULER'

        random_scale_input = logic_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0
        random_scale_input.min_value = 0.0
        random_scale_input.max_value = 1.0

        seed_input = logic_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0

        # Instance Collection options
        pick_instance_input = logic_group.interface.new_socket(name="Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
        pick_instance_input.default_value = False

        # --- Nodes ---
        nodes = logic_group.nodes
        links = logic_group.links

        group_input = nodes.new('NodeGroupInput')
        group_output = nodes.new('NodeGroupOutput')

        # Используем значения напрямую без множителей
        # Это позволит применять значения из конфигурации без дополнительных преобразований

        # Для обратной совместимости сохраняем ноды, но устанавливаем множитель 1.0
        radius_multiplier = nodes.new('ShaderNodeMath')
        radius_multiplier.operation = 'MULTIPLY'
        radius_multiplier.inputs[1].default_value = 1.0  # Множитель 1.0 (без изменений)
        links.new(group_input.outputs["Radius"], radius_multiplier.inputs[0])

        # Для высоты также используем множитель 1.0
        height_multiplier = nodes.new('ShaderNodeMath')
        height_multiplier.operation = 'MULTIPLY'
        height_multiplier.inputs[1].default_value = 1.0  # Множитель 1.0 (без изменений)
        links.new(group_input.outputs["Height"], height_multiplier.inputs[0])

        # --- 1. Создание базовых элементов ---
        # Создаем простую окружность
        mesh_circle = nodes.new('GeometryNodeMeshCircle')
        mesh_circle.fill_type = 'NONE'  # Только вершины окружности
        links.new(group_input.outputs["Count"], mesh_circle.inputs["Vertices"])
        links.new(radius_multiplier.outputs["Value"], mesh_circle.inputs["Radius"])

        # Преобразуем вершины в точки
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.mode = 'VERTICES'
        links.new(mesh_circle.outputs["Mesh"], mesh_to_points.inputs["Mesh"])

        # Устанавливаем высоту
        set_position = nodes.new('GeometryNodeSetPosition')
        combine_height = nodes.new('ShaderNodeCombineXYZ')
        combine_height.inputs[0].default_value = 0.0  # X остается без изменений
        combine_height.inputs[1].default_value = 0.0  # Y остается без изменений
        links.new(height_multiplier.outputs["Value"], combine_height.inputs[2])  # Z = Height * Multiplier

        links.new(mesh_to_points.outputs["Points"], set_position.inputs["Geometry"])
        links.new(combine_height.outputs["Vector"], set_position.inputs["Offset"])

        # --- 2. Инстансирование и базовые трансформации ---
        # Инстансируем объекты на точках
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')
        links.new(set_position.outputs["Geometry"], instance_on_points.inputs["Points"])

        # Changed: Connect Instance Source input
        links.new(group_input.outputs["Instance Source"], instance_on_points.inputs["Instance"])

        # Сначала создаем необходимые ноды для случайных значений
        index = nodes.new('GeometryNodeInputIndex')

        # --- Pick Random Instance Logic (if input is a collection) ---
        pick_instance_random = nodes.new('GeometryNodeInstanceOnPoints')
        pick_instance_random.name = "Pick Random Instance"

        # Random Index for picking instance
        random_instance_index = nodes.new('FunctionNodeRandomValue')
        random_instance_index.data_type = 'INT'
        links.new(group_input.outputs['Random Seed'], random_instance_index.inputs['Seed'])
        links.new(index.outputs['Index'], random_instance_index.inputs['ID'])
        links.new(set_position.outputs["Geometry"], pick_instance_random.inputs["Points"])

        # Changed: Connect Instance Source input
        links.new(group_input.outputs["Instance Source"], pick_instance_random.inputs["Instance"])

        # Switch between normal instancing and random pick instancing
        switch_instancing = nodes.new('GeometryNodeSwitch')
        switch_instancing.name = "Switch Instance Mode"
        switch_instancing.input_type = 'GEOMETRY'
        links.new(group_input.outputs['Pick Random Instance'], switch_instancing.inputs['Switch'])
        links.new(instance_on_points.outputs['Instances'], switch_instancing.inputs[False])
        links.new(pick_instance_random.outputs['Instances'], switch_instancing.inputs[True])

        # Поворачиваем к центру (лицом внутрь)
        # Добавляем угол поворота вокруг Z на 90 градусов по умолчанию
        face_center = nodes.new('GeometryNodeRotateInstances')
        combine_face_center = nodes.new('ShaderNodeCombineXYZ')
        combine_face_center.inputs[0].default_value = 0.0  # X
        combine_face_center.inputs[1].default_value = 0.0  # Y
        combine_face_center.inputs[2].default_value = 90.0  # Z - поворот на 90 градусов

        links.new(switch_instancing.outputs["Output"], face_center.inputs["Instances"])
        links.new(combine_face_center.outputs["Vector"], face_center.inputs["Rotation"])

        # Применяем пользовательское вращение
        rotate_user = nodes.new('GeometryNodeRotateInstances')
        links.new(face_center.outputs["Instances"], rotate_user.inputs["Instances"])
        links.new(group_input.outputs["Instance Rotation"], rotate_user.inputs["Rotation"])

        # Применяем масштаб
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        links.new(rotate_user.outputs["Instances"], scale_instances.inputs["Instances"])
        links.new(group_input.outputs["Instance Scale"], scale_instances.inputs["Scale"])

        # --- 3. Случайные трансформации ---
        # Случайная позиция
        random_position = nodes.new('FunctionNodeRandomValue')
        random_position.data_type = 'FLOAT_VECTOR'

        # Диапазон: от -Random Position до +Random Position
        vector_neg_pos = nodes.new('ShaderNodeVectorMath')
        vector_neg_pos.operation = 'MULTIPLY'
        vector_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)

        links.new(group_input.outputs["Random Position"], vector_neg_pos.inputs[0])
        links.new(vector_neg_pos.outputs["Vector"], random_position.inputs["Min"])
        links.new(group_input.outputs["Random Position"], random_position.inputs["Max"])
        links.new(group_input.outputs["Random Seed"], random_position.inputs["Seed"])
        links.new(index.outputs["Index"], random_position.inputs["ID"])

        # Случайное вращение
        random_rotation = nodes.new('FunctionNodeRandomValue')
        random_rotation.data_type = 'FLOAT_VECTOR'

        # Диапазон: от -Random Rotation до +Random Rotation
        vector_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_neg_rot.operation = 'MULTIPLY'
        vector_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)

        links.new(group_input.outputs["Random Rotation"], vector_neg_rot.inputs[0])
        links.new(vector_neg_rot.outputs["Vector"], random_rotation.inputs["Min"])
        links.new(group_input.outputs["Random Rotation"], random_rotation.inputs["Max"])
        links.new(group_input.outputs["Random Seed"], random_rotation.inputs["Seed"])
        links.new(index.outputs["Index"], random_rotation.inputs["ID"])

        # Случайный масштаб
        random_scale = nodes.new('FunctionNodeRandomValue')
        random_scale.data_type = 'FLOAT'

        # Диапазон: от -Random Scale до +Random Scale
        math_neg_scale = nodes.new('ShaderNodeMath')
        math_neg_scale.operation = 'MULTIPLY'
        math_neg_scale.inputs[1].default_value = -1.0

        links.new(group_input.outputs["Random Scale"], math_neg_scale.inputs[0])
        links.new(math_neg_scale.outputs["Value"], random_scale.inputs["Min"])
        links.new(group_input.outputs["Random Scale"], random_scale.inputs["Max"])
        links.new(group_input.outputs["Random Seed"], random_scale.inputs["Seed"])
        links.new(index.outputs["Index"], random_scale.inputs["ID"])

        # Преобразуем случайный масштаб из float в vector
        combine_random_scale = nodes.new('ShaderNodeCombineXYZ')
        links.new(random_scale.outputs["Value"], combine_random_scale.inputs[0])  # X
        links.new(random_scale.outputs["Value"], combine_random_scale.inputs[1])  # Y
        links.new(random_scale.outputs["Value"], combine_random_scale.inputs[2])  # Z

        # --- 4. Применяем случайные трансформации ---
        # Применяем случайную позицию
        translate_random = nodes.new('GeometryNodeTranslateInstances')
        links.new(scale_instances.outputs["Instances"], translate_random.inputs["Instances"])
        links.new(random_position.outputs["Value"], translate_random.inputs["Translation"])

        # Применяем случайное вращение
        rotate_random = nodes.new('GeometryNodeRotateInstances')
        links.new(translate_random.outputs["Instances"], rotate_random.inputs["Instances"])
        links.new(random_rotation.outputs["Value"], rotate_random.inputs["Rotation"])

        # Применяем случайный масштаб (1.0 + случайное значение)
        vector_add_scale = nodes.new('ShaderNodeVectorMath')
        vector_add_scale.operation = 'ADD'
        vector_add_scale.inputs[0].default_value = (1.0, 1.0, 1.0)

        links.new(combine_random_scale.outputs["Vector"], vector_add_scale.inputs[1])

        scale_random = nodes.new('GeometryNodeScaleInstances')
        links.new(rotate_random.outputs["Instances"], scale_random.inputs["Instances"])
        links.new(vector_add_scale.outputs["Vector"], scale_random.inputs["Scale"])

        # --- Final Output ---
        # Connect instances directly to output
        links.new(scale_random.outputs['Instances'], group_output.inputs['Geometry'])

        return logic_group

    @classmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Create a radial cloner node group similar to Cinema 4D's Radial Cloner"""

        # Create new node group for the main interface
        node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"CircleCloner{name_suffix}")

        # --- Interface for main group ---
        # Output
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # Changed: Replace Geometry input with Object input
        node_group.interface.new_socket(name="Object", in_out='INPUT', socket_type='NodeSocketObject')

        # Basic Settings
        count_input = node_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_input.default_value = 8
        count_input.min_value = 3
        count_input.max_value = 1000

        radius_input = node_group.interface.new_socket(name="Radius", in_out='INPUT', socket_type='NodeSocketFloat')
        radius_input.default_value = 1.0
        radius_input.min_value = 0.0

        height_input = node_group.interface.new_socket(name="Height", in_out='INPUT', socket_type='NodeSocketFloat')
        height_input.default_value = 0.0

        # Global Transform Settings
        global_position_input = node_group.interface.new_socket(name="Global Position", in_out='INPUT', socket_type='NodeSocketVector')
        global_position_input.default_value = (0.0, 0.0, 0.0)

        global_rotation_input = node_group.interface.new_socket(name="Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        global_rotation_input.default_value = (0.0, 0.0, 0.0)
        global_rotation_input.subtype = 'EULER'

        # Instance Transform Settings
        scale_input = node_group.interface.new_socket(name="Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')
        scale_input.default_value = (1.0, 1.0, 1.0)

        rotation_input = node_group.interface.new_socket(name="Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_input.default_value = (0.0, 0.0, 0.0)
        rotation_input.subtype = 'EULER'

        # Random Settings
        random_position_input = node_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_position_input.default_value = (0.0, 0.0, 0.0)

        random_rotation_input = node_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rotation_input.default_value = (0.0, 0.0, 0.0)
        random_rotation_input.subtype = 'EULER'

        random_scale_input = node_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0
        random_scale_input.min_value = 0.0
        random_scale_input.max_value = 1.0

        seed_input = node_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0

        # Instance Collection options
        pick_instance_input = node_group.interface.new_socket(name="Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
        pick_instance_input.default_value = False

        # --- Nodes ---
        nodes = node_group.nodes

        # Add group input and output
        group_input = nodes.new('NodeGroupInput')
        group_output = nodes.new('NodeGroupOutput')

        # Добавляем параметр для включения/выключения "реализации" инстансов
        realize_instances_input = node_group.interface.new_socket(name="Realize Instances", in_out='INPUT', socket_type='NodeSocketBool')
        realize_instances_input.default_value = False
        realize_instances_input.description = "Включите для предотвращения проблем с глубиной рекурсии при создании цепочек клонеров"

        # Используем улучшенный метод setup_instance_input_nodes из базового класса
        # Передаем параметр realize_instances для создания узла Realize Instances при необходимости
        object_info, instances_output = ClonerBase.setup_instance_input_nodes(
            nodes,
            links,
            group_input,
            realize_instances=False  # По умолчанию выключено, будет управляться через интерфейс
        )
        object_info.name = "Object Info"
        object_info.location = (-800, 0)

        # Create a node for the cloner logic subgroup
        cloner_logic_node = nodes.new('GeometryNodeGroup')
        cloner_logic_node.node_tree = logic_group
        cloner_logic_node.name = "Circle Cloner Logic"
        cloner_logic_node.location = (-400, 0)

        # Создаем узел Realize Instances, который будет включаться/выключаться
        realize_node = nodes.new('GeometryNodeRealizeInstances')
        realize_node.name = "Realize Instances (Anti-Recursion)"
        realize_node.location = (-600, 0)

        # Создаем узел Switch для переключения между обычным и "реализованным" потоком
        switch_realize = nodes.new('GeometryNodeSwitch')
        switch_realize.input_type = 'GEOMETRY'
        switch_realize.name = "Switch Realize Mode"
        switch_realize.location = (-500, 0)

        # Global transform
        global_transform = nodes.new('GeometryNodeTransform')
        global_transform.location = (0, 0)

        # Create links
        links = node_group.links

        # Соединяем выход инстансов с узлом Realize Instances
        links.new(instances_output, realize_node.inputs['Geometry'])

        # Настраиваем переключатель для выбора между обычными инстансами и "реализованными"
        links.new(group_input.outputs['Realize Instances'], switch_realize.inputs['Switch'])
        links.new(instances_output, switch_realize.inputs[False])  # Обычные инстансы
        links.new(realize_node.outputs['Geometry'], switch_realize.inputs[True])  # "Реализованные" инстансы

        # Соединяем выход переключателя с входом логики клонера
        links.new(switch_realize.outputs[0], cloner_logic_node.inputs['Instance Source'])
        print("Connected instance source with realize instances option to cloner logic")

        # Connect the main inputs to the logic subgroup
        links.new(group_input.outputs['Count'], cloner_logic_node.inputs['Count'])
        links.new(group_input.outputs['Radius'], cloner_logic_node.inputs['Radius'])
        links.new(group_input.outputs['Height'], cloner_logic_node.inputs['Height'])
        links.new(group_input.outputs['Instance Scale'], cloner_logic_node.inputs['Instance Scale'])
        links.new(group_input.outputs['Instance Rotation'], cloner_logic_node.inputs['Instance Rotation'])
        links.new(group_input.outputs['Random Position'], cloner_logic_node.inputs['Random Position'])
        links.new(group_input.outputs['Random Rotation'], cloner_logic_node.inputs['Random Rotation'])
        links.new(group_input.outputs['Random Scale'], cloner_logic_node.inputs['Random Scale'])
        links.new(group_input.outputs['Random Seed'], cloner_logic_node.inputs['Random Seed'])
        links.new(group_input.outputs['Pick Random Instance'], cloner_logic_node.inputs['Pick Random Instance'])

        # Apply Global Transform
        links.new(cloner_logic_node.outputs['Geometry'], global_transform.inputs['Geometry'])
        links.new(group_input.outputs['Global Position'], global_transform.inputs['Translation'])
        links.new(group_input.outputs['Global Rotation'], global_transform.inputs['Rotation'])

        # Создаем еще один узел Realize Instances для финального выхода
        # Это поможет предотвратить проблемы с глубиной рекурсии на выходе клонера
        final_realize = nodes.new('GeometryNodeRealizeInstances')
        final_realize.name = "Final Realize Instances"
        final_realize.location = (100, 0)

        # Создаем узел Switch для финального выхода
        final_switch = nodes.new('GeometryNodeSwitch')
        final_switch.input_type = 'GEOMETRY'
        final_switch.name = "Final Realize Switch"
        final_switch.location = (200, 0)

        # Соединяем глобальный трансформ с финальным Realize Instances
        links.new(global_transform.outputs['Geometry'], final_realize.inputs['Geometry'])

        # Настраиваем финальный переключатель
        links.new(group_input.outputs['Realize Instances'], final_switch.inputs['Switch'])
        links.new(global_transform.outputs['Geometry'], final_switch.inputs[False])  # Обычный выход
        links.new(final_realize.outputs['Geometry'], final_switch.inputs[True])  # "Реализованный" выход

        # Connect to output
        links.new(final_switch.outputs[0], group_output.inputs['Geometry'])

        return node_group

# Maintain backwards compatibility with the procedural interface
def create_circle_cloner_logic_group():
    return CircleCloner.create_logic_group()

def circlecloner_node_group():
    return CircleCloner.create_node_group()

def register():
    pass

def unregister():
    pass