import bpy
import mathutils
from .base import ClonerBase

class LinearCloner(ClonerBase):
    """Linear Cloner implementation"""

    @classmethod
    def create_logic_group(cls, name_suffix=""):
        """Create a node group with the core linear cloner logic"""

        # Create new node group
        logic_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"LinearClonerLogic{name_suffix}")

        # --- Interface ---
        # Output
        logic_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # Changed: Removed direct Geometry input, added Instance Source input
        logic_group.interface.new_socket(name="Instance Source", in_out='INPUT', socket_type='NodeSocketGeometry')

        # Basic Settings
        count_input = logic_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_input.default_value = 5
        count_input.min_value = 1
        count_input.max_value = 1000

        offset_input = logic_group.interface.new_socket(name="Offset", in_out='INPUT', socket_type='NodeSocketVector')
        offset_input.default_value = (1.0, 0.0, 0.0)

        # Scale Start/End Settings
        scale_start_input = logic_group.interface.new_socket(name="Scale Start", in_out='INPUT', socket_type='NodeSocketVector')
        scale_start_input.default_value = (1.0, 1.0, 1.0)

        scale_end_input = logic_group.interface.new_socket(name="Scale End", in_out='INPUT', socket_type='NodeSocketVector')
        scale_end_input.default_value = (1.0, 1.0, 1.0)

        # Rotation Start/End Settings
        rotation_start_input = logic_group.interface.new_socket(name="Rotation Start", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_start_input.default_value = (0.0, 0.0, 0.0)
        rotation_start_input.subtype = 'EULER'

        rotation_end_input = logic_group.interface.new_socket(name="Rotation End", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_end_input.default_value = (0.0, 0.0, 0.0)
        rotation_end_input.subtype = 'EULER'

        # Random Settings
        random_position_input = logic_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_position_input.default_value = (0.0, 0.0, 0.0)

        random_rotation_input = logic_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rotation_input.default_value = (0.0, 0.0, 0.0)

        random_scale_input = logic_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0
        random_scale_input.min_value = 0.0
        random_scale_input.max_value = 1.0

        seed_input = logic_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0
        seed_input.max_value = 10000

        # Switch between normal instancing and random pick
        pick_instance_input = logic_group.interface.new_socket(name="Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
        pick_instance_input.default_value = False

        # --- Nodes ---
        nodes = logic_group.nodes

        # Add group input and output
        group_input = nodes.new('NodeGroupInput')
        group_output = nodes.new('NodeGroupOutput')

        # Используем значения напрямую без множителей
        # Это позволит применять значения из конфигурации без дополнительных преобразований

        # Для обратной совместимости сохраняем ноды, но устанавливаем множитель 1.0
        offset_multiplier = nodes.new('ShaderNodeVectorMath')
        offset_multiplier.operation = 'MULTIPLY'
        offset_multiplier.inputs[1].default_value = (1.0, 1.0, 1.0)  # Множитель 1.0 (без изменений)
        links = logic_group.links
        links.new(group_input.outputs['Offset'], offset_multiplier.inputs[0])

        # Base cloner elements
        mesh_line = nodes.new('GeometryNodeMeshLine')
        mesh_line.mode = 'OFFSET'
        mesh_line.count_mode = 'TOTAL'

        # Instance on points
        instance_on_points = nodes.new('GeometryNodeInstanceOnPoints')

        # Interpolation setup for scale and rotation
        index = nodes.new('GeometryNodeInputIndex')
        math_subtract = nodes.new('ShaderNodeMath')
        math_subtract.operation = 'SUBTRACT'
        math_subtract.inputs[1].default_value = 1.0

        math_max = nodes.new('ShaderNodeMath')
        math_max.operation = 'MAXIMUM'
        math_max.inputs[1].default_value = 1.0

        math_divide = nodes.new('ShaderNodeMath')
        math_divide.operation = 'DIVIDE'

        # Map Range for factor (0-1)
        map_range = nodes.new('ShaderNodeMapRange')
        map_range.inputs['From Min'].default_value = 0.0
        map_range.inputs['From Max'].default_value = 1.0
        map_range.inputs['To Min'].default_value = 0.0
        map_range.inputs['To Max'].default_value = 1.0

        # Mix nodes for interpolation
        mix_scale = nodes.new('ShaderNodeMix')
        mix_scale.data_type = 'VECTOR'
        mix_scale.clamp_factor = True

        mix_rotation = nodes.new('ShaderNodeMix')
        mix_rotation.data_type = 'VECTOR'
        mix_rotation.clamp_factor = True

        # Random value nodes
        random_position = nodes.new('FunctionNodeRandomValue')
        random_position.data_type = 'FLOAT_VECTOR'

        random_rotation = nodes.new('FunctionNodeRandomValue')
        random_rotation.data_type = 'FLOAT_VECTOR'

        random_scale = nodes.new('FunctionNodeRandomValue')
        random_scale.data_type = 'FLOAT'

        # Vector math for negative ranges (to center the random range around 0)
        vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_pos.operation = 'MULTIPLY'
        vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)

        vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_rot.operation = 'MULTIPLY'
        vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)

        math_neg_scale = nodes.new('ShaderNodeMath')
        math_neg_scale.operation = 'MULTIPLY'
        math_neg_scale.inputs[1].default_value = -1.0

        # For combining random scale into vector
        combine_xyz_scale = nodes.new('ShaderNodeCombineXYZ')

        # Add vector math nodes
        add_random_rotation = nodes.new('ShaderNodeVectorMath')
        add_random_rotation.operation = 'ADD'

        add_random_scale = nodes.new('ShaderNodeVectorMath')
        add_random_scale.operation = 'ADD'

        # --- Pick Random Instance Logic ---
        pick_instance_random = nodes.new('GeometryNodeInstanceOnPoints')
        pick_instance_random.name = "Pick Random Instance"

        # Random Index for picking instance
        random_instance_index = nodes.new('FunctionNodeRandomValue')
        random_instance_index.data_type = 'INT'

        # Switch between normal instancing and random pick instancing
        switch_instancing = nodes.new('GeometryNodeSwitch')
        switch_instancing.name = "Switch Instance Mode"
        switch_instancing.input_type = 'GEOMETRY'

        # Transform instances
        set_position = nodes.new('GeometryNodeSetPosition')
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        scale_instances = nodes.new('GeometryNodeScaleInstances')

        # Create links
        links = logic_group.links

        # Basic cloning setup
        links.new(group_input.outputs['Count'], mesh_line.inputs['Count'])
        links.new(offset_multiplier.outputs['Vector'], mesh_line.inputs['Offset'])
        links.new(mesh_line.outputs['Mesh'], instance_on_points.inputs['Points'])

        # Changed: Connect Instance Source input
        links.new(group_input.outputs['Instance Source'], instance_on_points.inputs['Instance'])

        # Pick random instance setup
        links.new(group_input.outputs['Random Seed'], random_instance_index.inputs['Seed'])
        links.new(index.outputs['Index'], random_instance_index.inputs['ID'])
        links.new(mesh_line.outputs['Mesh'], pick_instance_random.inputs['Points'])

        # Changed: Connect Instance Source input
        links.new(group_input.outputs['Instance Source'], pick_instance_random.inputs['Instance'])

        # Calculate interpolation factor
        links.new(index.outputs['Index'], math_divide.inputs[0])
        links.new(group_input.outputs['Count'], math_subtract.inputs[0])
        links.new(math_subtract.outputs['Value'], math_max.inputs[0])
        links.new(math_max.outputs['Value'], math_divide.inputs[1])
        links.new(math_divide.outputs['Value'], map_range.inputs['Value'])

        # Scale interpolation
        links.new(group_input.outputs['Scale Start'], mix_scale.inputs['A'])
        links.new(group_input.outputs['Scale End'], mix_scale.inputs['B'])
        links.new(map_range.outputs['Result'], mix_scale.inputs['Factor'])

        # Rotation interpolation
        links.new(group_input.outputs['Rotation Start'], mix_rotation.inputs['A'])
        links.new(group_input.outputs['Rotation End'], mix_rotation.inputs['B'])
        links.new(map_range.outputs['Result'], mix_rotation.inputs['Factor'])

        # Random values setup
        links.new(group_input.outputs['Random Seed'], random_position.inputs['Seed'])
        links.new(group_input.outputs['Random Seed'], random_rotation.inputs['Seed'])
        links.new(group_input.outputs['Random Seed'], random_scale.inputs['Seed'])

        links.new(index.outputs['Index'], random_position.inputs['ID'])
        links.new(index.outputs['Index'], random_rotation.inputs['ID'])
        links.new(index.outputs['Index'], random_scale.inputs['ID'])

        # Random position range
        links.new(group_input.outputs['Random Position'], vector_math_neg_pos.inputs[0])
        links.new(vector_math_neg_pos.outputs['Vector'], random_position.inputs['Min'])
        links.new(group_input.outputs['Random Position'], random_position.inputs['Max'])

        # Random rotation range
        links.new(group_input.outputs['Random Rotation'], vector_math_neg_rot.inputs[0])
        links.new(vector_math_neg_rot.outputs['Vector'], random_rotation.inputs['Min'])
        links.new(group_input.outputs['Random Rotation'], random_rotation.inputs['Max'])

        # Random scale range
        links.new(group_input.outputs['Random Scale'], math_neg_scale.inputs[0])
        links.new(math_neg_scale.outputs['Value'], random_scale.inputs['Min'])
        links.new(group_input.outputs['Random Scale'], random_scale.inputs['Max'])

        # Switch between normal instancing and random pick instancing
        links.new(group_input.outputs['Pick Random Instance'], switch_instancing.inputs['Switch'])
        links.new(instance_on_points.outputs['Instances'], switch_instancing.inputs[False])
        links.new(pick_instance_random.outputs['Instances'], switch_instancing.inputs[True])

        # Apply transforms
        links.new(switch_instancing.outputs['Output'], set_position.inputs['Geometry'])
        links.new(random_position.outputs['Value'], set_position.inputs['Offset'])

        # Apply rotation (base interpolated + random)
        links.new(set_position.outputs['Geometry'], rotate_instances.inputs['Instances'])
        links.new(mix_rotation.outputs['Result'], add_random_rotation.inputs[0])
        links.new(random_rotation.outputs['Value'], add_random_rotation.inputs[1])
        links.new(add_random_rotation.outputs['Vector'], rotate_instances.inputs['Rotation'])

        # Apply scale (base interpolated + random)
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])

        links.new(random_scale.outputs['Value'], combine_xyz_scale.inputs['X'])
        links.new(random_scale.outputs['Value'], combine_xyz_scale.inputs['Y'])
        links.new(random_scale.outputs['Value'], combine_xyz_scale.inputs['Z'])

        links.new(mix_scale.outputs['Result'], add_random_scale.inputs[0])
        links.new(combine_xyz_scale.outputs['Vector'], add_random_scale.inputs[1])
        links.new(add_random_scale.outputs['Vector'], scale_instances.inputs['Scale'])

        # Connect to output
        links.new(scale_instances.outputs['Instances'], group_output.inputs['Geometry'])

        return logic_group

    @classmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Create a linear cloner node group with scale and rotation interpolation"""

        # Create new node group for the main interface
        node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"AdvancedLinearCloner{name_suffix}")

        # --- Interface for main group ---
        # Output
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # Changed: Replace Geometry input with Object input
        node_group.interface.new_socket(name="Object", in_out='INPUT', socket_type='NodeSocketObject')

        # Basic Settings
        count_input = node_group.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
        count_input.default_value = 5
        count_input.min_value = 1
        count_input.max_value = 1000

        offset_input = node_group.interface.new_socket(name="Offset", in_out='INPUT', socket_type='NodeSocketVector')
        offset_input.default_value = (1.0, 0.0, 0.0)

        # Global Transform Settings
        global_position_input = node_group.interface.new_socket(name="Global Position", in_out='INPUT', socket_type='NodeSocketVector')
        global_position_input.default_value = (0.0, 0.0, 0.0)

        global_rotation_input = node_group.interface.new_socket(name="Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        global_rotation_input.default_value = (0.0, 0.0, 0.0)
        global_rotation_input.subtype = 'EULER'

        # Scale Start/End Settings
        scale_start_input = node_group.interface.new_socket(name="Scale Start", in_out='INPUT', socket_type='NodeSocketVector')
        scale_start_input.default_value = (1.0, 1.0, 1.0)

        scale_end_input = node_group.interface.new_socket(name="Scale End", in_out='INPUT', socket_type='NodeSocketVector')
        scale_end_input.default_value = (1.0, 1.0, 1.0)

        # Rotation Start/End Settings
        rotation_start_input = node_group.interface.new_socket(name="Rotation Start", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_start_input.default_value = (0.0, 0.0, 0.0)
        rotation_start_input.subtype = 'EULER'

        rotation_end_input = node_group.interface.new_socket(name="Rotation End", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_end_input.default_value = (0.0, 0.0, 0.0)
        rotation_end_input.subtype = 'EULER'

        # Random Settings
        random_position_input = node_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_position_input.default_value = (0.0, 0.0, 0.0)

        random_rotation_input = node_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rotation_input.default_value = (0.0, 0.0, 0.0)

        random_scale_input = node_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0
        random_scale_input.min_value = 0.0
        random_scale_input.max_value = 1.0

        seed_input = node_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0
        seed_input.max_value = 10000

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
        cloner_logic_node.name = "Linear Cloner Logic"
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
        links.new(group_input.outputs['Offset'], cloner_logic_node.inputs['Offset'])
        links.new(group_input.outputs['Scale Start'], cloner_logic_node.inputs['Scale Start'])
        links.new(group_input.outputs['Scale End'], cloner_logic_node.inputs['Scale End'])
        links.new(group_input.outputs['Rotation Start'], cloner_logic_node.inputs['Rotation Start'])
        links.new(group_input.outputs['Rotation End'], cloner_logic_node.inputs['Rotation End'])
        links.new(group_input.outputs['Random Position'], cloner_logic_node.inputs['Random Position'])
        links.new(group_input.outputs['Random Rotation'], cloner_logic_node.inputs['Random Rotation'])
        links.new(group_input.outputs['Random Scale'], cloner_logic_node.inputs['Random Scale'])
        links.new(group_input.outputs['Random Seed'], cloner_logic_node.inputs['Random Seed'])
        links.new(group_input.outputs['Pick Random Instance'], cloner_logic_node.inputs['Pick Random Instance'])

        # Apply Global Transform - connect cloner logic directly to global transform
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
def create_linear_cloner_logic_group():
    return LinearCloner.create_logic_group()

def advancedlinearcloner_node_group():
    return LinearCloner.create_node_group()

def register():
    pass

def unregister():
    pass