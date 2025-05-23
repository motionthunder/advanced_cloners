"""
Utilities for duplicating and managing meshes for cloning.
Allows creating duplicates of objects for cloning,
leaving original objects unchanged.
"""

import bpy
import time
from collections import OrderedDict
from mathutils import Matrix
from typing import Dict, List, Tuple, Optional, Union

# Cache of already created duplicates for optimization
mesh_duplicates_cache = OrderedDict()
# Maximum cache size
MAX_CACHE_SIZE = 20

# Dictionary to track cloner hierarchy chains
# Maps duplicate object name to original object with cloner modifiers
cloner_hierarchy_map = {}

def create_cloner_collection(base_name="cloner"):
    """
    Creates a collection for storing cloner duplicate objects.
    
    Args:
        base_name (str): Base name for the collection
        
    Returns:
        bpy.types.Collection: Created collection
    """
    # Create unique name for collection
    collection_name = base_name
    counter = 1
    while collection_name in bpy.data.collections:
        collection_name = f"{base_name}_{counter:03d}"
        counter += 1
    
    # Create new collection
    collection = bpy.data.collections.new(collection_name)
    
    # Add collection to scene
    try:
        bpy.context.scene.collection.children.link(collection)
    except Exception as e:
        print(f"Failed to add collection to scene: {e}")
        # Try to find any collection to add it to
        for coll in bpy.data.collections:
            try:
                coll.children.link(collection)
                break
            except:
                continue
    
    return collection

def get_parent_collection(obj):
    """
    Finds the first collection containing the object.
    
    Args:
        obj (bpy.types.Object): Object to find parent collection for
        
    Returns:
        bpy.types.Collection or None: Parent collection or None if not found
    """
    for collection in bpy.data.collections:
        if obj.name in collection.objects:
            return collection
    
    # If object is in the master scene collection
    if obj.name in bpy.context.scene.collection.objects:
        return bpy.context.scene.collection
    
    return None

def get_mesh_duplicate(obj, target_collection=None, hide_original=True):
    """
    Creates a duplicate of the given object for use with cloners.
    
    Args:
        obj (bpy.types.Object): Object to duplicate 
        target_collection (bpy.types.Collection): Collection to add duplicate to
        hide_original (bool): Whether to hide the original object in viewport
        
    Returns:
        bpy.types.Object: Duplicate object
    """
    # Check if object exists
    if not obj:
        return None
    
    # Generate cache key based on object and modifier
    cache_key = (obj.name, str(id(target_collection)))
    
    # Check if we already have a duplicate for this object/collection
    if cache_key in mesh_duplicates_cache:
        # Return existing duplicate if its object still exists
        cached_obj, cached_collection = mesh_duplicates_cache[cache_key]
        if cached_obj and cached_obj.name in bpy.data.objects:
            return cached_obj
    
    # Create target collection if not provided
    if not target_collection:
        target_collection = create_cloner_collection(f"cloner_{obj.name}")
    
    # Create duplicate data based on object type
    duplicate_data = None
    if obj.type == 'MESH':
        # Duplicate mesh data
        duplicate_data = obj.data.copy()
        duplicate_data.name = f"{obj.data.name}_cloner_{int(time.time())}"
    elif obj.type == 'CURVE':
        # Duplicate curve data
        duplicate_data = obj.data.copy()
        duplicate_data.name = f"{obj.data.name}_cloner_{int(time.time())}"
    elif obj.type == 'FONT':
        # Duplicate text data
        duplicate_data = obj.data.copy()
        duplicate_data.name = f"{obj.data.name}_cloner_{int(time.time())}"
    else:
        # Unsupported object type, use original data (may cause issues)
        duplicate_data = obj.data
    
    # Create new object with duplicated data
    duplicate_obj = bpy.data.objects.new(f"{obj.name}_dup", duplicate_data)
    
    # Store reference to original object - this is critical
    duplicate_obj["original_obj"] = obj.name
    
    # Сохраняем текущее состояние видимости оригинала
    duplicate_obj["original_hide_viewport"] = obj.hide_viewport
    duplicate_obj["original_hide_render"] = obj.hide_render
    
    # Copy transformations
    duplicate_obj.matrix_world = obj.matrix_world.copy()
    
    # Copy materials if possible
    if hasattr(obj, 'material_slots') and hasattr(duplicate_obj.data, 'materials'):
        for mat_slot in obj.material_slots:
            if mat_slot.material:
                duplicate_obj.data.materials.append(mat_slot.material)
    
    # Assign appropriate collection
    if target_collection:
        # Add to target collection
        target_collection.objects.link(duplicate_obj)
    else:
        # Add to same collection(s) as original
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                collection.objects.link(duplicate_obj)
                break
        else:
            # Fallback to scene collection
            bpy.context.scene.collection.objects.link(duplicate_obj)
    
    # Hide original object if requested
    if hide_original:
        obj.hide_viewport = True
        obj.hide_render = True  # Также скрываем из рендера
    
    # Add to cache
    mesh_duplicates_cache[cache_key] = (duplicate_obj, target_collection)
    
    return duplicate_obj

