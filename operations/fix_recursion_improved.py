"""
Improved operators for fixing recursion depth issues in cloners.
"""

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty
from ..core.utils.cloner_effector_utils import update_cloner_with_effectors
from ..core.utils.anti_recursion_utils import diagnose_all_cloners, fix_unhealthy_cloner

class CLONER_OT_fix_recursion_depth_improved(Operator):
    """Fix recursion depth issues using improved anti-recursion system"""
    bl_idname = "object.fix_cloner_recursion_improved"
    bl_label = "Fix Recursion Issues (Improved)"
    bl_description = "Apply improved anti-recursion system that fixes red connections and effector issues"
    bl_options = {'REGISTER', 'UNDO'}

    update_all: BoolProperty(
        name="Update All Objects",
        description="Update all objects in the scene, not just the selected ones",
        default=True
    )

    def apply_improved_anti_recursion_fix(self, node_group, context):
        """
        Применяет улучшенную систему анти-рекурсии, которая совместима с эффекторами.

        Args:
            node_group: Группа узлов клонера
            context: Контекст Blender

        Returns:
            bool: True если исправление применено успешно
        """
        nodes = node_group.nodes
        links = node_group.links

        print(f"[DEBUG] Применение улучшенной анти-рекурсии к {node_group.name}")

        # Найти выходной узел
        output_node = None
        for node in nodes:
            if node.type == 'GROUP_OUTPUT':
                output_node = node
                break

        if not output_node:
            print("[ERROR] Не найден выходной узел")
            return False

        # Найти входной узел группы
        group_input = None
        for node in nodes:
            if node.type == 'GROUP_INPUT':
                group_input = node
                break

        if not group_input:
            print("[ERROR] Не найден входной узел группы")
            return False

        # Получить настройку анти-рекурсии
        use_anti_recursion = True
        try:
            use_anti_recursion = context.scene.use_anti_recursion
        except:
            pass

        # Проверить наличие параметра Realize Instances
        has_realize_param = False
        for socket in node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Realize Instances":
                has_realize_param = True
                socket.default_value = use_anti_recursion
                break

        # Добавить параметр если его нет
        if not has_realize_param:
            realize_instances_input = node_group.interface.new_socket(
                name="Realize Instances",
                in_out='INPUT',
                socket_type='NodeSocketBool'
            )
            realize_instances_input.default_value = use_anti_recursion
            realize_instances_input.description = "Enable to prevent recursion depth issues when creating chains of cloners"
            print("[DEBUG] Добавлен параметр Realize Instances")

        # Удалить проблемные узлы старой системы анти-рекурсии
        problematic_nodes = []
        for node in nodes:
            if node.name in ["Anti-Recursion Join Geometry", "Effector_Input"]:
                problematic_nodes.append(node)
                print(f"[DEBUG] Найден проблемный узел: {node.name}")

        # Сохранить связи перед удалением проблемных узлов
        connections_to_restore = []
        for node in problematic_nodes:
            # Найти что было подключено к этому узлу
            for link in links:
                if link.to_node == node:
                    connections_to_restore.append((link.from_node, link.from_socket))
                elif link.from_node == node:
                    connections_to_restore.append((link.to_node, link.to_socket))

        # Удалить проблемные узлы
        for node in problematic_nodes:
            nodes.remove(node)
            print(f"[DEBUG] Удален проблемный узел: {node.name}")

        # Найти или создать узел Switch для анти-рекурсии
        switch_node = None
        for node in nodes:
            if node.name == "Anti-Recursion Switch":
                switch_node = node
                break

        if not switch_node:
            # Создать новый Switch узел
            switch_node = nodes.new('GeometryNodeSwitch')
            switch_node.input_type = 'GEOMETRY'
            switch_node.name = "Anti-Recursion Switch"

            # Позиционировать узел
            switch_node.location = (output_node.location.x - 200, output_node.location.y)
            print("[DEBUG] Создан новый Switch узел")

        # Найти узел, который должен быть подключен к выходу (обычно это последний в цепочке)
        source_node = None
        source_socket = None

        # Сначала проверим, что подключено к выходу сейчас
        for link in links:
            if link.to_node == output_node and link.to_socket.name == 'Geometry':
                if link.from_node != switch_node:  # Если это не наш Switch
                    source_node = link.from_node
                    source_socket = link.from_socket
                    links.remove(link)  # Удаляем старую связь
                    break

        # Если не нашли прямую связь, ищем среди восстановленных связей
        if not source_node and connections_to_restore:
            # Берем последнюю найденную связь как источник
            for from_node, from_socket in connections_to_restore:
                if hasattr(from_socket, 'type') and from_socket.type == 'GEOMETRY':
                    source_node = from_node
                    source_socket = from_socket
                    break

        if source_node and source_socket:
            print(f"[DEBUG] Найден исходный узел: {source_node.name}")

            # Создать узел Realize Instances для True пути
            realize_node = None
            for node in nodes:
                if node.name == "Anti-Recursion Realize":
                    realize_node = node
                    break

            if not realize_node:
                realize_node = nodes.new('GeometryNodeRealizeInstances')
                realize_node.name = "Anti-Recursion Realize"
                realize_node.location = (switch_node.location.x - 150, switch_node.location.y + 100)
                print("[DEBUG] Создан узел Realize Instances")

            # Подключить источник к обоим путям Switch
            links.new(source_socket, switch_node.inputs[False])  # Прямой путь (без реализации)
            links.new(source_socket, realize_node.inputs['Geometry'])  # Путь через реализацию
            links.new(realize_node.outputs['Geometry'], switch_node.inputs[True])  # Реализованный путь

            print("[DEBUG] Подключены пути Switch узла")

        # Подключить управление Switch от параметра Realize Instances
        realize_output = None
        for output in group_input.outputs:
            if 'Realize' in output.name:
                realize_output = output
                break

        if realize_output:
            # Удалить старые связи к Switch управлению
            links_to_remove = []
            for link in links:
                if link.to_node == switch_node and link.to_socket.name == 'Switch':
                    links_to_remove.append(link)

            for link in links_to_remove:
                links.remove(link)

            # Подключить правильное управление
            links.new(realize_output, switch_node.inputs['Switch'])
            print("[DEBUG] Подключено управление Switch")

        # Подключить Switch к выходу
        links.new(switch_node.outputs[0], output_node.inputs['Geometry'])
        print("[DEBUG] Switch подключен к выходу")

        return True

    def execute(self, context):
        # First diagnose all cloners
        print("[INFO] Диагностика клонеров...")
        summary = diagnose_all_cloners(context)

        print(f"[INFO] Найдено {summary['total_cloners']} клонеров:")
        print(f"  - Здоровых: {summary['healthy_cloners']}")
        print(f"  - Требующих исправления: {summary['unhealthy_cloners']}")
        print(f"  - С эффекторами: {summary['cloners_with_effectors']}")

        if summary['issues_found']:
            print("[INFO] Найдены проблемы:")
            for issue in summary['issues_found']:
                print(f"  - {issue}")

        # Собираем объекты для обновления
        objects_to_update = []
        if self.update_all:
            objects_to_update = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        else:
            objects_to_update = [obj for obj in context.selected_objects if obj.type == 'MESH']

        # Счетчик обновленных клонеров
        updated_count = 0

        # Обновляем каждый объект
        for obj in objects_to_update:
            for modifier in obj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group:
                    node_group = modifier.node_group

                    # Проверяем, является ли это клонером
                    is_cloner = False
                    for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner", "ObjectCloner"]:
                        if prefix in node_group.name:
                            is_cloner = True
                            break

                    if not is_cloner:
                        continue

                    # Применяем улучшенную анти-рекурсию напрямую
                    if self.apply_improved_anti_recursion_fix(node_group, context):
                        updated_count += 1
                        print(f"[INFO] Применена улучшенная анти-рекурсия к {node_group.name}")

                        # Обновляем эффекторы, если они есть
                        if "linked_effectors" in node_group and node_group["linked_effectors"]:
                            try:
                                update_cloner_with_effectors(obj, modifier)
                                print(f"[INFO] Обновлены эффекторы для {node_group.name}")
                            except Exception as e:
                                print(f"[ERROR] Не удалось обновить эффекторы: {e}")

        # Показываем результат
        if updated_count > 0:
            self.report({'INFO'}, f"Успешно улучшено {updated_count} клонеров")
            print(f"[SUCCESS] Улучшено {updated_count} клонеров с новой системой анти-рекурсии")
        else:
            self.report({'INFO'}, "Все клонеры уже здоровы")
            print("[INFO] Все клонеры уже используют улучшенную систему")

        return {'FINISHED'}


