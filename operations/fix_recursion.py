"""
Operators for fixing recursion depth issues in cloners.
"""

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty
from ..core.utils.cloner_effector_utils import update_cloner_with_effectors

class CLONER_OT_fix_recursion_depth(Operator):
    """Fix recursion depth issues in cloners by adding a more robust anti-recursion system"""
    bl_idname = "object.fix_cloner_recursion"
    bl_label = "Fix Recursion Depth Issues"
    bl_description = "Add a robust anti-recursion system to all cloners to fix recursion depth issues"
    bl_options = {'REGISTER', 'UNDO'}

    update_all: BoolProperty(
        name="Update All Objects",
        description="Update all objects in the scene, not just the selected ones",
        default=True
    )

    def execute(self, context):
        # Collect objects to update
        objects_to_update = []
        if self.update_all:
            objects_to_update = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        else:
            objects_to_update = [obj for obj in context.selected_objects if obj.type == 'MESH']

        # Count of updated cloners
        updated_count = 0

        # Update each object
        for obj in objects_to_update:
            # Find all geometry nodes modifiers that are cloners
            for modifier in obj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group:
                    node_group = modifier.node_group

                    # Check if this is a cloner node group
                    is_cloner = False
                    for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner"]:
                        if prefix in node_group.name:
                            is_cloner = True
                            break

                    if not is_cloner:
                        continue

                    # Apply improved anti-recursion
                    if self.apply_improved_anti_recursion_fix(node_group, context):
                        updated_count += 1
                        print(f"Applied improved anti-recursion fix to {node_group.name}")

        # Show result
        if updated_count > 0:
            self.report({'INFO'}, f"Applied improved anti-recursion fix to {updated_count} cloners")
        else:
            self.report({'INFO'}, "No cloners needed updating")

        return {'FINISHED'}

    def apply_improved_anti_recursion_fix(self, node_group, context):
        """Apply improved anti-recursion fix to the node group"""
        nodes = node_group.nodes
        links = node_group.links

        # Find the output node
        output_node = None
        for node in nodes:
            if node.type == 'GROUP_OUTPUT':
                output_node = node
                break

        if not output_node:
            return False

        # Get current anti-recursion setting
        use_anti_recursion = True
        try:
            use_anti_recursion = context.scene.use_anti_recursion
        except:
            pass

        # Check if we already have a "Realize Instances" parameter
        has_realize_param = False
        for socket in node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Realize Instances":
                has_realize_param = True
                socket.default_value = use_anti_recursion
                break

        # Add the parameter if it doesn't exist
        if not has_realize_param:
            realize_instances_input = node_group.interface.new_socket(
                name="Realize Instances",
                in_out='INPUT',
                socket_type='NodeSocketBool'
            )
            realize_instances_input.default_value = use_anti_recursion
            realize_instances_input.description = "Enable to prevent recursion depth issues when creating chains of cloners"

        # Find the group input node
        group_input = None
        for node in nodes:
            if node.type == 'GROUP_INPUT':
                group_input = node
                break

        if not group_input:
            return False

        # Remove old anti-recursion nodes if they exist
        nodes_to_remove = []
        for node in nodes:
            if node.name in ["Anti-Recursion Join Geometry", "Anti-Recursion Realize", "Anti-Recursion Switch", "Effector_Input"]:
                nodes_to_remove.append(node)

        for node in nodes_to_remove:
            nodes.remove(node)

        # Find the node that was connected to the output
        source_node = None
        source_socket = None
        
        for link in links:
            if link.to_node == output_node and link.to_socket.name == 'Geometry':
                source_node = link.from_node
                source_socket = link.from_socket
                # Remove the existing link
                links.remove(link)
                break

        if not source_node:
            return False

        # Position new nodes relative to source node
        base_x = source_node.location.x + 200
        base_y = source_node.location.y

        # Create improved anti-recursion structure
        # 1. Realize Instances node - for converting instances to geometry when needed
        realize_node = nodes.new('GeometryNodeRealizeInstances')
        realize_node.name = "Anti-Recursion Realize"
        realize_node.location = (base_x, base_y + 100)

        # 2. Switch node - for choosing between normal and anti-recursion mode
        switch_node = nodes.new('GeometryNodeSwitch')
        switch_node.input_type = 'GEOMETRY'  # Important: use GEOMETRY type
        switch_node.name = "Anti-Recursion Switch"
        switch_node.location = (base_x + 150, base_y)

        # KEY IMPROVEMENT: Ensure both Switch inputs get the same data type
        if source_socket.name == 'Instances':
            # If source outputs instances, create Realize node for False path too
            realize_false = nodes.new('GeometryNodeRealizeInstances')
            realize_false.name = "False Path Realize"
            realize_false.location = (base_x, base_y - 100)
            
            # Connect both paths through Realize nodes
            links.new(source_socket, realize_false.inputs['Geometry'])
            links.new(source_socket, realize_node.inputs['Geometry'])
            links.new(realize_false.outputs['Geometry'], switch_node.inputs[False])
            links.new(realize_node.outputs['Geometry'], switch_node.inputs[True])
        else:
            # If source already outputs geometry, connect directly to False and through Realize to True
            links.new(source_socket, realize_node.inputs['Geometry'])
            links.new(source_socket, switch_node.inputs[False])  # Direct path
            links.new(realize_node.outputs['Geometry'], switch_node.inputs[True])  # Realized path

        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Правильно подключить Switch управление
        links.new(group_input.outputs['Realize Instances'], switch_node.inputs['Switch'])
        links.new(switch_node.outputs[0], output_node.inputs['Geometry'])

        return True

    def add_anti_recursion_fix(self, node_group):
        """Legacy function - redirects to improved version"""
        return self.apply_improved_anti_recursion_fix(node_group, bpy.context)