def restore_original_object(duplicate_obj):
    """
    Restores original object visibility and deletes duplicate.
    
    Args:
        duplicate_obj (bpy.types.Object): Duplicate object
        
    Returns:
        bool: True if successful, False in case of error
    """
    # Check that this is actually a duplicate
    if "original_obj" not in duplicate_obj:
        return False
    
    # Find original object
    original_name = duplicate_obj["original_obj"]
    if original_name not in bpy.data.objects:
        return False
    
    original_obj = bpy.data.objects[original_name]
    
    # Clean up hierarchy chain tracking
    if duplicate_obj.name in cloner_hierarchy_map:
        del cloner_hierarchy_map[duplicate_obj.name]
    
    # Remove this duplicate from any hierarchy chains
    for obj_name, chain in cloner_hierarchy_map.items():
        updated_chain = []
        for entry in chain:
            if entry["duplicate"] != duplicate_obj.name:
                updated_chain.append(entry)
        
        if len(updated_chain) != len(chain):
            cloner_hierarchy_map[obj_name] = updated_chain
    
    # Restore visibility
    if "original_hide_viewport" in duplicate_obj:
        original_obj.hide_viewport = duplicate_obj["original_hide_viewport"]
    else:
        original_obj.hide_viewport = False
    
    if "original_hide_render" in duplicate_obj:
        original_obj.hide_render = duplicate_obj["original_hide_render"]
    
    # Remove duplicate from cache
    global mesh_duplicates_cache
    keys_to_remove = []
    for key, (obj, coll) in mesh_duplicates_cache.items():
        if obj == duplicate_obj:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        mesh_duplicates_cache.pop(key, None)
    
    # Remove duplicate data
    if duplicate_obj.type == 'MESH' and duplicate_obj.data.users == 1:
        mesh_data = duplicate_obj.data
        bpy.data.objects.remove(duplicate_obj)
        bpy.data.meshes.remove(mesh_data)
    elif duplicate_obj.type == 'CURVE' and duplicate_obj.data.users == 1:
        curve_data = duplicate_obj.data
        bpy.data.objects.remove(duplicate_obj)
        bpy.data.curves.remove(curve_data)
    elif duplicate_obj.type == 'FONT' and duplicate_obj.data.users == 1:
        text_data = duplicate_obj.data
        bpy.data.objects.remove(duplicate_obj)
        bpy.data.curves.remove(text_data)
    else:
        bpy.data.objects.remove(duplicate_obj)
    
    return True

