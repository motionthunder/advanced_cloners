"""
Functions for creating and managing collection cloners.
"""

import bpy

def create_collection_cloner_nodetree(collection_obj, cloner_type, collection_name, use_anti_recursion=False):
    """
    Creates a node group for cloning a collection using Geometry Nodes

    Args:
        collection_obj: The collection to be cloned
        cloner_type: Type of cloner (GRID, LINEAR, CIRCLE)
        collection_name: Name of the collection
        use_anti_recursion: Whether to use anti-recursion

    Returns:
        Created node group
    """
    # Create a new geometry node group
    node_group_name = f"CollectionCloner_{cloner_type}_{collection_name}"
    counter = 1
    while node_group_name in bpy.data.node_groups:
        node_group_name = f"CollectionCloner_{cloner_type}_{collection_name}_{counter:03d}"
        counter += 1

    node_group = bpy.data.node_groups.new(node_group_name, 'GeometryNodeTree')

    # EXACTLY match the mesh cloner interface for consistency
    # Create input and output sockets for user parameters

    # Create these for all cloner types
    # Layout counts
    if cloner_type == "LINEAR":
        # LINEAR uses Count instead of Count X
        count_socket = node_group.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
    elif cloner_type == "CIRCLE":
        # CIRCLE должен использовать Count вместо Count X для совместимости с UI
        count_socket = node_group.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
    else:  # GRID
        count_x_socket = node_group.interface.new_socket("Count X", in_out='INPUT', socket_type='NodeSocketInt')

    # Different parameters based on cloner type
    if cloner_type == "GRID":
        # For Grid we need Y and Z counts
        count_y_socket = node_group.interface.new_socket("Count Y", in_out='INPUT', socket_type='NodeSocketInt')
        count_z_socket = node_group.interface.new_socket("Count Z", in_out='INPUT', socket_type='NodeSocketInt')

    # Spacing/Offset parameter - Vector for GRID, OFFSET vector for LINEAR, Float for CIRCLE
    if cloner_type == "GRID":
        spacing_socket = node_group.interface.new_socket("Spacing", in_out='INPUT', socket_type='NodeSocketVector')
    elif cloner_type == "LINEAR":
        offset_socket = node_group.interface.new_socket("Offset", in_out='INPUT', socket_type='NodeSocketVector')
    else:  # CIRCLE
        # Используем Radius вместо Spacing для совместимости с UI
        radius_socket = node_group.interface.new_socket("Radius", in_out='INPUT', socket_type='NodeSocketFloat')

    # Instance Transform
    rotation_socket = node_group.interface.new_socket("Instance Rotation", in_out='INPUT', socket_type='NodeSocketVector')
    scale_socket = node_group.interface.new_socket("Instance Scale", in_out='INPUT', socket_type='NodeSocketVector')

    # Global transform parameters
    global_pos_socket = node_group.interface.new_socket("Global Position", in_out='INPUT', socket_type='NodeSocketVector')
    global_rot_socket = node_group.interface.new_socket("Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')

    # Random parameters
    random_seed_socket = node_group.interface.new_socket("Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
    random_pos_socket = node_group.interface.new_socket("Random Position", in_out='INPUT', socket_type='NodeSocketVector')
    random_rot_socket = node_group.interface.new_socket("Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
    random_scale_socket = node_group.interface.new_socket("Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')

    # Material/Color parameters
    color_socket = node_group.interface.new_socket("Color", in_out='INPUT', socket_type='NodeSocketColor')

    # Extra options
    center_grid_socket = node_group.interface.new_socket("Center Grid", in_out='INPUT', socket_type='NodeSocketBool')
    pick_instance_socket = node_group.interface.new_socket("Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')

    # Добавляем параметр для включения/выключения "реализации" инстансов
    realize_instances_socket = node_group.interface.new_socket("Realize Instances", in_out='INPUT', socket_type='NodeSocketBool')

    # Output socket for the final geometry
    node_group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Set default values directly on the sockets as they are created
    try:
        # Устанавливаем значение по умолчанию для параметра Realize Instances
        # Используем значение параметра use_anti_recursion
        realize_instances_socket.default_value = use_anti_recursion

        # Layout defaults
        if cloner_type == "GRID":
            count_x_socket.default_value = 3
            count_x_socket.min_value = 1
            count_x_socket.max_value = 100
        elif cloner_type == "LINEAR":
            count_socket.default_value = 5
            count_socket.min_value = 1
            count_socket.max_value = 1000
        elif cloner_type == "CIRCLE":
            # Для CIRCLE используем значения из конфигурации
            count_socket.default_value = 8
            count_socket.min_value = 3
            count_socket.max_value = 1000

        if cloner_type == "GRID":
            count_y_socket.default_value = 3
            count_y_socket.min_value = 1
            count_y_socket.max_value = 100

            count_z_socket.default_value = 1
            count_z_socket.min_value = 1
            count_z_socket.max_value = 100

        # Set spacing/offset defaults
        if cloner_type == "GRID":
            spacing_socket.default_value = (3.0, 3.0, 3.0)
        elif cloner_type == "LINEAR":
            offset_socket.default_value = (3.0, 0.0, 0.0)  # Exactly like mesh linear cloner
        else:  # CIRCLE
            radius_socket.default_value = 4.0  # Используем значение из конфигурации

        # Transform defaults
        rotation_socket.default_value = (0.0, 0.0, 0.0)
        rotation_socket.subtype = 'EULER'

        scale_socket.default_value = (1.0, 1.0, 1.0)

        # Global transform defaults
        global_pos_socket.default_value = (0.0, 0.0, 0.0)
        global_rot_socket.default_value = (0.0, 0.0, 0.0)
        global_rot_socket.subtype = 'EULER'

        # Random defaults
        random_seed_socket.default_value = 0
        random_seed_socket.min_value = 0
        random_seed_socket.max_value = 10000

        random_pos_socket.default_value = (0.0, 0.0, 0.0)
        random_rot_socket.default_value = (0.0, 0.0, 0.0)
        random_rot_socket.subtype = 'EULER'

        random_scale_socket.default_value = 0.0
        random_scale_socket.min_value = 0.0
        random_scale_socket.max_value = 1.0

        # Color default
        color_socket.default_value = (1.0, 1.0, 1.0, 1.0)

        # Options defaults
        center_grid_socket.default_value = True  # Изменено с False на True для центрирования по умолчанию
        pick_instance_socket.default_value = False

    except Exception as e:
        print(f"Warning: Could not set default values for sockets: {e}")

    # Create nodes
    nodes = node_group.nodes
    links = node_group.links

    # Group input/output nodes
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1000, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (1000, 0)

    # Collection Info node
    collection_info = nodes.new('GeometryNodeCollectionInfo')
    collection_info.inputs["Collection"].default_value = collection_obj
    collection_info.inputs["Separate Children"].default_value = False
    collection_info.location = (-800, -200)

    # Если анти-рекурсия включена, добавляем узлы для её реализации на входе
    if use_anti_recursion:
        # Добавляем узел Realize Instances для входных инстансов
        input_realize = nodes.new('GeometryNodeRealizeInstances')
        input_realize.name = "Input Realize Instances"
        input_realize.location = (-700, -200)

        # Создаем узел Switch для входных инстансов
        input_switch = nodes.new('GeometryNodeSwitch')
        input_switch.input_type = 'GEOMETRY'
        input_switch.name = "Input Realize Switch"
        input_switch.location = (-600, -200)

        # Соединяем коллекцию с узлом Realize Instances
        links.new(collection_info.outputs['Instances'], input_realize.inputs['Geometry'])

        # Настраиваем входной переключатель
        links.new(group_in.outputs['Realize Instances'], input_switch.inputs['Switch'])
        links.new(collection_info.outputs['Instances'], input_switch.inputs[False])  # Обычные инстансы
        links.new(input_realize.outputs['Geometry'], input_switch.inputs[True])  # "Реализованные" инстансы

        # Используем выход переключателя для дальнейшей логики
        collection_output = input_switch.outputs[0]
    else:
        # Если анти-рекурсия выключена, просто используем выход коллекции
        collection_output = collection_info.outputs['Instances']

    # Add a spacing multiplier node just like in mesh cloner
    # For GRID we convert the vector to 3 components
    # For LINEAR we use offset vector directly
    # For CIRCLE we convert float to vector

    if cloner_type == "GRID":
        # GRID cloner uses spacing vector
        spacing_multiplier = nodes.new('ShaderNodeVectorMath')
        spacing_multiplier.operation = 'MULTIPLY'
        # Используем множитель 1.0 для применения значений напрямую
        spacing_multiplier.inputs[1].default_value = (1.0, 1.0, 1.0)
        spacing_multiplier.location = (-900, 100)
        links.new(group_in.outputs["Spacing"], spacing_multiplier.inputs[0])

        # Separate XYZ to get individual spacing components
        separate_xyz = nodes.new('ShaderNodeSeparateXYZ')
        separate_xyz.location = (-750, 100)
        links.new(spacing_multiplier.outputs[0], separate_xyz.inputs[0])
    elif cloner_type == "LINEAR":
        # LINEAR cloner uses offset vector directly
        # No need for spacing multiplier
        offset_vector = group_in.outputs["Offset"]

        # Still need to separate for centering calculations
        separate_xyz = nodes.new('ShaderNodeSeparateXYZ')
        separate_xyz.location = (-750, 100)
        links.new(offset_vector, separate_xyz.inputs[0])
    else:  # CIRCLE
        # CIRCLE uses float radius
        combine_spacing = nodes.new('ShaderNodeCombineXYZ')
        combine_spacing.location = (-900, 100)
        links.new(group_in.outputs["Radius"], combine_spacing.inputs['X'])
        links.new(group_in.outputs["Radius"], combine_spacing.inputs['Y'])
        links.new(group_in.outputs["Radius"], combine_spacing.inputs['Z'])

        spacing_multiplier = nodes.new('ShaderNodeVectorMath')
        spacing_multiplier.operation = 'MULTIPLY'
        spacing_multiplier.inputs[1].default_value = (1.0, 1.0, 1.0)
        spacing_multiplier.location = (-800, 100)
        links.new(combine_spacing.outputs[0], spacing_multiplier.inputs[0])

        # Separate XYZ to get individual spacing components
        separate_xyz = nodes.new('ShaderNodeSeparateXYZ')
        separate_xyz.location = (-750, 100)
        links.new(spacing_multiplier.outputs[0], separate_xyz.inputs[0])

    # Create different layout based on cloner type
    if cloner_type == "GRID":
        # Implement exact same grid creation logic as in GN_GridCloner.py

        # --- Point Generation Logic ---

        # Create 2D grid using Mesh Line technique instead of Mesh Grid
        # This ensures consistent spacing between points

        # Step 1: Create a line of points along X axis with correct spacing
        line_x = nodes.new('GeometryNodeMeshLine')
        line_x.name = "Line X Points"
        if hasattr(line_x, "mode"):
            line_x.mode = 'OFFSET'  # Use OFFSET mode for consistent spacing
        if hasattr(line_x, "count_mode"):
            line_x.count_mode = 'TOTAL'
        line_x.location = (-700, 300)
        links.new(group_in.outputs['Count X'], line_x.inputs['Count'])

        # Create offset vector for X axis (Spacing X, 0, 0)
        combine_x_offset = nodes.new('ShaderNodeCombineXYZ')
        combine_x_offset.location = (-800, 300)
        links.new(separate_xyz.outputs['X'], combine_x_offset.inputs['X'])
        combine_x_offset.inputs['Y'].default_value = 0.0
        combine_x_offset.inputs['Z'].default_value = 0.0

        # Connect offset to line
        if "Offset" in line_x.inputs:
            links.new(combine_x_offset.outputs['Vector'], line_x.inputs['Offset'])

        # Step 2: Create a line of points along Y axis with correct spacing
        line_y = nodes.new('GeometryNodeMeshLine')
        line_y.name = "Line Y Points"
        if hasattr(line_y, "mode"):
            line_y.mode = 'OFFSET'
        if hasattr(line_y, "count_mode"):
            line_y.count_mode = 'TOTAL'
        line_y.location = (-700, 200)
        links.new(group_in.outputs['Count Y'], line_y.inputs['Count'])

        # Create offset vector for Y axis (0, Spacing Y, 0)
        combine_y_offset = nodes.new('ShaderNodeCombineXYZ')
        combine_y_offset.location = (-800, 200)
        combine_y_offset.inputs['X'].default_value = 0.0
        links.new(separate_xyz.outputs['Y'], combine_y_offset.inputs['Y'])
        combine_y_offset.inputs['Z'].default_value = 0.0

        # Connect offset to line
        if "Offset" in line_y.inputs:
            links.new(combine_y_offset.outputs['Vector'], line_y.inputs['Offset'])

        # Convert lines to points for instancing
        points_x = nodes.new('GeometryNodeMeshToPoints')
        points_x.location = (-600, 300)
        links.new(line_x.outputs['Mesh'], points_x.inputs['Mesh'])

        # Step 3: Instance line_x along line_y to create a 2D grid
        instance_x_on_y = nodes.new('GeometryNodeInstanceOnPoints')
        instance_x_on_y.name = "Instance X on Y"
        instance_x_on_y.location = (-500, 250)
        links.new(line_y.outputs['Mesh'], instance_x_on_y.inputs['Points'])
        links.new(line_x.outputs['Mesh'], instance_x_on_y.inputs['Instance'])

        # Realize the 2D grid instances
        realize_2d_grid = nodes.new('GeometryNodeRealizeInstances')
        realize_2d_grid.name = "Realize 2D Grid"
        realize_2d_grid.location = (-400, 250)
        links.new(instance_x_on_y.outputs['Instances'], realize_2d_grid.inputs['Geometry'])

        # Step 4: Create a line along Z axis with correct spacing
        line_z = nodes.new('GeometryNodeMeshLine')
        line_z.name = "Line Z Points"
        if hasattr(line_z, "mode"):
            line_z.mode = 'OFFSET'
        if hasattr(line_z, "count_mode"):
            line_z.count_mode = 'TOTAL'
        line_z.location = (-700, 100)
        links.new(group_in.outputs['Count Z'], line_z.inputs['Count'])

        # Create offset vector for Z axis (0, 0, Spacing Z)
        combine_z_offset = nodes.new('ShaderNodeCombineXYZ')
        combine_z_offset.location = (-800, 100)
        combine_z_offset.inputs['X'].default_value = 0.0
        combine_z_offset.inputs['Y'].default_value = 0.0
        links.new(separate_xyz.outputs['Z'], combine_z_offset.inputs['Z'])

        # Connect offset to line
        if "Offset" in line_z.inputs:
            links.new(combine_z_offset.outputs['Vector'], line_z.inputs['Offset'])

        # Step 5: Instance the 2D grid along the Z line to create a 3D grid
        instance_2d_on_z = nodes.new('GeometryNodeInstanceOnPoints')
        instance_2d_on_z.name = "Instance 2D on Z"
        instance_2d_on_z.location = (-300, 200)
        links.new(line_z.outputs['Mesh'], instance_2d_on_z.inputs['Points'])
        links.new(realize_2d_grid.outputs['Geometry'], instance_2d_on_z.inputs['Instance'])

        # Realize the 3D grid instances
        realize_3d_grid = nodes.new('GeometryNodeRealizeInstances')
        realize_3d_grid.name = "Realize 3D Grid"
        realize_3d_grid.location = (-200, 200)
        links.new(instance_2d_on_z.outputs['Instances'], realize_3d_grid.inputs['Geometry'])

        # Switch between 2D grid (if Count Z = 1) and 3D grid (if Count Z > 1)
        compare_z_count = nodes.new('FunctionNodeCompare')
        compare_z_count.data_type = 'INT'
        compare_z_count.operation = 'GREATER_THAN'
        compare_z_count.inputs[3].default_value = 1  # Compare with 1
        compare_z_count.location = (-300, 100)
        links.new(group_in.outputs['Count Z'], compare_z_count.inputs[2])  # Input A

        switch_points = nodes.new('GeometryNodeSwitch')
        switch_points.name = "Switch 2D/3D Points"
        switch_points.input_type = 'GEOMETRY'
        switch_points.location = (-100, 150)
        links.new(compare_z_count.outputs['Result'], switch_points.inputs['Switch'])
        links.new(realize_2d_grid.outputs['Geometry'], switch_points.inputs[False])  # Use 2D if Count Z = 1
        links.new(realize_3d_grid.outputs['Geometry'], switch_points.inputs[True])  # Use 3D if Count Z > 1

        # --- Centering Logic ---
        # Calculate offset for centering the grid based on the total size

        # Calculate X size: (Count X - 1) * Spacing X
        count_x_minus_one = nodes.new('ShaderNodeMath')
        count_x_minus_one.operation = 'SUBTRACT'
        count_x_minus_one.inputs[1].default_value = 1.0
        count_x_minus_one.location = (-400, 0)
        links.new(group_in.outputs['Count X'], count_x_minus_one.inputs[0])

        total_size_x = nodes.new('ShaderNodeMath')
        total_size_x.operation = 'MULTIPLY'
        total_size_x.location = (-300, 0)
        links.new(count_x_minus_one.outputs['Value'], total_size_x.inputs[0])
        links.new(separate_xyz.outputs['X'], total_size_x.inputs[1])

        # Calculate Y size: (Count Y - 1) * Spacing Y
        count_y_minus_one = nodes.new('ShaderNodeMath')
        count_y_minus_one.operation = 'SUBTRACT'
        count_y_minus_one.inputs[1].default_value = 1.0
        count_y_minus_one.location = (-400, -50)
        links.new(group_in.outputs['Count Y'], count_y_minus_one.inputs[0])

        total_size_y = nodes.new('ShaderNodeMath')
        total_size_y.operation = 'MULTIPLY'
        total_size_y.location = (-300, -50)
        links.new(count_y_minus_one.outputs['Value'], total_size_y.inputs[0])
        links.new(separate_xyz.outputs['Y'], total_size_y.inputs[1])

        # Calculate Z size: (Count Z - 1) * Spacing Z
        count_z_minus_one = nodes.new('ShaderNodeMath')
        count_z_minus_one.operation = 'SUBTRACT'
        count_z_minus_one.inputs[1].default_value = 1.0
        count_z_minus_one.location = (-400, -100)
        links.new(group_in.outputs['Count Z'], count_z_minus_one.inputs[0])

        total_size_z = nodes.new('ShaderNodeMath')
        total_size_z.operation = 'MULTIPLY'
        total_size_z.location = (-300, -100)
        links.new(count_z_minus_one.outputs['Value'], total_size_z.inputs[0])
        links.new(separate_xyz.outputs['Z'], total_size_z.inputs[1])

        # Calculate center offset (half of total size)
        center_offset_x = nodes.new('ShaderNodeMath')
        center_offset_x.operation = 'DIVIDE'
        center_offset_x.inputs[1].default_value = 2.0
        center_offset_x.location = (-200, 0)
        links.new(total_size_x.outputs['Value'], center_offset_x.inputs[0])

        center_offset_y = nodes.new('ShaderNodeMath')
        center_offset_y.operation = 'DIVIDE'
        center_offset_y.inputs[1].default_value = 2.0
        center_offset_y.location = (-200, -50)
        links.new(total_size_y.outputs['Value'], center_offset_y.inputs[0])

        center_offset_z = nodes.new('ShaderNodeMath')
        center_offset_z.operation = 'DIVIDE'
        center_offset_z.inputs[1].default_value = 2.0
        center_offset_z.location = (-200, -100)
        links.new(total_size_z.outputs['Value'], center_offset_z.inputs[0])

        # Combine center offset
        center_offset = nodes.new('ShaderNodeCombineXYZ')
        center_offset.location = (-100, -50)
        links.new(center_offset_x.outputs['Value'], center_offset.inputs['X'])
        links.new(center_offset_y.outputs['Value'], center_offset.inputs['Y'])
        links.new(center_offset_z.outputs['Value'], center_offset.inputs['Z'])

        # Negate for correct offset direction
        negate_center = nodes.new('ShaderNodeVectorMath')
        negate_center.operation = 'MULTIPLY'
        negate_center.inputs[1].default_value = (-1.0, -1.0, -1.0)
        negate_center.location = (0, -50)
        links.new(center_offset.outputs['Vector'], negate_center.inputs[0])

        # Create zero vector for non-centered option
        zero_vector = nodes.new('ShaderNodeCombineXYZ')
        zero_vector.inputs[0].default_value = 0.0
        zero_vector.inputs[1].default_value = 0.0
        zero_vector.inputs[2].default_value = 0.0
        zero_vector.location = (0, -100)

        # Switch between centered and non-centered based on Center Grid option
        center_switch = nodes.new('GeometryNodeSwitch')
        center_switch.input_type = 'VECTOR'
        center_switch.location = (100, -50)
        links.new(group_in.outputs['Center Grid'], center_switch.inputs[0])  # Switch
        links.new(zero_vector.outputs['Vector'], center_switch.inputs[False])  # No centering
        links.new(negate_center.outputs['Vector'], center_switch.inputs[True])  # With centering

        # Apply the centering offset to the grid points
        set_grid_center = nodes.new('GeometryNodeSetPosition')
        set_grid_center.name = "Center Grid Points"
        set_grid_center.location = (200, 100)
        links.new(switch_points.outputs[0], set_grid_center.inputs['Geometry'])
        links.new(center_switch.outputs[0], set_grid_center.inputs['Offset'])

        # Mesh to points for the final grid
        final_points = nodes.new('GeometryNodeMeshToPoints')
        final_points.location = (300, 100)
        links.new(set_grid_center.outputs['Geometry'], final_points.inputs['Mesh'])

        # Use these points for instancing our collection
        point_source = final_points.outputs['Points']

    elif cloner_type == "LINEAR":
        # Create line for linear layout
        line_node = nodes.new('GeometryNodeMeshLine')
        if hasattr(line_node, "mode"):
            line_node.mode = 'OFFSET'
        if hasattr(line_node, "count_mode"):
            line_node.count_mode = 'TOTAL'
        line_node.location = (-600, 200)

        # Link line parameters - use Count instead of Count X
        links.new(group_in.outputs['Count'], line_node.inputs['Count'])

        # Connect offset vector directly from input
        # No need to create a combined offset vector
        if "Offset" in line_node.inputs:
            links.new(group_in.outputs['Offset'], line_node.inputs['Offset'])
        elif "Resolution" in line_node.inputs:
            # Fallback for older versions - extract X component
            links.new(separate_xyz.outputs['X'], line_node.inputs['Resolution'])
        elif "Length" in line_node.inputs:
            # Fallback for older versions - extract X component
            links.new(separate_xyz.outputs['X'], line_node.inputs['Length'])

        # --- Centering Logic ---
        # Calculate total size: (Count - 1) * Offset X component
        count_minus_one = nodes.new('ShaderNodeMath')
        count_minus_one.operation = 'SUBTRACT'
        count_minus_one.inputs[1].default_value = 1.0
        count_minus_one.location = (-400, 0)
        links.new(group_in.outputs['Count'], count_minus_one.inputs[0])

        total_size = nodes.new('ShaderNodeMath')
        total_size.operation = 'MULTIPLY'
        total_size.location = (-300, 0)
        links.new(count_minus_one.outputs['Value'], total_size.inputs[0])
        links.new(separate_xyz.outputs['X'], total_size.inputs[1])

        # Calculate center offset (half of total size)
        center_offset_value = nodes.new('ShaderNodeMath')
        center_offset_value.operation = 'DIVIDE'
        center_offset_value.inputs[1].default_value = 2.0
        center_offset_value.location = (-200, 0)
        links.new(total_size.outputs['Value'], center_offset_value.inputs[0])

        # Create vector for centering (offset only in X direction)
        center_offset = nodes.new('ShaderNodeCombineXYZ')
        center_offset.location = (-100, 0)
        links.new(center_offset_value.outputs['Value'], center_offset.inputs['X'])
        center_offset.inputs['Y'].default_value = 0.0
        center_offset.inputs['Z'].default_value = 0.0

        # Negate for correct offset direction
        negate_center = nodes.new('ShaderNodeVectorMath')
        negate_center.operation = 'MULTIPLY'
        negate_center.inputs[1].default_value = (-1.0, -1.0, -1.0)
        negate_center.location = (0, 0)
        links.new(center_offset.outputs['Vector'], negate_center.inputs[0])

        # Create zero vector for non-centered option
        zero_vector = nodes.new('ShaderNodeCombineXYZ')
        zero_vector.inputs[0].default_value = 0.0
        zero_vector.inputs[1].default_value = 0.0
        zero_vector.inputs[2].default_value = 0.0
        zero_vector.location = (0, -50)

        # Switch between centered and non-centered
        center_switch = nodes.new('GeometryNodeSwitch')
        center_switch.input_type = 'VECTOR'
        center_switch.location = (100, 0)
        links.new(group_in.outputs['Center Grid'], center_switch.inputs[0])  # Switch
        links.new(zero_vector.outputs['Vector'], center_switch.inputs[False])  # No centering
        links.new(negate_center.outputs['Vector'], center_switch.inputs[True])  # With centering

        # Set position for centering
        set_position = nodes.new('GeometryNodeSetPosition')
        set_position.location = (200, 200)
        links.new(line_node.outputs['Mesh'], set_position.inputs['Geometry'])
        links.new(center_switch.outputs[0], set_position.inputs['Offset'])

        # Convert to points
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.location = (300, 200)
        links.new(set_position.outputs['Geometry'], mesh_to_points.inputs['Mesh'])

        point_source = mesh_to_points.outputs['Points']

    elif cloner_type == "CIRCLE":
        # Создаем круг точек
        circle_node = nodes.new('GeometryNodeMeshCircle')
        circle_node.location = (-400, 200)

        # Соединяем параметры круга
        # Теперь всегда используем Count для кругового клонера
        links.new(group_in.outputs['Count'], circle_node.inputs['Vertices'])

        # Теперь всегда используем Radius для кругового клонера
        links.new(group_in.outputs['Radius'], circle_node.inputs['Radius'])

        # Преобразуем меш в точки
        mesh_to_points = nodes.new('GeometryNodeMeshToPoints')
        mesh_to_points.location = (-200, 200)
        links.new(circle_node.outputs['Mesh'], mesh_to_points.inputs['Mesh'])

        point_source = mesh_to_points.outputs['Points']

    # --- Random Transform Logic ---
    # Get point indices for random generation
    index_node = nodes.new('GeometryNodeInputIndex')
    index_node.location = (350, -100)

    # Random values nodes
    # Position randomization
    random_pos_node = nodes.new('FunctionNodeRandomValue')
    random_pos_node.data_type = 'FLOAT_VECTOR'
    random_pos_node.location = (400, -150)

    # Create negative range for position
    vector_math_neg_pos = nodes.new('ShaderNodeVectorMath')
    vector_math_neg_pos.operation = 'MULTIPLY'
    vector_math_neg_pos.inputs[1].default_value = (-1.0, -1.0, -1.0)
    vector_math_neg_pos.location = (300, -150)
    links.new(group_in.outputs['Random Position'], vector_math_neg_pos.inputs[0])

    # Connect to random node
    links.new(group_in.outputs['Random Seed'], random_pos_node.inputs['Seed'])
    links.new(index_node.outputs['Index'], random_pos_node.inputs['ID'])
    links.new(vector_math_neg_pos.outputs['Vector'], random_pos_node.inputs['Min'])
    links.new(group_in.outputs['Random Position'], random_pos_node.inputs['Max'])

    # Rotation randomization
    random_rot_node = nodes.new('FunctionNodeRandomValue')
    random_rot_node.data_type = 'FLOAT_VECTOR'
    random_rot_node.location = (400, -250)

    # Create negative range for rotation
    vector_math_neg_rot = nodes.new('ShaderNodeVectorMath')
    vector_math_neg_rot.operation = 'MULTIPLY'
    vector_math_neg_rot.inputs[1].default_value = (-1.0, -1.0, -1.0)
    vector_math_neg_rot.location = (300, -250)
    links.new(group_in.outputs['Random Rotation'], vector_math_neg_rot.inputs[0])

    # Connect to random node
    links.new(group_in.outputs['Random Seed'], random_rot_node.inputs['Seed'])
    links.new(index_node.outputs['Index'], random_rot_node.inputs['ID'])
    links.new(vector_math_neg_rot.outputs['Vector'], random_rot_node.inputs['Min'])
    links.new(group_in.outputs['Random Rotation'], random_rot_node.inputs['Max'])

    # Scale randomization
    random_scale_node = nodes.new('FunctionNodeRandomValue')
    random_scale_node.data_type = 'FLOAT'  # Single float for uniform scaling
    random_scale_node.location = (400, -350)

    # Create negative range for scale
    math_neg_scale = nodes.new('ShaderNodeMath')
    math_neg_scale.operation = 'MULTIPLY'
    math_neg_scale.inputs[1].default_value = -1.0
    math_neg_scale.location = (300, -350)
    links.new(group_in.outputs['Random Scale'], math_neg_scale.inputs[0])

    # Connect to random node
    links.new(group_in.outputs['Random Seed'], random_scale_node.inputs['Seed'])
    links.new(index_node.outputs['Index'], random_scale_node.inputs['ID'])
    links.new(math_neg_scale.outputs['Value'], random_scale_node.inputs['Min'])
    links.new(group_in.outputs['Random Scale'], random_scale_node.inputs['Max'])

    # Instance on Points node - this will place the collection on each point
    instance_node = nodes.new('GeometryNodeInstanceOnPoints')
    instance_node.location = (400, 100)

    # Connect the generated points to the instances
    links.new(point_source, instance_node.inputs['Points'])

    # Connect the collection instances через переменную collection_output
    links.new(collection_output, instance_node.inputs['Instance'])

    # --- Apply Transforms to Instances ---
    # 1. Apply random position
    translate_instances = nodes.new('GeometryNodeTranslateInstances')
    translate_instances.location = (500, 100)
    links.new(instance_node.outputs['Instances'], translate_instances.inputs['Instances'])
    links.new(random_pos_node.outputs['Value'], translate_instances.inputs['Translation'])

    # 2. Apply rotation (base + random)
    add_random_rotation = nodes.new('ShaderNodeVectorMath')
    add_random_rotation.operation = 'ADD'
    add_random_rotation.location = (500, 0)
    links.new(group_in.outputs['Instance Rotation'], add_random_rotation.inputs[0])
    links.new(random_rot_node.outputs['Value'], add_random_rotation.inputs[1])

    rotate_instances = nodes.new('GeometryNodeRotateInstances')
    rotate_instances.location = (600, 100)
    links.new(translate_instances.outputs['Instances'], rotate_instances.inputs['Instances'])
    links.new(add_random_rotation.outputs['Vector'], rotate_instances.inputs['Rotation'])

    # 3. Apply scale (base + random)
    combine_xyz_scale = nodes.new('ShaderNodeCombineXYZ')
    combine_xyz_scale.location = (600, -100)
    links.new(random_scale_node.outputs['Value'], combine_xyz_scale.inputs['X'])
    links.new(random_scale_node.outputs['Value'], combine_xyz_scale.inputs['Y'])
    links.new(random_scale_node.outputs['Value'], combine_xyz_scale.inputs['Z'])

    add_random_scale = nodes.new('ShaderNodeVectorMath')
    add_random_scale.operation = 'ADD'
    add_random_scale.location = (600, -50)
    links.new(group_in.outputs['Instance Scale'], add_random_scale.inputs[0])
    links.new(combine_xyz_scale.outputs['Vector'], add_random_scale.inputs[1])

    scale_instances = nodes.new('GeometryNodeScaleInstances')
    scale_instances.location = (700, 100)
    links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
    links.new(add_random_scale.outputs['Vector'], scale_instances.inputs['Scale'])

    # Apply global transforms
    global_transform = nodes.new('GeometryNodeTransform')
    global_transform.location = (800, 100)
    links.new(scale_instances.outputs['Instances'], global_transform.inputs['Geometry'])
    links.new(group_in.outputs['Global Position'], global_transform.inputs['Translation'])
    links.new(group_in.outputs['Global Rotation'], global_transform.inputs['Rotation'])

    # Если анти-рекурсия включена, добавляем узлы для её реализации на выходе
    if use_anti_recursion:
        # Создаем узел Realize Instances для финального выхода
        final_realize = nodes.new('GeometryNodeRealizeInstances')
        final_realize.name = "Final Realize Instances"
        final_realize.location = (900, 0)

        # Создаем узел Switch для финального выхода
        final_switch = nodes.new('GeometryNodeSwitch')
        final_switch.input_type = 'GEOMETRY'
        final_switch.name = "Final Realize Switch"
        final_switch.location = (950, 0)

        # Соединяем глобальный трансформ с финальным Realize Instances
        links.new(global_transform.outputs['Geometry'], final_realize.inputs['Geometry'])

        # Настраиваем финальный переключатель
        links.new(group_in.outputs['Realize Instances'], final_switch.inputs['Switch'])
        links.new(global_transform.outputs['Geometry'], final_switch.inputs[False])  # Обычный выход
        links.new(final_realize.outputs['Geometry'], final_switch.inputs[True])  # "Реализованный" выход

        # Connect the final output to group output
        links.new(final_switch.outputs[0], group_out.inputs['Geometry'])
    else:
        # Если анти-рекурсия выключена, просто соединяем глобальный трансформ с выходом
        links.new(global_transform.outputs['Geometry'], group_out.inputs['Geometry'])

    return node_group
