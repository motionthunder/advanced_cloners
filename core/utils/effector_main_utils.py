"""
Функции для работы с эффекторами.
"""

import bpy
from ...models.effectors import EFFECTOR_NODE_GROUP_PREFIXES
from .cloner_effector_utils import update_cloner_with_effectors, apply_effector_to_stacked_cloner

def link_effector_to_cloner(obj, cloner_mod, effector_mod):
    """
    Links an effector to a cloner, adding it to the linked_effectors list and configuring parameters

    Args:
        obj: Object containing the modifiers
        cloner_mod: Cloner modifier
        effector_mod: Effector modifier to link

    Returns:
        bool: True if linking successful, False in case of error
    """
    if not cloner_mod or not cloner_mod.node_group:
        print("Error: cloner doesn't have a node group")
        return False

    if not effector_mod or not effector_mod.node_group:
        print("Error: effector doesn't have a node group")
        return False

    # Check that this is actually an effector
    is_effector = False
    for prefix in EFFECTOR_NODE_GROUP_PREFIXES:
        if effector_mod.node_group.name.startswith(prefix):
            is_effector = True
            break

    if not is_effector:
        print(f"Error: {effector_mod.name} is not an effector")
        return False

    # Get the list of linked effectors
    node_group = cloner_mod.node_group
    linked_effectors = list(node_group.get("linked_effectors", []))

    # Check if the effector is already linked to the cloner
    if effector_mod.name in linked_effectors:
        print(f"Effector {effector_mod.name} is already linked to cloner {cloner_mod.name}")
        return True  # Consider this a success, since the effector is already linked

    # Add effector to the linked list
    linked_effectors.append(effector_mod.name)
    node_group["linked_effectors"] = linked_effectors

    # Activate the effector by setting its parameters
    # Enable effector display since it's now linked
    effector_mod.show_viewport = True

    # Look for Enable and Strength parameters in the effector interface
    for socket in effector_mod.node_group.interface.items_tree:
        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
            if socket.name == "Enable":
                try:
                    effector_mod[socket.identifier] = True
                except:
                    pass
            elif socket.name == "Strength":
                try:
                    effector_mod[socket.identifier] = 1.0
                except:
                    pass

    # Determine if this is a collection cloner (new method)
    is_collection_cloner = False
    if "source_type" in cloner_mod and cloner_mod["source_type"] == "COLLECTION":
        if "cloner_collection" in cloner_mod:
            is_collection_cloner = True

    # For collection cloners, we need a different approach to apply effectors
    if is_collection_cloner:
        # Not implementing collection cloner effectors yet - requires modifying the node setup
        # This would be a more complex implementation involving injecting effect nodes
        # into the node tree directly
        print("Note: Effectors on collection cloners not fully implemented yet")
        # For now, we just mark it as linked but don't actually modify the node tree
        return True

    # Update the cloner node group with effectors
    # Now the object with the cloner modifier is the duplicate,
    # which stores both the modifier and the node group
    update_cloner_with_effectors(obj, cloner_mod)

    return True

def update_effector_connection(obj, cloner_mod, effector_mod):
    """
    Updates the connection between an effector and a cloner.
    This is used to refresh the connection when the effector parameters have changed.

    Args:
        obj: Object containing the modifiers
        cloner_mod: Cloner modifier
        effector_mod: Effector modifier to update

    Returns:
        bool: True if update successful, False in case of error
    """
    if not cloner_mod or not cloner_mod.node_group:
        print("Error: cloner doesn't have a node group")
        return False

    if not effector_mod or not effector_mod.node_group:
        print("Error: effector doesn't have a node group")
        return False

    # Check that this is actually an effector
    is_effector = False
    for prefix in EFFECTOR_NODE_GROUP_PREFIXES:
        if effector_mod.node_group.name.startswith(prefix):
            is_effector = True
            break

    if not is_effector:
        print(f"Error: {effector_mod.name} is not an effector")
        return False

    # Get the list of linked effectors
    node_group = cloner_mod.node_group
    linked_effectors = list(node_group.get("linked_effectors", []))

    # Check if the effector is linked to the cloner
    if effector_mod.name not in linked_effectors:
        print(f"Error: Effector {effector_mod.name} is not linked to cloner {cloner_mod.name}")
        return False

    # Determine if this is a stacked cloner
    is_stacked_cloner = False
    if "is_stacked_cloner" in cloner_mod.node_group:
        is_stacked_cloner = cloner_mod.node_group["is_stacked_cloner"]

    # For stacked cloners, we need to update the effector connection differently
    if is_stacked_cloner:
        # Apply the effector to the stacked cloner
        apply_effector_to_stacked_cloner(obj, cloner_mod, effector_mod)
    else:
        # Update the cloner node group with all effectors
        update_cloner_with_effectors(obj, cloner_mod)

    return True