def cleanup_empty_cloner_collections():
    """
    Deletes empty cloner collections.
    
    Returns:
        int: Number of deleted collections
    """
    count = 0
    
    # Find all cloner collections
    cloner_collections = [c for c in bpy.data.collections 
                          if c.name.startswith("cloner") or c.name.startswith("cloner_")]
    
    # Delete empty collections
    for collection in cloner_collections:
        if len(collection.objects) == 0:
            try:
                bpy.data.collections.remove(collection)
                count += 1
            except Exception as e:
                print(f"Failed to delete collection {collection.name}: {e}")
    
    return count

def get_or_create_duplicate_for_cloner(obj, cloner_modifier):
    """
    Gets or creates a duplicate for use with a cloner.
    If the cloner modifier already uses a duplicate, returns it.
    
    Args:
        obj (bpy.types.Object): Original object with cloner modifier
        cloner_modifier (bpy.types.Modifier): Cloner modifier
        
    Returns:
        bpy.types.Object: Duplicate object for use with cloner
    """
    # Check if modifier has duplicate information
    if "duplicate_obj" in cloner_modifier and cloner_modifier["duplicate_obj"] in bpy.data.objects:
        # Return existing duplicate
        return bpy.data.objects[cloner_modifier["duplicate_obj"]]
    
    # Create new collection name for duplicate
    collection_name = f"cloner_{cloner_modifier.name.replace(' ', '_').lower()}"
    
    # Check if collection already exists
    if "duplicate_collection" in cloner_modifier and cloner_modifier["duplicate_collection"] in bpy.data.collections:
        collection = bpy.data.collections[cloner_modifier["duplicate_collection"]]
    else:
        collection = create_cloner_collection(collection_name)
        cloner_modifier["duplicate_collection"] = collection.name
    
    # Проверяем специальный случай: клонер меша после клонера коллекции
    new_source_type = cloner_modifier.get("source_type", "OBJECT")
    
    # Если это первый модификатор объекта, просто создаем дубликат как обычно
    if len(obj.modifiers) <= 1:
        # Стандартное поведение - не скрываем оригинал, чтобы он был доступен для геометрии
        duplicate = get_mesh_duplicate(obj, collection, hide_original=False)
    else:
        # Проверяем, есть ли предыдущий клонер коллекции
        has_collection_cloner = False
        original_collection = None
        
        for mod in obj.modifiers:
            if mod != cloner_modifier and mod.type == 'NODES' and mod.node_group:
                # Если это клонер коллекции
                if mod.get("source_type", "") == "COLLECTION":
                    has_collection_cloner = True
                    # Пытаемся найти коллекцию
                    if "collection_to_clone" in bpy.context.scene:
                        original_collection = bpy.context.scene.collection_to_clone
                    break
        
        # Если переходим с клонера коллекции на клонер меша
        if has_collection_cloner and new_source_type == "OBJECT" and original_collection:
            # Вместо дубликата пустого объекта, создаем новый объект с геометрией
            print(f"Detected COLLECTION->OBJECT cloner chain. Creating mesh object for cloning.")
            
            # Получаем объект коллекции из имени
            coll_obj = None
            if original_collection in bpy.data.collections:
                coll_obj = bpy.data.collections[original_collection]
            
            # Создаем куб как стандартный объект по умолчанию
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
            temp_obj = bpy.context.active_object
            
            # Создаем дубликат на основе этого объекта
            duplicate = get_mesh_duplicate(temp_obj, collection, hide_original=False)
            
            # Применяем преобразования оригинального объекта
            duplicate.matrix_world = obj.matrix_world.copy()
            
            # Удаляем временный объект
            mesh_data = temp_obj.data
            bpy.data.objects.remove(temp_obj)
            
            # Пробуем удалить меш, если он больше не используется
            if mesh_data.users == 0:
                bpy.data.meshes.remove(mesh_data)
        else:
            # Стандартное поведение если нет специального случая - не скрываем оригинал
            duplicate = get_mesh_duplicate(obj, collection, hide_original=False)
    
    # Save duplicate information in modifier
    cloner_modifier["duplicate_obj"] = duplicate.name
    
    # Also store the relationship in the duplicate object to original modifier
    duplicate["source_modifier"] = cloner_modifier.name
    duplicate["source_object"] = obj.name
    duplicate["source_type"] = new_source_type  # Сохраняем тип клонера
    
    # Track hierarchy relationship for cloner chain
    # Save both the original and the cloner modifier name for later access
    if obj.name not in cloner_hierarchy_map:
        cloner_hierarchy_map[obj.name] = []
    
    # Add this duplicate to the hierarchy chain
    cloner_hierarchy_map[obj.name].append({
        "duplicate": duplicate.name,
        "modifier": cloner_modifier.name,
        "source_type": new_source_type
    })
    
    # If this object is itself a duplicate created by a cloner, maintain the chain
    if "original_obj" in obj and obj["original_obj"] in bpy.data.objects:
        original_obj_name = obj["original_obj"]
        if original_obj_name in cloner_hierarchy_map:
            # Create entry for the new duplicate if it doesn't exist
            if duplicate.name not in cloner_hierarchy_map:
                cloner_hierarchy_map[duplicate.name] = []
            
            # Copy the chain from the parent (original) object
            cloner_hierarchy_map[duplicate.name] = cloner_hierarchy_map[original_obj_name].copy()
    
    return duplicate

