"""
Functions for creating and managing node groups.
"""

import bpy

def create_independent_node_group(template_creator_func, base_node_name):
    """Создает независимую копию группы узлов"""
    # Создаем базовую группу узлов
    template_node_group = template_creator_func()
    if template_node_group is None:
        return None
    
    # Создаем независимую копию
    try:
        independent_node_group = template_node_group.copy()
    except Exception as e:
        print(f"Failed to copy node group: {e}")
        if template_node_group.users == 0:
            try:
                bpy.data.node_groups.remove(template_node_group, do_unlink=True)
            except Exception as remove_e:
                print(f"Warning: Could not remove template node group: {remove_e}")
        return None
    
    # Удаляем шаблон или переименовываем его
    if template_node_group.users == 0:
        try:
            bpy.data.node_groups.remove(template_node_group, do_unlink=True)
        except Exception as e:
            print(f"Warning: Could not remove template node group: {e}")
    else:
        template_node_group.name += ".template"
    
    # Создаем уникальное имя для копии
    unique_node_name = base_node_name
    counter = 1
    while unique_node_name in bpy.data.node_groups:
        unique_node_name = f"{base_node_name}.{counter:03d}"
        counter += 1
    independent_node_group.name = unique_node_name
    
    return independent_node_group
