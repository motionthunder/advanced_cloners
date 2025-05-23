import bpy
import bmesh
from ...core.common.constants import CLONER_MOD_NAMES
from ...core.utils.collection_cloner import create_collection_cloner_nodetree

from .common_utils import find_layer_collection
from .params_utils import (
    setup_grid_cloner_params,
    setup_linear_cloner_params,
    setup_circle_cloner_params
)

def create_collection_cloner(context, cloner_type, target_collection_name, use_custom_group=True):
    # Параметр use_custom_group сохранен для обратной совместимости, но больше не используется

    """
    Создает клонер для коллекции.

    Args:
        context: Контекст Blender
        cloner_type: Тип клонера (GRID, LINEAR, CIRCLE)
        target_collection_name: Имя коллекции для клонирования
        use_custom_group: Использовать кастомную группу узлов

    Returns:
        bool: True если клонер успешно создан, False в случае ошибки
    """
    try:
        # Get target collection
        target_collection = bpy.data.collections[target_collection_name]

        # Check if collection has objects
        if len(target_collection.objects) == 0:
            print("Selected collection is empty")
            return False

        # Get base modifier name
        base_mod_name = CLONER_MOD_NAMES[cloner_type]

        # Проверяем, является ли коллекция результатом клонера
        is_cloner_collection = target_collection.name.startswith("cloner_")
        previous_cloner_object = None

        if is_cloner_collection:
            # Сначала проверим, хранится ли информация о клонере в самой коллекции
            if hasattr(target_collection, "get") and target_collection.get("cloner_obj") and target_collection.get("cloner_obj") in bpy.data.objects:
                # Если есть прямая ссылка на объект клонер в коллекции
                previous_cloner_object = bpy.data.objects[target_collection.get("cloner_obj")]
            else:
                # Если нет прямой ссылки, ищем объект клонера методом перебора
                for obj in bpy.data.objects:
                    if (obj.name.startswith("Cloner_") and
                        hasattr(obj, "modifiers") and
                        any(mod.type == 'NODES' and
                            (mod.get("cloner_collection") == target_collection.name or
                             mod.get("original_collection") == target_collection.name)
                            for mod in obj.modifiers)):
                        previous_cloner_object = obj
                        break

        # Create unique name for the cloner object
        cloner_name = f"Cloner_{target_collection.name}"
        counter = 1
        while cloner_name in bpy.data.objects:
            cloner_name = f"Cloner_{target_collection.name}_{counter:03d}"
            counter += 1

        # Create empty mesh as base for the cloner
        mesh = bpy.data.meshes.new(f"{cloner_name}_Mesh")
        cloner_obj = bpy.data.objects.new(cloner_name, mesh)

        # Create collection for the cloner if needed
        cloner_collection_name = f"cloner_{cloner_type.lower()}_{target_collection.name}"
        counter = 1
        while cloner_collection_name in bpy.data.collections:
            cloner_collection_name = f"cloner_{cloner_type.lower()}_{target_collection.name}_{counter:03d}"
            counter += 1

        cloner_collection = bpy.data.collections.new(cloner_collection_name)

        # Сохраняем ссылку на объект клонера в коллекции
        cloner_collection["cloner_obj"] = cloner_obj.name

        # Add cloner to the collection and make sure it's linked to the scene
        cloner_collection.objects.link(cloner_obj)

        # Убедимся, что коллекция клонера добавлена в сцену
        if cloner_collection.name not in bpy.context.scene.collection.children:
            try:
                bpy.context.scene.collection.children.link(cloner_collection)
            except Exception as e:
                print(f"Ошибка при добавлении коллекции в сцену: {e}")

                # Функция find_layer_collection импортирована из common_utils

        # Убеждаемся, что коллекция клонера видима
        layer_collection = context.view_layer.layer_collection
        layer_coll = find_layer_collection(layer_collection, cloner_collection.name)
        if layer_coll:
            # Всегда делаем коллекцию клонера видимой
            layer_coll.exclude = False

            # Гарантируем, что созданный клонер видим
            if cloner_obj:
                cloner_obj.hide_viewport = False
                cloner_obj.hide_render = False

                # Гарантируем, что объект имеет вершины
                if cloner_obj.type == 'MESH' and len(cloner_obj.data.vertices) == 0:
                    # Создаем простую геометрию, чтобы объект был видим
                    bm = bmesh.new()
                    bm.verts.new((0, 0, 0))
                    bm.to_mesh(cloner_obj.data)
                    bm.free()

        # Проверяем и обеспечиваем видимость всех коллекций клонеров в цепочке
        if is_cloner_collection and previous_cloner_object:
            for mod in previous_cloner_object.modifiers:
                if mod.type == 'NODES' and mod.get("cloner_collection"):
                    prev_collection_name = mod.get("cloner_collection")
                    prev_layer_coll = find_layer_collection(layer_collection, prev_collection_name)
                    if prev_layer_coll:
                        prev_layer_coll.exclude = False

        # Создаем уникальное имя для модификатора
        modifier_name = base_mod_name
        counter = 1
        while modifier_name in cloner_obj.modifiers:
            modifier_name = f"{base_mod_name}.{counter:03d}"
            counter += 1

        # Create the geometry nodes modifier
        modifier = cloner_obj.modifiers.new(name=modifier_name, type='NODES')

        # Create node group for cloning the entire collection
        node_group = create_collection_cloner_nodetree(
            target_collection,
            cloner_type,
            target_collection.name,
            use_anti_recursion=context.scene.use_anti_recursion
        )

        # Set the node group for the modifier
        modifier.node_group = node_group

        # Initialize effectors list
        node_group["linked_effectors"] = []

        # Save information about source collection
        modifier["source_type"] = "COLLECTION"
        modifier["original_collection"] = target_collection.name
        modifier["cloner_collection"] = cloner_collection.name

        # Устанавливаем объект в сокет Object модификатора если он есть
        for item in node_group.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == 'Object':
                socket_id = item.identifier
                try:
                    modifier[socket_id] = cloner_obj
                    # Дополнительно ищем и устанавливаем объект в узел ObjectInfo
                    for node in node_group.nodes:
                        if node.bl_idname == 'GeometryNodeObjectInfo':
                            try:
                                node.inputs['Object'].default_value = cloner_obj
                            except Exception as e:
                                print(f"Warning: Could not set object in ObjectInfo node: {e}")
                except Exception as e:
                    print(f"Warning: Could not set Object parameter: {e}")
                break

        # Устанавливаем параметры клонера
        if cloner_type == "GRID":
            setup_grid_cloner_params(modifier)
        elif cloner_type == "LINEAR":
            setup_linear_cloner_params(modifier)
        elif cloner_type == "CIRCLE":
            setup_circle_cloner_params(modifier)

        # Устанавливаем флаги для цепочки клонеров
        if is_cloner_collection:
            modifier["is_collection_chain"] = True
            modifier["is_chained_cloner"] = True
            modifier["chain_source_collection"] = target_collection.name

            if previous_cloner_object:
                modifier["previous_cloner_object"] = previous_cloner_object.name
                cloner_collection["parent_cloner_collection"] = target_collection.name

                                # Регистрируем обновление цепочки                if hasattr(bpy.app, "timers"):                    # Используем функцию register_chain_update из common_utils                    # но эта функция сделана под другой контекст, поэтому лучше оставить оригинал                    def register_chain_update_local():                        try:                            # Для коллекций цепочку нужно строить вручную                            chain = []                            current_obj = previous_cloner_object                            while current_obj:                                chain.append(current_obj)                                # Ищем предыдущий объект в цепочке                                prev_name = None                                for mod in current_obj.modifiers:                                    if mod.type == 'NODES' and mod.get("previous_cloner_object"):                                        prev_name = mod.get("previous_cloner_object")                                        break                                                                if prev_name and prev_name in bpy.data.objects:                                    current_obj = bpy.data.objects[prev_name]                                else:                                    current_obj = None                                                        # Обновляем всю цепочку                            for chain_obj in chain:                                if chain_obj.name != cloner_obj.name:                                    # Добавляем сведения об этом клонере ко всем предыдущим                                    for mod in chain_obj.modifiers:                                        if mod.type == 'NODES' and mod.get("is_chained_cloner"):                                            if "next_cloners" not in mod:                                                mod["next_cloners"] = []                                            if cloner_obj.name not in mod["next_cloners"]:                                                mod["next_cloners"].append(cloner_obj.name)                        except Exception as e:                            print(f"Ошибка при регистрации цепочки обновлений: {e}")                        return None  # Запуск только один раз

                    # Регистрируем отложенное обновление цепочки
                    # Используем функцию register_chain_update из common_utils                    bpy.app.timers.register(lambda: register_chain_update(previous_cloner_object, cloner_obj), first_interval=0.2)
        else:
            # Сохраняем ссылку на источник
            modifier["chain_source_collection"] = target_collection.name

        # Инициализируем список следующих клонеров
        modifier["next_cloners"] = []

        # Сохраняем коллекцию для автоматического обновления UI
        if hasattr(context.scene, "last_cloned_collection"):
            context.scene.last_cloned_collection = cloner_collection_name

        # Скрываем исходную коллекцию в layer view
        target_layer_coll = find_layer_collection(layer_collection, target_collection.name)
        if target_layer_coll:
            # Сохраняем текущее состояние видимости
            was_excluded = target_layer_coll.exclude
            modifier["was_collection_excluded"] = was_excluded

            # Скрываем исходную коллекцию только если это не коллекция клонера
            if not target_collection.name.startswith("cloner_"):
                target_layer_coll.exclude = True

        # Делаем объект клонера активным
        for obj in context.selected_objects:
            obj.select_set(False)
        cloner_obj.select_set(True)
        context.view_layer.objects.active = cloner_obj

        # Обновляем UI
        context.view_layer.update()

        return True

    except Exception as e:
        print(f"Error creating collection cloner: {e}")
        return False