class CLONER_OT_diagnose_cloners(Operator):
    """Diagnose all cloners for anti-recursion issues"""
    bl_idname = "object.diagnose_cloners"
    bl_label = "Diagnose Cloners"
    bl_description = "Check all cloners for anti-recursion and effector issues"
    bl_options = {'REGISTER'}

    def execute(self, context):
        summary = diagnose_all_cloners(context)

        message_lines = [
            f"Found {summary['total_cloners']} cloners in scene:",
            f"• Healthy: {summary['healthy_cloners']}",
            f"• Need fixing: {summary['unhealthy_cloners']}",
            f"• With effectors: {summary['cloners_with_effectors']}"
        ]

        if summary['unhealthy_cloners'] > 0:
            message_lines.append("Issues found:")
            for issue in summary['issues_found'][:5]:  # Show first 5 issues
                message_lines.append(f"• {issue}")
            if len(summary['issues_found']) > 5:
                message_lines.append(f"• ... and {len(summary['issues_found']) - 5} more")

        # Print detailed report to console
        print("\n" + "="*50)
        print("CLONER DIAGNOSIS REPORT")
        print("="*50)
        for line in message_lines:
            print(line)
        print("="*50 + "\n")

        # Show summary in UI
        if summary['unhealthy_cloners'] > 0:
            self.report({'WARNING'}, f"Found {summary['unhealthy_cloners']} cloners that need fixing")
        else:
            self.report({'INFO'}, "All cloners are healthy")

        return {'FINISHED'}


