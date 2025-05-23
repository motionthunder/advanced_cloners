# src/effectors/GN_RandomEffector.py
import bpy
import mathutils
from .base import EffectorBase

class RandomEffector(EffectorBase):
    """Реализация случайного эффектора на основе базового класса"""
    
    @classmethod
    def create_logic_group(cls, name_suffix=""):
        """Создать логическую группу для случайного эффектора"""
        # Создаем новую группу узлов
        logic_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"RandomEffectorLogic{name_suffix}")
        
        # --- Настройка интерфейса ---
        # Выходы
        logic_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        # Входы
        logic_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        logic_group.interface.new_socket(name="Enable", in_out='INPUT', socket_type='NodeSocketBool')
        logic_group.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
        
        # Параметры трансформации
        logic_group.interface.new_socket(name="Position", in_out='INPUT', socket_type='NodeSocketVector')
        logic_group.interface.new_socket(name="Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        logic_group.interface.new_socket(name="Scale", in_out='INPUT', socket_type='NodeSocketVector')
        
        # Специфичные для RandomEffector
        uniform_scale_input = logic_group.interface.new_socket(name="Uniform Scale", in_out='INPUT', socket_type='NodeSocketBool')
        uniform_scale_input.default_value = True
        
        seed_input = logic_group.interface.new_socket(name="Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0
        
        # --- Создание узлов ---
        nodes = logic_group.nodes
        links = logic_group.links
        
        group_input = nodes.new('NodeGroupInput')
        group_output = nodes.new('NodeGroupOutput')
        
        # Basic switch for enabling/disabling the effector
        switch = nodes.new('GeometryNodeSwitch')
        switch.input_type = 'GEOMETRY'
        links.new(group_input.outputs['Enable'], switch.inputs[0])  # Switch
        links.new(group_input.outputs['Geometry'], switch.inputs[2])  # False (bypass)
        
        # Get index for random per-instance values
        index = nodes.new('GeometryNodeInputIndex')
        
        # Random position
        random_position = nodes.new('FunctionNodeRandomValue')
        random_position.data_type = 'FLOAT_VECTOR'
        
        # Link seed and ID
        links.new(group_input.outputs['Seed'], random_position.inputs['Seed'])
        links.new(index.outputs['Index'], random_position.inputs['ID'])
        
        # Set random position range (-Position to +Position)
        vector_math_neg = nodes.new('ShaderNodeVectorMath')
        vector_math_neg.operation = 'MULTIPLY'
        vector_math_neg.inputs[1].default_value = (-1.0, -1.0, -1.0)
        links.new(group_input.outputs['Position'], vector_math_neg.inputs[0])
        
        links.new(vector_math_neg.outputs['Vector'], random_position.inputs['Min'])
        links.new(group_input.outputs['Position'], random_position.inputs['Max'])
        
        # Random rotation
        random_rotation = nodes.new('FunctionNodeRandomValue')
        random_rotation.data_type = 'FLOAT_VECTOR'
        
        # Link seed and ID
        links.new(group_input.outputs['Seed'], random_rotation.inputs['Seed'])
        links.new(index.outputs['Index'], random_rotation.inputs['ID'])
        
        # Set rotation range (-Rotation to +Rotation)
        vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
        vector_math_neg_rot.operation = 'MULTIPLY'
        vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
        links.new(group_input.outputs['Rotation'], vector_math_neg_rot.inputs[0])
        
        links.new(vector_math_neg_rot.outputs['Vector'], random_rotation.inputs['Min'])
        links.new(group_input.outputs['Rotation'], random_rotation.inputs['Max'])
        
        # Random scale
        random_scale = nodes.new('FunctionNodeRandomValue')
        random_scale.data_type = 'FLOAT_VECTOR'
        
        # For uniform scale
        random_uniform_scale = nodes.new('FunctionNodeRandomValue')
        random_uniform_scale.data_type = 'FLOAT'
        
        # Link seed and ID
        links.new(group_input.outputs['Seed'], random_scale.inputs['Seed'])
        links.new(index.outputs['Index'], random_scale.inputs['ID'])
        links.new(group_input.outputs['Seed'], random_uniform_scale.inputs['Seed'])
        links.new(index.outputs['Index'], random_uniform_scale.inputs['ID'])
        
        # Set scale range (1-Scale to 1+Scale)
        one_minus_scale = nodes.new('ShaderNodeVectorMath')
        one_minus_scale.operation = 'SUBTRACT'
        one_minus_scale.inputs[0].default_value = (1.0, 1.0, 1.0)
        links.new(group_input.outputs['Scale'], one_minus_scale.inputs[1])
        
        one_plus_scale = nodes.new('ShaderNodeVectorMath')
        one_plus_scale.operation = 'ADD'
        one_plus_scale.inputs[0].default_value = (1.0, 1.0, 1.0)
        links.new(group_input.outputs['Scale'], one_plus_scale.inputs[1])
        
        links.new(one_minus_scale.outputs['Vector'], random_scale.inputs['Min'])
        links.new(one_plus_scale.outputs['Vector'], random_scale.inputs['Max'])
        
        # For uniform scale (single float)
        scale_max = nodes.new('ShaderNodeMath')
        scale_max.operation = 'MAXIMUM'
        links.new(group_input.outputs['Scale'], scale_max.inputs[0])  # X
        scale_max_temp = nodes.new('ShaderNodeMath')
        scale_max_temp.operation = 'MAXIMUM'
        links.new(group_input.outputs['Scale'], scale_max_temp.inputs[0])  # Y
        links.new(group_input.outputs['Scale'], scale_max_temp.inputs[1])  # Z
        links.new(scale_max_temp.outputs[0], scale_max.inputs[1])
        
        one_minus_uniform = nodes.new('ShaderNodeMath')
        one_minus_uniform.operation = 'SUBTRACT'
        one_minus_uniform.inputs[0].default_value = 1.0
        links.new(scale_max.outputs[0], one_minus_uniform.inputs[1])
        
        one_plus_uniform = nodes.new('ShaderNodeMath')
        one_plus_uniform.operation = 'ADD'
        one_plus_uniform.inputs[0].default_value = 1.0
        links.new(scale_max.outputs[0], one_plus_uniform.inputs[1])
        
        links.new(one_minus_uniform.outputs[0], random_uniform_scale.inputs['Min'])
        links.new(one_plus_uniform.outputs[0], random_uniform_scale.inputs['Max'])
        
        # Switch between uniform and non-uniform scale
        scale_switch = nodes.new('GeometryNodeSwitch')
        scale_switch.input_type = 'VECTOR'
        links.new(group_input.outputs['Uniform Scale'], scale_switch.inputs[0])  # Switch
        links.new(random_scale.outputs['Value'], scale_switch.inputs['False'])  # False (vector scale)
        
        # Create uniform scale vector
        uniform_vector = nodes.new('ShaderNodeCombineXYZ')
        links.new(random_uniform_scale.outputs['Value'], uniform_vector.inputs['X'])
        links.new(random_uniform_scale.outputs['Value'], uniform_vector.inputs['Y'])
        links.new(random_uniform_scale.outputs['Value'], uniform_vector.inputs['Z'])
        
        links.new(uniform_vector.outputs['Vector'], scale_switch.inputs['True'])  # True (uniform scale)
        
        # Apply global strength multiplier to position and rotation
        strength_mul_pos = nodes.new('ShaderNodeVectorMath')
        strength_mul_pos.operation = 'MULTIPLY'
        links.new(random_position.outputs['Value'], strength_mul_pos.inputs[0])
        links.new(group_input.outputs['Strength'], strength_mul_pos.inputs[1])  # Strength
        
        strength_mul_rot = nodes.new('ShaderNodeVectorMath')
        strength_mul_rot.operation = 'MULTIPLY'
        links.new(random_rotation.outputs['Value'], strength_mul_rot.inputs[0])
        links.new(group_input.outputs['Strength'], strength_mul_rot.inputs[1])  # Strength
        
        # Apply transformations to instances
        # Start with the input geometry
        translate_instances = nodes.new('GeometryNodeTranslateInstances')
        links.new(group_input.outputs['Geometry'], translate_instances.inputs['Instances'])
        links.new(strength_mul_pos.outputs['Vector'], translate_instances.inputs['Translation'])
        
        # Rotate instances
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
        links.new(strength_mul_rot.outputs['Vector'], rotate_instances.inputs['Rotation'])
        
        # Scale instances
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
        links.new(scale_switch.outputs['Output'], scale_instances.inputs['Scale'])
        
        # Connect the transformed geometry to the switch (if enabled)
        links.new(scale_instances.outputs['Instances'], switch.inputs['True'])  # True (with effect)
        
        # Output
        links.new(switch.outputs['Output'], group_output.inputs['Geometry'])
        
        return logic_group
    
    @classmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Создать основную группу для случайного эффектора, которая использует логическую группу"""
        # Создаем новую группу узлов
        main_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"RandomEffector{name_suffix}")
        
        # --- Настройка общего базового интерфейса ---
        cls.setup_common_interface(main_group)
        
        # --- Настройка специфичного интерфейса для RandomEffector ---
        # Uniform Scale
        uniform_scale_input = main_group.interface.new_socket(name="Uniform Scale", in_out='INPUT', socket_type='NodeSocketBool')
        uniform_scale_input.default_value = True
        
        # Seed
        seed_input = main_group.interface.new_socket(name="Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0
        
        # --- Поддержка полей (опциональная) ---
        cls.setup_field_interface(main_group)
        
        # --- Настройка трансформаций, общих для большинства эффекторов ---
        cls.setup_transform_interface(main_group)
        
        # --- Создание узлов ---
        nodes = main_group.nodes
        links = main_group.links
        
        group_input = nodes.new('NodeGroupInput')
        group_output = nodes.new('NodeGroupOutput')
        
        # Добавляем узел логической группы
        logic_node = nodes.new('GeometryNodeGroup')
        logic_node.node_tree = logic_group
        
        # Соединяем общие входы с логической группой
        links.new(group_input.outputs['Geometry'], logic_node.inputs['Geometry'])
        links.new(group_input.outputs['Enable'], logic_node.inputs['Enable'])
        links.new(group_input.outputs['Strength'], logic_node.inputs['Strength'])
        links.new(group_input.outputs['Position'], logic_node.inputs['Position'])
        links.new(group_input.outputs['Rotation'], logic_node.inputs['Rotation'])
        links.new(group_input.outputs['Scale'], logic_node.inputs['Scale'])
        
        # Специфичные соединения
        links.new(group_input.outputs['Uniform Scale'], logic_node.inputs['Uniform Scale'])
        links.new(group_input.outputs['Seed'], logic_node.inputs['Seed'])
        
        # --- Настройка модификации через поле (если поддерживается) ---
        # Получаем фактор влияния поля
        field_factor = cls.setup_nodes_for_field_control(
            nodes, links, group_input, 
            'Enable', 'Field'
        )
        
        # Соединяем выход с группой логики
        links.new(logic_node.outputs['Geometry'], group_output.inputs['Geometry'])
        
        return main_group


# Обратная совместимость со старым кодом
def randomeffector_node_group():
    """Create a random effector node group using the new OOP approach"""
    return RandomEffector.create_node_group()


def register():
    pass


def unregister():
    pass