def get_cloner_chain_for_object(obj):
    """
    Gets the complete chain of cloners that led to this object.
    
    Args:
        obj (bpy.types.Object): Object to get cloner chain for
        
    Returns:
        list: List of dictionaries with information about each cloner in the chain
              Each dict contains: 
              - "object": The object with the cloner modifier
              - "modifier": The cloner modifier name
    """
    chain = []
    current_obj = obj
    processed_modifiers = set()  # Для предотвращения дублирования модификаторов в цепочке
    processed_collections = set()  # Для отслеживания уже обработанных коллекций
    
    # Special handling for collection cloners - check if this object might be a collection cloner
    # (usually it's a specially created empty with a specific name pattern)
    if obj.name.startswith("Cloner_") or "original_obj" in obj:
        # This is likely a collection or object cloner object
        for mod in obj.modifiers:
            # Пропускаем уже обработанные модификаторы
            mod_key = f"{obj.name}|{mod.name}"
            if mod_key in processed_modifiers:
                continue
                
            if (mod.type == 'NODES' and 
                hasattr(mod, "node_group") and 
                mod.node_group and 
                ("CollectionCloner_" in mod.node_group.name or 
                 "ObjectCloner_" in mod.node_group.name or
                 "original_collection" in mod)):
                
                # Отмечаем модификатор как обработанный
                processed_modifiers.add(mod_key)
                
                # Определяем тип клонера
                is_collection = "CollectionCloner_" in mod.node_group.name or "original_collection" in mod
                
                # This is a collection cloner
                chain.append({
                    "object": obj.name,
                    "modifier": mod.name,
                    "is_collection_cloner": is_collection
                })
                
                # Добавляем информацию о коллекции в processed_collections, если это клонер коллекции
                if is_collection and "original_collection" in mod:
                    coll_name = mod["original_collection"]
                    processed_collections.add(coll_name)
                
                # Изменённая логика для цепочки клонеров - проверяем, является ли этот модификатор частью цепочки
                is_in_chain = ("is_collection_chain" in mod or "is_chained_cloner" in mod or "chain_source_collection" in mod)
                
                if is_in_chain:
                    # Пытаемся найти предыдущий объект в цепочке
                    prev_obj_name = None
                    
                    # Предпочтительно используем "previous_cloner_object" если оно есть
                    if "previous_cloner_object" in mod:
                        prev_obj_name = mod["previous_cloner_object"]
                    
                    # Если не нашли предыдущий объект, но есть информация об исходной коллекции,
                    # пытаемся найти объект клонера, создавший эту коллекцию
                    elif "chain_source_collection" in mod:
                        source_coll_name = mod["chain_source_collection"]
                        
                        # Пропускаем уже обработанные коллекции для избежания циклов
                        if source_coll_name in processed_collections:
                            continue
                        
                        processed_collections.add(source_coll_name)
                        
                        # Ищем объект клонера, создавший эту коллекцию
                        for source_obj in bpy.data.objects:
                            if (source_obj.name.startswith("Cloner_") and 
                                hasattr(source_obj, "modifiers")):
                                for source_mod in source_obj.modifiers:
                                    if (source_mod.type == 'NODES' and 
                                        (source_mod.get("cloner_collection") == source_coll_name or
                                         source_mod.get("original_collection") == source_coll_name)):
                                        prev_obj_name = source_obj.name
                                        break
                                if prev_obj_name:
                                    break
                    
                    # Если нашли предыдущий объект, обрабатываем его
                    while prev_obj_name and prev_obj_name in bpy.data.objects:
                        prev_obj = bpy.data.objects[prev_obj_name]
                        
                        # Find the cloner modifier in this object
                        for prev_mod in prev_obj.modifiers:
                            prev_mod_key = f"{prev_obj.name}|{prev_mod.name}"
                            if prev_mod_key in processed_modifiers:
                                continue
                                
                            if (prev_mod.type == 'NODES' and 
                                hasattr(prev_mod, "node_group") and 
                                prev_mod.node_group and 
                                ("CollectionCloner_" in prev_mod.node_group.name or 
                                 "ObjectCloner_" in prev_mod.node_group.name or
                                "original_collection" in prev_mod)):
                                
                                # Отмечаем модификатор как обработанный
                                processed_modifiers.add(prev_mod_key)
                                
                                # Определяем тип клонера
                                is_prev_collection = "CollectionCloner_" in prev_mod.node_group.name or "original_collection" in prev_mod
                                
                                # Add this cloner to the chain
                                chain.append({
                                    "object": prev_obj.name,
                                    "modifier": prev_mod.name,
                                    "is_collection_cloner": is_prev_collection
                                })
                                
                                # Добавляем информацию о коллекции в processed_collections
                                if is_prev_collection and "original_collection" in prev_mod:
                                    coll_name = prev_mod["original_collection"]
                                    processed_collections.add(coll_name)
                                
                                # Проверяем, есть ли у этого модификатора информация о предыдущем клонере
                                is_prev_in_chain = ("is_collection_chain" in prev_mod or 
                                                  "is_chained_cloner" in prev_mod or 
                                                  "chain_source_collection" in prev_mod)
                                
                                # Получаем имя следующего объекта в цепочке
                                next_prev_obj_name = None
                                
                                if is_prev_in_chain:
                                    if "previous_cloner_object" in prev_mod:
                                        next_prev_obj_name = prev_mod["previous_cloner_object"]
                                    elif "chain_source_collection" in prev_mod:
                                        source_coll_name = prev_mod["chain_source_collection"]
                                        
                                        # Пропускаем уже обработанные коллекции для избежания циклов
                                        if source_coll_name in processed_collections:
                                            break
                                        
                                        processed_collections.add(source_coll_name)
                                        
                                        # Ищем объект клонера, создавший эту коллекцию
                                        for source_obj in bpy.data.objects:
                                            if (source_obj.name.startswith("Cloner_") and 
                                                hasattr(source_obj, "modifiers")):
                                                for source_mod in source_obj.modifiers:
                                                    if (source_mod.type == 'NODES' and 
                                                        (source_mod.get("cloner_collection") == source_coll_name or
                                                         source_mod.get("original_collection") == source_coll_name)):
                                                        next_prev_obj_name = source_obj.name
                                                        break
                                                if next_prev_obj_name:
                                                    break
                                
                                # Продолжаем цепочку, если нашли следующий объект
                                if next_prev_obj_name:
                                    prev_obj_name = next_prev_obj_name
                                    break
                                else:
                                    # Выходим из цикла, если не нашли следующий объект
                                    prev_obj_name = None
                                    break
                            else:
                                # Если не нашли подходящий модификатор, продолжаем поиск
                                continue
                        else:
                            # Если не нашли ни одного подходящего модификатора в объекте, завершаем поиск
                            prev_obj_name = None
    
    # First check for cloners applied directly to this object
    # (happens when a cloner is applied to an object that's already a result of cloning)
    if current_obj.modifiers:
        for mod in current_obj.modifiers:
            # Пропускаем уже обработанные модификаторы
            mod_key = f"{current_obj.name}|{mod.name}"
            if mod_key in processed_modifiers:
                continue
                
            if (mod.type == 'NODES' and 
                hasattr(mod, "node_group") and 
                mod.node_group and 
                ("is_chained_cloner" in mod or "chain_source_collection" in mod or 
                 (mod.node_group and "ObjectCloner_" in mod.node_group.name))):
                
                # Отмечаем модификатор как обработанный
                processed_modifiers.add(mod_key)
                
                # This is a cloner applied directly to a clone
                chain.append({
                    "object": current_obj.name,
                    "modifier": mod.name,
                    "is_chained_cloner": True,
                    "is_collection_cloner": "original_collection" in mod
                })
    
    # Now traverse up the hierarchy chain for cloners that created duplicates
    while "original_obj" in current_obj:
        original_name = current_obj["original_obj"]
        if original_name in bpy.data.objects:
            original_obj = bpy.data.objects[original_name]
            
            # If we have direct source info, use it
            if "source_modifier" in current_obj and "source_object" in current_obj:
                source_mod_name = current_obj["source_modifier"]
                source_obj_name = current_obj["source_object"]
                
                # Verify that the source object and modifier still exist
                if source_obj_name in bpy.data.objects:
                    source_obj = bpy.data.objects[source_obj_name]
                    if source_mod_name in source_obj.modifiers:
                        # Пропускаем уже обработанные модификаторы
                        mod_key = f"{source_obj_name}|{source_mod_name}"
                        if mod_key not in processed_modifiers:
                            mod = source_obj.modifiers[source_mod_name]
                            is_collection = False
                            
                            # Определяем тип клонера
                            if mod.node_group:
                                is_collection = "CollectionCloner_" in mod.node_group.name or "original_collection" in mod
                            
                            processed_modifiers.add(mod_key)
                            chain.append({
                                "object": source_obj_name,
                                "modifier": source_mod_name,
                                "is_collection_cloner": is_collection
                            })
                        
                        # Move up the chain to the source object
                        current_obj = source_obj
                        continue
            
            # Fallback: Find the modifier on the original object that created this duplicate
            found = False
            for mod in original_obj.modifiers:
                # Пропускаем уже обработанные модификаторы
                mod_key = f"{original_obj.name}|{mod.name}"
                if mod_key in processed_modifiers:
                    continue
                    
                if mod.type == 'NODES' and hasattr(mod, "node_group") and mod.node_group:
                    if "duplicate_obj" in mod and mod["duplicate_obj"] == current_obj.name:
                        # Определяем тип клонера
                        is_collection = False
                        if mod.node_group:
                            is_collection = "CollectionCloner_" in mod.node_group.name or "original_collection" in mod
                        
                        processed_modifiers.add(mod_key)
                        chain.append({
                            "object": original_obj.name,
                            "modifier": mod.name,
                            "is_collection_cloner": is_collection,
                            "is_chained_cloner": "is_chained_cloner" in mod or "chain_source_collection" in mod or 
                                                (mod.node_group and "ObjectCloner_" in mod.node_group.name)
                        })
                        found = True
                        break
            
            # Move up the chain
            if not found:
                # Even if we don't find the exact modifier, we still want to continue up the chain
                print(f"Warning: Could not find modifier that created {current_obj.name}")
            
            current_obj = original_obj
        else:
            # Break if original no longer exists
            break
    
    # Reverse the chain to get it in creation order,
    # with the most recent additions at the end (our directly applied cloners)
    chain.reverse()
    return chain