# Keep original classes for compatibility
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
        # Redirect to improved version
        improved_op = CLONER_OT_fix_recursion_depth_improved()
        improved_op.update_all = self.update_all
        return improved_op.execute(context)


def apply_anti_recursion_to_cloner(node_group):
    """
    Applies improved anti-recursion to a new cloner.

    Args:
        node_group: The cloner node group

    Returns:
        bool: True if anti-recursion was successfully applied, False otherwise
    """
    try:
        # Get current anti-recursion setting
        use_anti_recursion = True
        try:
            use_anti_recursion = bpy.context.scene.use_anti_recursion
        except:
            pass

        # Check if the Realize Instances parameter already exists
        has_realize_param = False
        for socket in node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Realize Instances":
                has_realize_param = True
                socket.default_value = use_anti_recursion
                break

        # If the parameter doesn't exist, add it
        if not has_realize_param:
            realize_instances_input = node_group.interface.new_socket(
                name="Realize Instances",
                in_out='INPUT',
                socket_type='NodeSocketBool'
            )
            realize_instances_input.default_value = use_anti_recursion
            realize_instances_input.description = "Enable to prevent recursion depth issues when creating chains of cloners"

        # Apply improved anti-recursion fix
        fixer = CLONER_OT_fix_recursion_depth_improved()
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
                try:
                    update_cloner_with_effectors(obj, modifier)
                    updated_count += 1
                    print(f"Updated cloner {modifier.name} with effectors")
                except Exception as e:
                    print(f"Error updating cloner {modifier.name}: {e}")

        # Show result
        if updated_count > 0:
            self.report({'INFO'}, f"Updated {updated_count} cloners with effectors")
        else:
            self.report({'INFO'}, "No cloners with effectors found")

        return {'FINISHED'}