# Function to apply anti-recursion to a new cloner
def apply_anti_recursion_to_cloner(node_group):
    """
    Применяет анти-рекурсию к новому клонеру с исправленным методом.

    Args:
        node_group: Группа узлов клонера

    Returns:
        bool: True если анти-рекурсия успешно применена, иначе False
    """
    try:
        # Получаем текущую настройку анти-рекурсии
        use_anti_recursion = True
        try:
            use_anti_recursion = bpy.context.scene.use_anti_recursion
        except:
            pass

        # Проверяем, существует ли параметр Realize Instances
        has_realize_param = False
        for socket in node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Realize Instances":
                has_realize_param = True
                socket.default_value = use_anti_recursion
                break

        # Если параметра нет, добавляем его
        if not has_realize_param:
            realize_instances_input = node_group.interface.new_socket(
                name="Realize Instances",
                in_out='INPUT',
                socket_type='NodeSocketBool'
            )
            realize_instances_input.default_value = use_anti_recursion
            realize_instances_input.description = "Включите для предотвращения проблем с глубиной рекурсии при создании цепочек клонеров"

        # Найдем узел Switch для анти-рекурсии
        switch_node = None
        group_input = None
        
        for node in node_group.nodes:
            if node.name == "Anti-Recursion Switch":
                switch_node = node
            elif node.type == 'GROUP_INPUT':
                group_input = node
        
        # Если найден Switch узел и Group Input, исправим связи
        if switch_node and group_input:
            print(f"[DEBUG] Найден Switch узел в {node_group.name}, исправляем связи...")
            
            # Удаляем любые неправильные связи к Switch входу
            wrong_links = []
            for link in node_group.links:
                if (link.to_node == switch_node and 
                    link.to_socket.name == 'Switch' and 
                    hasattr(link.from_socket, 'type') and 
                    link.from_socket.type == 'GEOMETRY'):
                    wrong_links.append(link)
            
            # Удаляем неправильные связи
            for link in wrong_links:
                node_group.links.remove(link)
                print(f"[DEBUG] Удалена неправильная связь: {link.from_node.name}.{link.from_socket.name} -> Switch")
            
            # Найдем правильный выход Realize Instances
            realize_output = None
            for output in group_input.outputs:
                if 'Realize' in output.name:
                    realize_output = output
                    break
            
            if realize_output:
                # Проверяем, не подключен ли уже правильно
                already_connected = False
                for link in node_group.links:
                    if (link.from_socket == realize_output and 
                        link.to_node == switch_node and 
                        link.to_socket.name == 'Switch'):
                        already_connected = True
                        break
                
                if not already_connected:
                    # Подключаем правильную связь
                    node_group.links.new(realize_output, switch_node.inputs['Switch'])
                    print(f"[DEBUG] Подключен {realize_output.name} к Switch входу")
                else:
                    print(f"[DEBUG] Switch вход уже правильно подключен")
                
                return True
            else:
                print(f"[DEBUG] Не найден выход Realize Instances")
                return False
        else:
            print(f"[DEBUG] Switch узел или Group Input не найдены")
            # Используем старый метод
            fixer = CLONER_OT_fix_recursion_depth()
            return fixer.apply_improved_anti_recursion_fix(node_group, bpy.context)

    except Exception as e:
        print(f"Error applying anti-recursion to cloner: {e}")
        return False


class CLONER_OT_update_all_effectors(Operator):
    """Update all cloners with effectors to fix issues with anti-recursion"""
    bl_idname = "object.update_all_cloner_effectors"
    bl_label = "Update All Cloner Effectors"
    bl_description = "Update all cloners with effectors to fix issues with anti-recursion"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Count of updated cloners
        updated_count = 0

        # Update each object
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

                # Check if the cloner has linked effectors
                if "linked_effectors" not in node_group or not node_group["linked_effectors"]:
                    continue

                # Update the cloner with effectors using improved method
                update_cloner_with_effectors(obj, modifier)
                updated_count += 1

                print(f"Updated cloner {modifier.name} with effectors")

        # Show result
        if updated_count > 0:
            self.report({'INFO'}, f"Updated {updated_count} cloners with effectors")
        else:
            self.report({'INFO'}, "No cloners with effectors found")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(CLONER_OT_fix_recursion_depth)
    bpy.utils.register_class(CLONER_OT_update_all_effectors)

def unregister():
    bpy.utils.unregister_class(CLONER_OT_update_all_effectors)
    bpy.utils.unregister_class(CLONER_OT_fix_recursion_depth)
