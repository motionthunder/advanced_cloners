# src/effectors/GN_NoiseEffector.py
import bpy
import mathutils
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty, FloatVectorProperty, EnumProperty, IntProperty
from .base import EffectorBase

class NoiseEffector(EffectorBase):
    """Реализация шумового эффектора на основе базового класса"""
    
    @classmethod
    def create_logic_group(cls, name_suffix=""):
        """Создать логическую группу для шумового эффектора"""
        # Создаем новую группу узлов
        logic_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"NoiseEffectorLogic{name_suffix}")
        
        # --- Настройка интерфейса ---
        # Выходы
        logic_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        # Входы
        logic_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        logic_group.interface.new_socket(name="Enable", in_out='INPUT', socket_type='NodeSocketBool')
        logic_group.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
        
        # Параметры трансформации
        logic_group.interface.new_socket(name="Position", in_out='INPUT', socket_type='NodeSocketVector')
        
        symmetric_translation_input = logic_group.interface.new_socket(name="Symmetric Translation", in_out='INPUT', socket_type='NodeSocketBool')
        symmetric_translation_input.default_value = False
        
        logic_group.interface.new_socket(name="Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        
        symmetric_rotation_input = logic_group.interface.new_socket(name="Symmetric Rotation", in_out='INPUT', socket_type='NodeSocketBool')
        symmetric_rotation_input.default_value = False
        
        logic_group.interface.new_socket(name="Scale", in_out='INPUT', socket_type='NodeSocketVector')
        
        uniform_scale_input = logic_group.interface.new_socket(name="Uniform Scale", in_out='INPUT', socket_type='NodeSocketBool')
        uniform_scale_input.default_value = True
        
        # Параметры шума
        noise_scale_input = logic_group.interface.new_socket(name="Noise Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_scale_input.default_value = 0.5
        noise_scale_input.min_value = 0.1
        noise_scale_input.max_value = 10.0
        
        noise_detail_input = logic_group.interface.new_socket(name="Noise Detail", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_detail_input.default_value = 2.0
        noise_detail_input.min_value = 0.0
        noise_detail_input.max_value = 15.0
        
        noise_roughness_input = logic_group.interface.new_socket(name="Noise Roughness", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_roughness_input.default_value = 0.5
        noise_roughness_input.min_value = 0.0
        noise_roughness_input.max_value = 1.0
        
        noise_lacunarity_input = logic_group.interface.new_socket(name="Noise Lacunarity", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_lacunarity_input.default_value = 2.0
        noise_lacunarity_input.min_value = 0.0
        noise_lacunarity_input.max_value = 10.0
        
        noise_distortion_input = logic_group.interface.new_socket(name="Noise Distortion", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_distortion_input.default_value = 0.0
        noise_distortion_input.min_value = -10.0
        noise_distortion_input.max_value = 10.0
        
        # Позиция шума и масштаб
        noise_position_input = logic_group.interface.new_socket(name="Noise Position", in_out='INPUT', socket_type='NodeSocketVector')
        noise_position_input.default_value = (0.0, 0.0, 0.0)
        
        noise_xyz_scale_input = logic_group.interface.new_socket(name="Noise XYZ Scale", in_out='INPUT', socket_type='NodeSocketVector')
        noise_xyz_scale_input.default_value = (1.0, 1.0, 1.0)
        
        # Анимация
        speed_input = logic_group.interface.new_socket(name="Speed", in_out='INPUT', socket_type='NodeSocketFloat')
        speed_input.default_value = 0.0
        speed_input.min_value = 0.0
        speed_input.max_value = 10.0
        
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
        links.new(group_input.outputs['Geometry'], switch.inputs[1])  # True (bypass)
        
        # Get position for noise input
        position = nodes.new('GeometryNodeInputPosition')
        
        # Get index for per-instance noise offset
        index = nodes.new('GeometryNodeInputIndex')
        
        # Scene time for animation
        scene_time = nodes.new('GeometryNodeInputSceneTime')
        
        # Calculate time factor for animation
        time_factor = nodes.new('ShaderNodeMath')
        time_factor.operation = 'MULTIPLY'
        links.new(scene_time.outputs[1], time_factor.inputs[0])  # Frame
        links.new(group_input.outputs['Speed'], time_factor.inputs[1])  # Speed
        
        # Add instance index for variation
        index_to_float = nodes.new('ShaderNodeMath')
        index_to_float.operation = 'MULTIPLY'
        links.new(index.outputs['Index'], index_to_float.inputs[0])
        index_to_float.inputs[1].default_value = 123.456  # Arbitrary scaling factor
        
        # Add seed for more control
        seed_value = nodes.new('ShaderNodeMath')
        seed_value.operation = 'ADD'
        links.new(index_to_float.outputs[0], seed_value.inputs[0])
        links.new(group_input.outputs['Seed'], seed_value.inputs[1])
        
        # Add time for animation
        animated_value = nodes.new('ShaderNodeMath')
        animated_value.operation = 'ADD'
        links.new(seed_value.outputs[0], animated_value.inputs[0])
        links.new(time_factor.outputs[0], animated_value.inputs[1])
        
        # Apply noise position and scale to position input
        position_offset = nodes.new('ShaderNodeVectorMath')
        position_offset.operation = 'ADD'
        links.new(position.outputs[0], position_offset.inputs[0])
        links.new(group_input.outputs['Noise Position'], position_offset.inputs[1])
        
        position_scaled = nodes.new('ShaderNodeVectorMath')
        position_scaled.operation = 'MULTIPLY'
        links.new(position_offset.outputs[0], position_scaled.inputs[0])
        links.new(group_input.outputs['Noise XYZ Scale'], position_scaled.inputs[1])
        
        # Position noise (for translation)
        position_noise = nodes.new('ShaderNodeTexNoise')
        position_noise.noise_dimensions = '4D'
        links.new(position_scaled.outputs[0], position_noise.inputs['Vector'])
        links.new(animated_value.outputs[0], position_noise.inputs['W'])
        links.new(group_input.outputs['Noise Scale'], position_noise.inputs['Scale'])
        links.new(group_input.outputs['Noise Detail'], position_noise.inputs['Detail'])
        links.new(group_input.outputs['Noise Roughness'], position_noise.inputs['Roughness'])
        links.new(group_input.outputs['Noise Lacunarity'], position_noise.inputs['Lacunarity'])
        links.new(group_input.outputs['Noise Distortion'], position_noise.inputs['Distortion'])
        
        # Rotation noise (with different offset)
        rotation_noise = nodes.new('ShaderNodeTexNoise')
        rotation_noise.noise_dimensions = '4D'
        rotation_offset = nodes.new('ShaderNodeMath')
        rotation_offset.operation = 'ADD'
        links.new(animated_value.outputs[0], rotation_offset.inputs[0])
        rotation_offset.inputs[1].default_value = 42.0  # Different offset
        links.new(position_scaled.outputs[0], rotation_noise.inputs['Vector'])
        links.new(rotation_offset.outputs[0], rotation_noise.inputs['W'])
        links.new(group_input.outputs['Noise Scale'], rotation_noise.inputs['Scale'])
        links.new(group_input.outputs['Noise Detail'], rotation_noise.inputs['Detail'])
        links.new(group_input.outputs['Noise Roughness'], rotation_noise.inputs['Roughness'])
        links.new(group_input.outputs['Noise Lacunarity'], rotation_noise.inputs['Lacunarity'])
        links.new(group_input.outputs['Noise Distortion'], rotation_noise.inputs['Distortion'])
        
        # Scale noise (with different offset)
        scale_noise = nodes.new('ShaderNodeTexNoise')
        scale_noise.noise_dimensions = '4D'
        scale_offset = nodes.new('ShaderNodeMath')
        scale_offset.operation = 'ADD'
        links.new(animated_value.outputs[0], scale_offset.inputs[0])
        scale_offset.inputs[1].default_value = 84.0  # Different offset
        links.new(position_scaled.outputs[0], scale_noise.inputs['Vector'])
        links.new(scale_offset.outputs[0], scale_noise.inputs['W'])
        links.new(group_input.outputs['Noise Scale'], scale_noise.inputs['Scale'])
        links.new(group_input.outputs['Noise Detail'], scale_noise.inputs['Detail'])
        links.new(group_input.outputs['Noise Roughness'], scale_noise.inputs['Roughness'])
        links.new(group_input.outputs['Noise Lacunarity'], scale_noise.inputs['Lacunarity'])
        links.new(group_input.outputs['Noise Distortion'], scale_noise.inputs['Distortion'])
        
        # Convert noise to vector transforms
        
        # Position transform (map 0-1 to -Position to +Position)
        position_sub = nodes.new('ShaderNodeVectorMath')
        position_sub.operation = 'MULTIPLY_ADD'
        position_sub.inputs[1].default_value = (2.0, 2.0, 2.0)
        position_sub.inputs[2].default_value = (-1.0, -1.0, -1.0)
        links.new(position_noise.outputs['Color'], position_sub.inputs[0])
        
        # Обрабатываем симметричное смещение
        position_neg = nodes.new('ShaderNodeVectorMath')
        position_neg.operation = 'MULTIPLY'
        position_neg.inputs[1].default_value = (-1.0, -1.0, -1.0)
        links.new(group_input.outputs['Position'], position_neg.inputs[0])
        
        # Switch между симметричным и обычным смещением
        position_sym_switch = nodes.new('GeometryNodeSwitch')
        position_sym_switch.input_type = 'VECTOR'
        links.new(group_input.outputs['Symmetric Translation'], position_sym_switch.inputs[0])
        links.new(group_input.outputs['Position'], position_sym_switch.inputs[2])  # True
        links.new(position_neg.outputs[0], position_sym_switch.inputs[1])  # False
        
        # Multiply by position range
        position_range = nodes.new('ShaderNodeVectorMath')
        position_range.operation = 'MULTIPLY'
        links.new(position_sub.outputs[0], position_range.inputs[0])
        links.new(group_input.outputs['Position'], position_range.inputs[1])
        
        # Rotation transform (map 0-1 to -Rotation to +Rotation)
        rotation_sub = nodes.new('ShaderNodeVectorMath')
        rotation_sub.operation = 'MULTIPLY_ADD'
        rotation_sub.inputs[1].default_value = (2.0, 2.0, 2.0)
        rotation_sub.inputs[2].default_value = (-1.0, -1.0, -1.0)
        links.new(rotation_noise.outputs['Color'], rotation_sub.inputs[0])
        
        # Обрабатываем симметричное вращение
        rotation_neg = nodes.new('ShaderNodeVectorMath')
        rotation_neg.operation = 'MULTIPLY'
        rotation_neg.inputs[1].default_value = (-1.0, -1.0, -1.0)
        links.new(group_input.outputs['Rotation'], rotation_neg.inputs[0])
        
        # Switch между симметричным и обычным вращением
        rotation_sym_switch = nodes.new('GeometryNodeSwitch')
        rotation_sym_switch.input_type = 'VECTOR'
        links.new(group_input.outputs['Symmetric Rotation'], rotation_sym_switch.inputs[0])
        links.new(group_input.outputs['Rotation'], rotation_sym_switch.inputs[2])  # True
        links.new(rotation_neg.outputs[0], rotation_sym_switch.inputs[1])  # False
        
        # Multiply by rotation range
        rotation_range = nodes.new('ShaderNodeVectorMath')
        rotation_range.operation = 'MULTIPLY'
        links.new(rotation_sub.outputs[0], rotation_range.inputs[0])
        links.new(group_input.outputs['Rotation'], rotation_range.inputs[1])
        
        # Scale transform
        # Map noise to 1-x to 1+x scale range
        scale_add = nodes.new('ShaderNodeVectorMath')
        scale_add.operation = 'MULTIPLY_ADD'
        scale_add.inputs[1].default_value = (2.0, 2.0, 2.0)
        scale_add.inputs[2].default_value = (-1.0, -1.0, -1.0)
        links.new(scale_noise.outputs['Color'], scale_add.inputs[0])
        
        # Create base scale vector (1,1,1)
        scale_base = nodes.new('ShaderNodeCombineXYZ')
        scale_base.inputs[0].default_value = 1.0
        scale_base.inputs[1].default_value = 1.0
        scale_base.inputs[2].default_value = 1.0
        
        # Apply scale variation
        scale_mul = nodes.new('ShaderNodeVectorMath')
        scale_mul.operation = 'MULTIPLY'
        links.new(scale_add.outputs[0], scale_mul.inputs[0])
        links.new(group_input.outputs['Scale'], scale_mul.inputs[1])
        
        # Add to base scale
        scale_final = nodes.new('ShaderNodeVectorMath')
        scale_final.operation = 'ADD'
        links.new(scale_base.outputs[0], scale_final.inputs[0])
        links.new(scale_mul.outputs[0], scale_final.inputs[1])
        
        # For uniform scale (use only the X component)
        # Extract X component
        separate_xyz = nodes.new('ShaderNodeSeparateXYZ')
        links.new(scale_final.outputs[0], separate_xyz.inputs[0])
        
        # Create uniform vector from X
        uniform_scale = nodes.new('ShaderNodeCombineXYZ')
        links.new(separate_xyz.outputs[0], uniform_scale.inputs[0])
        links.new(separate_xyz.outputs[0], uniform_scale.inputs[1])
        links.new(separate_xyz.outputs[0], uniform_scale.inputs[2])
        
        # Switch between uniform and non-uniform scale
        scale_switch = nodes.new('GeometryNodeSwitch')
        scale_switch.input_type = 'VECTOR'
        links.new(group_input.outputs['Uniform Scale'], scale_switch.inputs[0])  # Switch
        links.new(scale_final.outputs[0], scale_switch.inputs[1])  # False
        links.new(uniform_scale.outputs[0], scale_switch.inputs[2])  # True
        
        # Apply strength multiplier
        position_strength = nodes.new('ShaderNodeVectorMath')
        position_strength.operation = 'MULTIPLY'
        links.new(position_range.outputs[0], position_strength.inputs[0])
        links.new(group_input.outputs['Strength'], position_strength.inputs[1])  # Scalar
        
        rotation_strength = nodes.new('ShaderNodeVectorMath')
        rotation_strength.operation = 'MULTIPLY'
        links.new(rotation_range.outputs[0], rotation_strength.inputs[0])
        links.new(group_input.outputs['Strength'], rotation_strength.inputs[1])  # Scalar
        
        # Apply transforms to instances
        translate_instances = nodes.new('GeometryNodeTranslateInstances')
        links.new(group_input.outputs['Geometry'], translate_instances.inputs['Instances'])
        links.new(position_strength.outputs[0], translate_instances.inputs['Translation'])
        
        # Rotate instances
        rotate_instances = nodes.new('GeometryNodeRotateInstances')
        links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
        links.new(rotation_strength.outputs[0], rotate_instances.inputs['Rotation'])
        
        # Scale instances
        scale_instances = nodes.new('GeometryNodeScaleInstances')
        links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
        links.new(scale_switch.outputs[0], scale_instances.inputs['Scale'])
        
        # Connect to the output
        links.new(scale_instances.outputs['Instances'], switch.inputs[2])  # False
        links.new(switch.outputs[0], group_output.inputs['Geometry'])
        
        # Layout nodes for better organization
        group_input.location = (-1000, 0)
        group_output.location = (1000, 0)
        
        return logic_group
    
    @classmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Создать основную группу для шумового эффектора, которая использует логическую группу"""
        # Создаем новую группу узлов
        main_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=f"NoiseEffector{name_suffix}")
        
        # --- Настройка общего базового интерфейса ---
        cls.setup_common_interface(main_group)
        
        # --- Настройка специфичного интерфейса для NoiseEffector ---
        # Симметричное смещение
        symmetric_translation_input = main_group.interface.new_socket(name="Symmetric Translation", in_out='INPUT', socket_type='NodeSocketBool')
        symmetric_translation_input.default_value = False
        
        # Симметричное вращение
        symmetric_rotation_input = main_group.interface.new_socket(name="Symmetric Rotation", in_out='INPUT', socket_type='NodeSocketBool')
        symmetric_rotation_input.default_value = False
        
        # Uniform Scale
        uniform_scale_input = main_group.interface.new_socket(name="Uniform Scale", in_out='INPUT', socket_type='NodeSocketBool')
        uniform_scale_input.default_value = True
        
        # Параметры шума
        noise_scale_input = main_group.interface.new_socket(name="Noise Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_scale_input.default_value = 0.5
        noise_scale_input.min_value = 0.1
        noise_scale_input.max_value = 10.0
        
        noise_detail_input = main_group.interface.new_socket(name="Noise Detail", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_detail_input.default_value = 2.0
        noise_detail_input.min_value = 0.0
        noise_detail_input.max_value = 15.0
        
        noise_roughness_input = main_group.interface.new_socket(name="Noise Roughness", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_roughness_input.default_value = 0.5
        noise_roughness_input.min_value = 0.0
        noise_roughness_input.max_value = 1.0
        
        noise_lacunarity_input = main_group.interface.new_socket(name="Noise Lacunarity", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_lacunarity_input.default_value = 2.0
        noise_lacunarity_input.min_value = 0.0
        noise_lacunarity_input.max_value = 10.0
        
        noise_distortion_input = main_group.interface.new_socket(name="Noise Distortion", in_out='INPUT', socket_type='NodeSocketFloat')
        noise_distortion_input.default_value = 0.0
        noise_distortion_input.min_value = -10.0
        noise_distortion_input.max_value = 10.0
        
        # Позиция шума и масштаб
        noise_position_input = main_group.interface.new_socket(name="Noise Position", in_out='INPUT', socket_type='NodeSocketVector')
        noise_position_input.default_value = (0.0, 0.0, 0.0)
        
        noise_xyz_scale_input = main_group.interface.new_socket(name="Noise XYZ Scale", in_out='INPUT', socket_type='NodeSocketVector')
        noise_xyz_scale_input.default_value = (1.0, 1.0, 1.0)
        
        # Анимация
        speed_input = main_group.interface.new_socket(name="Speed", in_out='INPUT', socket_type='NodeSocketFloat')
        speed_input.default_value = 0.0
        speed_input.min_value = 0.0
        speed_input.max_value = 10.0
        
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
        
        # Специфичные соединения для NoiseEffector
        links.new(group_input.outputs['Symmetric Translation'], logic_node.inputs['Symmetric Translation'])
        links.new(group_input.outputs['Symmetric Rotation'], logic_node.inputs['Symmetric Rotation'])
        links.new(group_input.outputs['Uniform Scale'], logic_node.inputs['Uniform Scale'])
        links.new(group_input.outputs['Noise Scale'], logic_node.inputs['Noise Scale'])
        links.new(group_input.outputs['Noise Detail'], logic_node.inputs['Noise Detail'])
        links.new(group_input.outputs['Noise Roughness'], logic_node.inputs['Noise Roughness'])
        links.new(group_input.outputs['Noise Lacunarity'], logic_node.inputs['Noise Lacunarity'])
        links.new(group_input.outputs['Noise Distortion'], logic_node.inputs['Noise Distortion'])
        links.new(group_input.outputs['Noise Position'], logic_node.inputs['Noise Position'])
        links.new(group_input.outputs['Noise XYZ Scale'], logic_node.inputs['Noise XYZ Scale'])
        links.new(group_input.outputs['Speed'], logic_node.inputs['Speed'])
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
def noiseeffector_node_group():
    """Create a noise effector node group using the new OOP approach"""
    return NoiseEffector.create_node_group()


# Сохраняем оригинальные операторы
class CE_OT_Noise_Effector(Operator):
    bl_idname = "object.ce_ot_noise_effector"
    bl_label = "Noise Effector"
    bl_description = "Add a new Noise Effector object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Этот метод будет реализован в соответствующем месте в advanced_cloners
        # Для совместимости с существующим кодом
        return {'FINISHED'}

# Operator for editing a NoiseEffector
class CE_OT_Edit_NoiseEffector(Operator):
    bl_idname = "object.ce_ot_edit_noise_effector"
    bl_label = "Edit Noise Effector"
    bl_description = "Edit selected noise effector"
    bl_options = {'REGISTER', 'UNDO'}
    
    # NoiseEffector parameters
    strength: FloatProperty(
        name="Strength",
        description="Effect strength",
        default=0.0,
        min=0.0,
        max=1.0,
    )
    
    position: FloatVectorProperty(
        name="Position",
        description="Position offset range",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION',
    )
    
    symmetric_translation: BoolProperty(
        name="Symmetric Translation",
        description="Use symmetric translation values (-value to +value)",
        default=False,
    )
    
    rotation: FloatVectorProperty(
        name="Rotation",
        description="Rotation range in degrees",
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
    )
    
    symmetric_rotation: BoolProperty(
        name="Symmetric Rotation",
        description="Use symmetric rotation values (-value to +value)",
        default=False,
    )
    
    scale: FloatVectorProperty(
        name="Scale",
        description="Scale range",
        default=(0.0, 0.0, 0.0),
        subtype='XYZ',
    )
    
    uniform_scale: BoolProperty(
        name="Uniform Scale",
        description="Use uniform scaling (X value only)",
        default=True,
    )
    
    # Noise parameters
    noise_scale: FloatProperty(
        name="Noise Scale",
        description="Overall scale of the noise pattern",
        default=0.5,
        min=0.1,
        max=10.0,
    )
    
    noise_detail: FloatProperty(
        name="Detail",
        description="Amount of noise detail",
        default=2.0,
        min=0.0,
        max=15.0,
    )
    
    noise_roughness: FloatProperty(
        name="Roughness",
        description="Roughness of the noise",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    
    noise_lacunarity: FloatProperty(
        name="Lacunarity",
        description="Gap between successive noise frequencies",
        default=2.0,
        min=0.0,
        max=10.0,
    )
    
    noise_distortion: FloatProperty(
        name="Distortion",
        description="Amount of distortion",
        default=0.0,
        min=-10.0,
        max=10.0,
    )
    
    # Noise position and scale
    noise_position: FloatVectorProperty(
        name="Noise Position",
        description="Offset of the noise pattern",
        default=(0.0, 0.0, 0.0),
    )
    
    noise_xyz_scale: FloatVectorProperty(
        name="Noise XYZ Scale",
        description="Scale of the noise in each axis",
        default=(1.0, 1.0, 1.0),
    )
    
    # Animation
    speed: FloatProperty(
        name="Speed",
        description="Speed of noise animation",
        default=0.0,
        min=0.0,
        max=10.0,
    )
    
    seed: IntProperty(
        name="Seed",
        description="Random seed for the noise pattern",
        default=0,
        min=0,
    )
    
    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and "clo_effector_type" in active
    
    def invoke(self, context, event):
        obj = context.active_object
        
        if "clo_effector_type" in obj:
            effector_type = obj["clo_effector_type"]
            
            # Get current values from the effector
            modifiers = obj.modifiers
            if effector_type == "noise":
                for mod in modifiers:
                    if mod.type == 'NODES' and "NoiseEffector" in mod.node_group.name:
                        # Access the modifier's node group input values
                        try:
                            self.strength = mod["Input_2"]  # Strength
                            self.position = mod["Input_3"]  # Position
                            self.symmetric_translation = mod["Input_4"]  # Symmetric Translation
                            self.rotation = mod["Input_5"]  # Rotation
                            self.symmetric_rotation = mod["Input_6"]  # Symmetric Rotation
                            self.scale = mod["Input_7"]  # Scale
                            self.uniform_scale = mod["Input_8"]  # Uniform Scale
                            self.noise_scale = mod["Input_9"]  # Noise Scale
                            self.noise_detail = mod["Input_10"]  # Noise Detail
                            self.noise_roughness = mod["Input_11"]  # Noise Roughness
                            self.noise_lacunarity = mod["Input_12"]  # Noise Lacunarity
                            self.noise_distortion = mod["Input_13"]  # Noise Distortion
                            self.noise_position = mod["Input_14"]  # Noise Position
                            self.noise_xyz_scale = mod["Input_15"]  # Noise XYZ Scale
                            self.speed = mod["Input_16"]  # Speed
                            self.seed = mod["Input_17"]  # Seed
                        except Exception as e:
                            print(f"Error reading NoiseEffector values: {e}")
                        break
        
        return self.execute(context)
    
    def execute(self, context):
        obj = context.active_object
        
        if "clo_effector_type" in obj:
            effector_type = obj["clo_effector_type"]
            
            modifiers = obj.modifiers
            if effector_type == "noise":
                for mod in modifiers:
                    if mod.type == 'NODES' and "NoiseEffector" in mod.node_group.name:
                        # Update the modifier's node group input values
                        try:
                            mod["Input_2"] = self.strength  # Strength
                            mod["Input_3"] = self.position  # Position
                            mod["Input_4"] = self.symmetric_translation  # Symmetric Translation
                            mod["Input_5"] = self.rotation  # Rotation
                            mod["Input_6"] = self.symmetric_rotation  # Symmetric Rotation
                            mod["Input_7"] = self.scale  # Scale
                            mod["Input_8"] = self.uniform_scale  # Uniform Scale
                            mod["Input_9"] = self.noise_scale  # Noise Scale
                            mod["Input_10"] = self.noise_detail  # Noise Detail
                            mod["Input_11"] = self.noise_roughness  # Noise Roughness
                            mod["Input_12"] = self.noise_lacunarity  # Noise Lacunarity
                            mod["Input_13"] = self.noise_distortion  # Noise Distortion
                            mod["Input_14"] = self.noise_position  # Noise Position
                            mod["Input_15"] = self.noise_xyz_scale  # Noise XYZ Scale
                            mod["Input_16"] = self.speed  # Speed
                            mod["Input_17"] = self.seed  # Seed
                        except Exception as e:
                            print(f"Error updating NoiseEffector values: {e}")
                        break
        
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Main strength
        layout.prop(self, "strength")
        
        # Transform properties
        transform_box = layout.box()
        transform_box.label(text="Transform")
        
        # Translation
        trans_row = transform_box.row()
        trans_row.prop(self, "position")
        trans_row.prop(self, "symmetric_translation", icon='ARROW_LEFTRIGHT')
        
        # Rotation
        rot_row = transform_box.row()
        rot_row.prop(self, "rotation")
        rot_row.prop(self, "symmetric_rotation", icon='ARROW_LEFTRIGHT')
        
        # Scale
        scale_row = transform_box.row()
        scale_row.prop(self, "scale")
        scale_row.prop(self, "uniform_scale", icon='ARROW_LEFTRIGHT')
        
        # Noise settings
        noise_box = layout.box()
        noise_box.label(text="Noise Settings")
        noise_box.prop(self, "noise_scale")
        noise_box.prop(self, "noise_detail")
        noise_box.prop(self, "noise_roughness")
        noise_box.prop(self, "noise_lacunarity")
        noise_box.prop(self, "noise_distortion")
        
        # Noise position/scale
        position_box = layout.box()
        position_box.label(text="Noise Position & Scale")
        position_box.prop(self, "noise_position")
        position_box.prop(self, "noise_xyz_scale")
        
        # Animation
        anim_box = layout.box()
        anim_box.label(text="Animation")
        anim_box.prop(self, "speed")
        anim_box.prop(self, "seed")


def register():
    bpy.utils.register_class(CE_OT_Noise_Effector)
    bpy.utils.register_class(CE_OT_Edit_NoiseEffector)


def unregister():
    bpy.utils.unregister_class(CE_OT_Edit_NoiseEffector)
    bpy.utils.unregister_class(CE_OT_Noise_Effector) 