class CLONER_OT_fix_red_connections(Operator):
    """Fix red connections in Anti-Recursion Switch nodes"""
    bl_idname = "object.fix_red_connections"
    bl_label = "Fix Red Connections"
    bl_description = "Fix red connections in Anti-Recursion Switch nodes by properly connecting boolean control"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fixed_count = 0

        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue

            for modifier in obj.modifiers:
                if modifier.type != 'NODES' or not modifier.node_group:
                    continue

                node_group = modifier.node_group

                # Проверить, является ли это клонером
                is_cloner = False
                for prefix in ["GridCloner", "LinearCloner", "CircleCloner", "CollectionCloner", "ObjectCloner"]:
                    if prefix in node_group.name:
                        is_cloner = True
                        break

                if not is_cloner:
                    continue

                # Найти узел Anti-Recursion Switch
                switch_node = None
                for node in node_group.nodes:
                    if node.name == "Anti-Recursion Switch":
                        switch_node = node
                        break

                if not switch_node:
                    continue

                # Проверить наличие неправильных связей
                has_wrong_connection = False
                wrong_links = []

                for link in node_group.links:
                    if (link.to_node == switch_node and
                        link.to_socket.name == 'Switch' and
                        hasattr(link.from_socket, 'type') and
                        link.from_socket.type == 'GEOMETRY'):
                        has_wrong_connection = True
                        wrong_links.append(link)

                if not has_wrong_connection:
                    continue

                # Исправить связи
                print(f"[FIX] Fixing red connections in {node_group.name}")

                # Найти Group Input
                group_input = None
                for node in node_group.nodes:
                    if node.type == 'GROUP_INPUT':
                        group_input = node
                        break

                if not group_input:
                    continue

                # Удалить неправильные связи
                for link in wrong_links:
                    node_group.links.remove(link)
                    print(f"[FIX] Removed wrong link: {link.from_node.name}.{link.from_socket.name} -> Switch")

                # Найти правильный выход Realize Instances
                realize_output = None
                for output in group_input.outputs:
                    if 'Realize' in output.name:
                        realize_output = output
                        break

                if realize_output:
                    # Подключить правильную связь
                    node_group.links.new(realize_output, switch_node.inputs['Switch'])
                    print(f"[FIX] Connected {realize_output.name} to Switch input")
                    fixed_count += 1

        if fixed_count > 0:
            self.report({'INFO'}, f"Fixed red connections in {fixed_count} cloners")
        else:
            self.report({'INFO'}, "No red connections found")

        return {'FINISHED'}


class CLONER_OT_fix_effector_issues(Operator):
    """Fix issues with effectors on cloners with anti-recursion"""
    bl_idname = "object.fix_effector_issues"
    bl_label = "Fix Effector Issues"
    bl_description = "Fix issues with effectors not working on cloners with anti-recursion enabled"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fixed_count = 0

        # Сначала исправляем анти-рекурсию
        fixer = CLONER_OT_fix_recursion_depth_improved()
        fixer.update_all = True
        result = fixer.execute(context)

        if result == {'FINISHED'}:
            # Затем обновляем все эффекторы
            effector_updater = CLONER_OT_update_all_effectors()
            effector_result = effector_updater.execute(context)

            if effector_result == {'FINISHED'}:
                self.report({'INFO'}, "Исправлены проблемы с эффекторами и анти-рекурсией")
                return {'FINISHED'}

        self.report({'WARNING'}, "Не удалось полностью исправить проблемы")
        return {'CANCELLED'}


def register():
    bpy.utils.register_class(CLONER_OT_fix_recursion_depth)
    bpy.utils.register_class(CLONER_OT_fix_recursion_depth_improved)
    bpy.utils.register_class(CLONER_OT_diagnose_cloners)
    bpy.utils.register_class(CLONER_OT_update_all_effectors)
    bpy.utils.register_class(CLONER_OT_fix_red_connections)
    bpy.utils.register_class(CLONER_OT_fix_effector_issues)

def unregister():
    bpy.utils.unregister_class(CLONER_OT_fix_effector_issues)
    bpy.utils.unregister_class(CLONER_OT_fix_red_connections)
    bpy.utils.unregister_class(CLONER_OT_update_all_effectors)
    bpy.utils.unregister_class(CLONER_OT_diagnose_cloners)
    bpy.utils.unregister_class(CLONER_OT_fix_recursion_depth_improved)
    bpy.utils.unregister_class(CLONER_OT_fix_recursion_depth)
