"""
Utilities for managing anti-recursion settings in cloners.
"""

import bpy
import importlib

def update_anti_recursion_for_all_cloners(context):
    """
    Update the Realize Instances parameter for all cloners based on the current anti-recursion setting.
    Uses improved anti-recursion system that fixes red connections and effector issues.

    Args:
        context: Blender context
    """
    # Get the current anti-recursion setting
    use_anti_recursion = context.scene.use_anti_recursion

    # Import necessary functions
    try:
        cloner_effector_utils = importlib.import_module("advanced_cloners.core.utils.cloner_effector_utils")
        update_cloner_with_effectors = cloner_effector_utils.update_cloner_with_effectors
        
        fix_recursion = importlib.import_module("advanced_cloners.operations.fix_recursion")
        apply_anti_recursion_to_cloner = fix_recursion.apply_anti_recursion_to_cloner
    except ImportError as e:
        print(f"[ERROR] Failed to import required modules: {e}")
        return

    # Update all objects in the scene
    updated_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        # Find all geometry nodes modifiers that are cloners
        for modifier in obj.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue

            node_group = modifier.node_group

            # Check if this is a cloner node group
            is_cloner = False
            for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner", "ObjectCloner"]:
                if prefix in node_group.name:
                    is_cloner = True
                    break

            if not is_cloner:
                continue

            # Update or add the Realize Instances parameter
            has_realize_param = False
            for socket in node_group.interface.items_tree:
                if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Realize Instances":
                    # Update the parameter value
                    socket.default_value = use_anti_recursion
                    has_realize_param = True
                    break

            # If the parameter doesn't exist, apply anti-recursion system
            if not has_realize_param:
                if apply_anti_recursion_to_cloner(node_group):
                    print(f"[DEBUG] Applied improved anti-recursion to {node_group.name}")
                    updated_count += 1

            # Check if we need to update the node structure
            has_anti_recursion_switch = False
            has_problematic_structure = False
            
            for node in node_group.nodes:
                if node.name == "Anti-Recursion Switch":
                    has_anti_recursion_switch = True
                    
                    # Check for problematic old structure (Join Geometry node)
                    for other_node in node_group.nodes:
                        if other_node.name == "Anti-Recursion Join Geometry":
                            has_problematic_structure = True
                            break
                    
                    break

            # If we have old problematic structure, update it
            if has_anti_recursion_switch and has_problematic_structure:
                print(f"[DEBUG] Updating problematic anti-recursion structure in {node_group.name}")
                if apply_anti_recursion_to_cloner(node_group):
                    updated_count += 1

            # Update cloner with effectors if it has any
            if "linked_effectors" in node_group and node_group["linked_effectors"]:
                try:
                    print(f"[DEBUG] Updating effectors for {node_group.name}")
                    update_cloner_with_effectors(obj, modifier)
                except Exception as e:
                    print(f"[ERROR] Failed to update effectors for {node_group.name}: {e}")

    # Force update the view
    context.view_layer.update()
    
    if updated_count > 0:
        print(f"[INFO] Updated {updated_count} cloners with improved anti-recursion system")


def update_anti_recursion_callback(self, context):
    """
    Callback function for the anti-recursion property.

    Args:
        self: The property owner (unused but required by Blender)
        context: Blender context
    """
    # Update all cloners when the anti-recursion setting changes
    update_anti_recursion_for_all_cloners(context)
    return None


def update_stacked_modifiers_callback(self, context):
    """
    Callback function for the stacked modifiers property.

    Args:
        self: The property owner (unused but required by Blender)
        context: Blender context
    """
    # Stacked modifiers can now work together with anti-recursion
    return None


# Additional utility functions for the improved system

def check_cloner_anti_recursion_health(node_group):
    """
    Checks if a cloner's anti-recursion system is healthy (no red connections).
    
    Args:
        node_group: The cloner node group to check
        
    Returns:
        dict: Health status with details
    """
    health_status = {
        'healthy': True,
        'issues': [],
        'has_anti_recursion': False,
        'has_effectors': False
    }
    
    # Check for anti-recursion switch
    switch_node = None
    for node in node_group.nodes:
        if node.name == "Anti-Recursion Switch":
            switch_node = node
            health_status['has_anti_recursion'] = True
            break
    
    if switch_node:
        # Check for type mismatches in switch inputs
        false_input_type = None
        true_input_type = None
        
        for link in node_group.links:
            if link.to_node == switch_node:
                if link.to_socket == switch_node.inputs[False]:
                    false_input_type = link.from_socket.name
                elif link.to_socket == switch_node.inputs[True]:
                    true_input_type = link.from_socket.name
        
        if false_input_type and true_input_type and false_input_type != true_input_type:
            health_status['healthy'] = False
            health_status['issues'].append(f"Type mismatch in Switch: False={false_input_type}, True={true_input_type}")
    
    # Check for problematic nodes
    problematic_nodes = ["Anti-Recursion Join Geometry", "Effector_Input"]
    for node in node_group.nodes:
        if node.name in problematic_nodes:
            health_status['healthy'] = False
            health_status['issues'].append(f"Found problematic node: {node.name}")
    
    # Check for effectors
    if "linked_effectors" in node_group and node_group["linked_effectors"]:
        health_status['has_effectors'] = True
        
        # Check if effectors are properly connected
        effector_nodes = [n for n in node_group.nodes if n.name.startswith('Effector_')]
        if len(effector_nodes) != len(node_group["linked_effectors"]):
            health_status['healthy'] = False
            health_status['issues'].append(f"Effector count mismatch: {len(effector_nodes)} nodes vs {len(node_group['linked_effectors'])} linked")
    
    return health_status


def fix_unhealthy_cloner(node_group, context=None):
    """
    Attempts to fix an unhealthy cloner's anti-recursion system.
    
    Args:
        node_group: The cloner node group to fix
        context: Blender context (optional)
        
    Returns:
        bool: True if fix was successful
    """
    if context is None:
        context = bpy.context
    
    try:
        # Import and apply improved anti-recursion
        fix_recursion = importlib.import_module("advanced_cloners.operations.fix_recursion")
        apply_anti_recursion_to_cloner = fix_recursion.apply_anti_recursion_to_cloner
        
        return apply_anti_recursion_to_cloner(node_group)
    except Exception as e:
        print(f"[ERROR] Failed to fix unhealthy cloner: {e}")
        return False


def diagnose_all_cloners(context):
    """
    Diagnoses all cloners in the scene and reports their health status.
    
    Args:
        context: Blender context
        
    Returns:
        dict: Summary of cloner health across the scene
    """
    summary = {
        'total_cloners': 0,
        'healthy_cloners': 0,
        'unhealthy_cloners': 0,
        'cloners_with_effectors': 0,
        'issues_found': []
    }
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        for modifier in obj.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            
            node_group = modifier.node_group
            
            # Check if this is a cloner
            is_cloner = False
            for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner", "ObjectCloner"]:
                if prefix in node_group.name:
                    is_cloner = True
                    break
            
            if not is_cloner:
                continue
            
            summary['total_cloners'] += 1
            
            # Check health
            health = check_cloner_anti_recursion_health(node_group)
            
            if health['healthy']:
                summary['healthy_cloners'] += 1
            else:
                summary['unhealthy_cloners'] += 1
                summary['issues_found'].extend([f"{node_group.name}: {issue}" for issue in health['issues']])
            
            if health['has_effectors']:
                summary['cloners_with_effectors'] += 1
    
    return summary
