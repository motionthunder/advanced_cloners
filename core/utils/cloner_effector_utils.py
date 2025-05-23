"""
Утилиты для работы с эффекторами в клонерах.
"""

import bpy
from ...models.effectors import EFFECTOR_NODE_GROUP_PREFIXES


def safe_link_new(links, from_socket, to_socket):
    """
    Безопасное создание связи с проверкой на самоподключение.

    Args:
        links: Коллекция связей node_group.links
        from_socket: Исходящий сокет
        to_socket: Входящий сокет

    Returns:
        bool: True если связь создана, False если заблокирована
    """
    # Проверяем, что сокеты принадлежат разным узлам
    if hasattr(from_socket, 'node') and hasattr(to_socket, 'node'):
        if from_socket.node == to_socket.node:
            print(f"[SAFE_LINK] Заблокировано самоподключение узла: {from_socket.node.name}")
            return False

        # Дополнительная проверка по имени (на случай если узлы разные объекты, но одинаковые)
        if hasattr(from_socket.node, 'name') and hasattr(to_socket.node, 'name'):
            if from_socket.node.name == to_socket.node.name:
                print(f"[SAFE_LINK] Заблокировано самоподключение по имени: {from_socket.node.name}")
                return False

    try:
        links.new(from_socket, to_socket)
        if hasattr(from_socket, 'node') and hasattr(to_socket, 'node'):
            print(f"[SAFE_LINK] Создана связь: {from_socket.node.name}.{from_socket.name} -> {to_socket.node.name}.{to_socket.name}")
        return True
    except Exception as e:
        print(f"[SAFE_LINK] Ошибка создания связи: {e}")
        return False

def get_effector_modifiers(obj):
    """
    Получает список всех модификаторов-эффекторов на объекте.

    Args:
        obj: Объект Blender, для которого нужно найти эффекторы

    Returns:
        list: Список имен модификаторов-эффекторов
    """
    if not obj or not hasattr(obj, 'modifiers'):
        return []

    effector_mods = []

    for mod in obj.modifiers:
        # Проверка на Geometry Nodes модификатор с группой
        if mod.type == 'NODES' and mod.node_group:
            # Проверка на эффектор по префиксу имени группы
            if any(mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES):
                effector_mods.append(mod.name)
            # Дополнительная проверка для пользовательских эффекторов
            elif "Effector" in mod.node_group.name:
                effector_mods.append(mod.name)
            # Проверка на наличие флага эффектора в метаданных
            elif mod.get("is_effector", False):
                effector_mods.append(mod.name)

    return effector_mods


def update_cloner_with_effectors(obj, cloner_mod):
    """
    Улучшенная функция обновления клонера с эффекторами.
    Работает корректно с новой системой анти-рекурсии.

    Args:
        obj: Объект, содержащий модификатор
        cloner_mod: Модификатор клонера с нод-группой
    """
    if not cloner_mod or not cloner_mod.node_group:
        print("[DEBUG] update_cloner_with_effectors: Модификатор не имеет нод-группы")
        return

    # Проверяем, является ли клонер стековым
    mod_is_stacked = cloner_mod.get("is_stacked_cloner", False)
    node_is_stacked = cloner_mod.node_group.get("is_stacked_cloner", False)
    is_stacked_cloner = mod_is_stacked or node_is_stacked

    # Для стековых клонеров используем существующую логику
    if is_stacked_cloner:
        print(f"[DEBUG] Обработка стекового клонера {cloner_mod.name}")
        return update_stacked_cloner_with_effectors(obj, cloner_mod)

    # Для обычных клонеров используем улучшенную логику
    return update_standard_cloner_with_effectors(obj, cloner_mod)


def update_standard_cloner_with_effectors(obj, cloner_mod):
    """
    Обновляет обычный (не стековый) клонер с эффекторами.
    Заменяет проблемные узлы анти-рекурсии на эффекторы.

    Args:
        obj: Объект с модификатором
        cloner_mod: Модификатор клонера
    """
    node_group = cloner_mod.node_group
    linked_effectors = node_group.get("linked_effectors", [])
    print(f"[DEBUG] Связанные эффекторы: {linked_effectors}")

    # Проверяем валидность списка эффекторов
    valid_linked_effectors = []
    for eff_name in linked_effectors:
        eff_mod = obj.modifiers.get(eff_name)
        if eff_mod and eff_mod.type == 'NODES' and eff_mod.node_group:
            # Проверяем, что это действительно эффектор
            is_effector = any(eff_mod.node_group.name.startswith(p) for p in EFFECTOR_NODE_GROUP_PREFIXES)
            if is_effector:
                valid_linked_effectors.append(eff_name)
                print(f"[DEBUG] Валидный эффектор: {eff_name}")

    # Обновляем список эффекторов
    if len(valid_linked_effectors) != len(linked_effectors):
        print(f"[DEBUG] Обновляем список эффекторов с {len(linked_effectors)} на {len(valid_linked_effectors)}")
        node_group["linked_effectors"] = valid_linked_effectors
        linked_effectors = valid_linked_effectors

    # Находим ключевые узлы
    nodes = node_group.nodes
    links = node_group.links

    group_output = None
    anti_recursion_switch = None
    final_realize_switch = None

    for node in nodes:
        if node.type == 'GROUP_OUTPUT':
            group_output = node
        elif node.name == "Anti-Recursion Switch":
            anti_recursion_switch = node
        elif node.name == "Final Realize Switch":
            final_realize_switch = node

    if not group_output:
        print("[DEBUG] Не найден выходной узел")
        return

    # Используем Final Realize Switch если он есть, иначе Anti-Recursion Switch
    target_switch = final_realize_switch if final_realize_switch else anti_recursion_switch

    # Если нет эффекторов, восстанавливаем прямые связи и Realize узел для анти-рекурсии
    if not linked_effectors:
        print("[DEBUG] Нет эффекторов, восстанавливаем прямые связи и Realize узел")
        # Удаляем старые узлы эффекторов
        old_effector_nodes = [n for n in nodes if n.name.startswith('Effector_')]
        for node in old_effector_nodes:
            nodes.remove(node)
            print(f"[DEBUG] Удален старый узел эффектора: {node.name}")

        # Восстанавливаем Realize узел для анти-рекурсии, если его нет
        restore_realize_node_for_anti_recursion(node_group, target_switch)

        restore_direct_connection_improved(node_group)
        # Включаем видимость всех отвязанных эффекторов
        for eff_name in [n.name.replace('Effector_', '') for n in old_effector_nodes]:
            eff_mod = obj.modifiers.get(eff_name)
            if eff_mod:
                eff_mod.show_render = True
        return

    # НОВАЯ ЛОГИКА: Заменяем проблемные узлы на эффекторы
    replace_problematic_nodes_with_effectors(obj, node_group, linked_effectors)

    print("[DEBUG] Цепочка эффекторов создана успешно")


def replace_problematic_nodes_with_effectors(obj, node_group, linked_effectors):
    """
    Заменяет проблемные узлы анти-рекурсии на эффекторы с сохранением связей.

    Args:
        obj: Объект с модификатором
        node_group: Группа узлов клонера
        linked_effectors: Список связанных эффекторов
    """
    nodes = node_group.nodes
    links = node_group.links

    # Находим проблемные узлы
    problematic_nodes = []
    realize_nodes_to_remove = []

    for node in nodes:
        if node.name in ["Anti-Recursion Join Geometry", "Effector_Input"]:
            problematic_nodes.append(node)
            print(f"[DEBUG] Найден проблемный узел для замены: {node.name}")
        elif node.name == "Anti-Recursion Realize":
            # При привязке эффекторов удаляем Realize узел
            realize_nodes_to_remove.append(node)
            print(f"[DEBUG] Найден Realize узел для удаления при привязке эффекторов: {node.name}")

    # Если есть Realize узлы для удаления, добавляем их к проблемным узлам
    if realize_nodes_to_remove:
        print(f"[DEBUG] Добавляем {len(realize_nodes_to_remove)} Realize узлов к проблемным узлам")
        problematic_nodes.extend(realize_nodes_to_remove)

    # Если нет проблемных узлов (включая Realize узлы), используем стандартную логику
    if not problematic_nodes:
        print("[DEBUG] Проблемные узлы не найдены, используем стандартную логику")
        create_standard_effector_chain(obj, node_group, linked_effectors)
        return

    # Заменяем первый проблемный узел на цепочку эффекторов
    target_node = problematic_nodes[0]

    # ВАЖНО: Сохраняем позицию узла ДО его удаления
    pos_x = target_node.location.x
    pos_y = target_node.location.y

    # Сохраняем входящие и исходящие связи проблемного узла
    incoming_links = []
    outgoing_links = []

    for link in links:
        if link.to_node == target_node:
            incoming_links.append((link.from_node, link.from_socket, link.to_socket))
        elif link.from_node == target_node:
            outgoing_links.append((link.from_socket, link.to_node, link.to_socket))

    print(f"[DEBUG] Сохранено {len(incoming_links)} входящих и {len(outgoing_links)} исходящих связей")

    # Удаляем все проблемные узлы
    for node in problematic_nodes:
        try:
            nodes.remove(node)
            print(f"[DEBUG] Удален проблемный узел: {node.name}")
        except:
            print(f"[DEBUG] Узел уже был удален")

    # Создаем цепочку эффекторов на месте проблемного узла
    current_output = None
    first_effector_input = None

    for i, effector_name in enumerate(linked_effectors):
        effector_mod = obj.modifiers.get(effector_name)
        if not effector_mod or not effector_mod.node_group:
            print(f"[DEBUG] Пропускаем неверный эффектор: {effector_name}")
            continue

        # Создаем узел эффектора
        effector_node = nodes.new('GeometryNodeGroup')
        effector_node.name = f"Effector_{effector_name}"
        effector_node.node_tree = effector_mod.node_group
        effector_node.location = (pos_x + i * 250, pos_y)

        # Запоминаем первый эффектор для входящих связей
        if first_effector_input is None:
            first_effector_input = effector_node.inputs['Geometry']

        # Подключаем к цепочке
        if current_output is not None:
            links.new(current_output, effector_node.inputs['Geometry'])

        current_output = effector_node.outputs['Geometry']

        # Копируем параметры эффектора
        copy_effector_parameters(effector_mod, effector_node)

        # Отключаем рендер оригинального эффектора
        effector_mod.show_render = False
        effector_mod.show_viewport = True

        print(f"[DEBUG] Создан узел эффектора: {effector_name}")

    # Восстанавливаем входящие связи к первому эффектору
    input_connected = False
    first_effector_node = None

    # Находим первый созданный эффектор
    for i, effector_name in enumerate(linked_effectors):
        effector_mod = obj.modifiers.get(effector_name)
        if effector_mod and effector_mod.node_group:
            for node in nodes:
                if node.name == f"Effector_{effector_name}":
                    first_effector_node = node
                    break
            if first_effector_node:
                break

    for from_node, from_socket, to_socket in incoming_links:
        if first_effector_input and first_effector_node:
            try:
                # ВАЖНО: Проверяем, что не подключаем узел сам к себе
                if from_node == first_effector_node:
                    print(f"[DEBUG] Пропущена связь (самоподключение): {from_node.name} -> сам себе")
                    continue

                # Дополнительная проверка по имени узла (для Noise эффектора)
                if hasattr(from_node, 'name') and hasattr(first_effector_node, 'name'):
                    if from_node.name == first_effector_node.name:
                        print(f"[DEBUG] Пропущена связь (самоподключение по имени): {from_node.name} -> {first_effector_node.name}")
                        continue

                # Подключаем к входу Geometry первого эффектора
                if to_socket.name == 'Geometry' or 'Geometry' in to_socket.name:
                    print(f"[DEBUG] Попытка подключения: {from_node.name}.{from_socket.name} -> {first_effector_node.name}.{first_effector_input.name}")
                    if safe_link_new(links, from_socket, first_effector_input):
                        print(f"[DEBUG] Восстановлена входящая связь: {from_node.name}.{from_socket.name} -> первый эффектор")
                        input_connected = True
                else:
                    print(f"[DEBUG] Пропущена входящая связь (не Geometry): {to_socket.name}")
            except Exception as e:
                print(f"[DEBUG] Не удалось восстановить входящую связь: {e}")

    # Если входящие связи не были восстановлены, ищем Transform Geometry узел
    if not input_connected and first_effector_input:
        print("[DEBUG] Входящие связи не восстановлены, ищем Transform Geometry узел")
        for node in nodes:
            if ('Transform' in node.name or 'Transform' in getattr(node, 'bl_idname', '')) and hasattr(node, 'outputs'):
                for output in node.outputs:
                    if output.name == 'Geometry':
                        try:
                            if safe_link_new(links, output, first_effector_input):
                                print(f"[DEBUG] Подключен {node.name}.{output.name} к первому эффектору")
                                input_connected = True
                                break
                        except Exception as e:
                            print(f"[DEBUG] Не удалось подключить {node.name}: {e}")
                if input_connected:
                    break

    # Восстанавливаем исходящие связи от последнего эффектора
    last_effector_node = None

    # Находим последний созданный эффектор
    for i in range(len(linked_effectors) - 1, -1, -1):
        effector_name = linked_effectors[i]
        effector_mod = obj.modifiers.get(effector_name)
        if effector_mod and effector_mod.node_group:
            for node in nodes:
                if node.name == f"Effector_{effector_name}":
                    last_effector_node = node
                    break
            if last_effector_node:
                break

    for from_socket, to_node, to_socket in outgoing_links:
        if current_output and last_effector_node:
            try:
                # ВАЖНО: Проверяем, что не подключаем узел сам к себе
                if to_node == last_effector_node:
                    print(f"[DEBUG] Пропущена связь (самоподключение): последний эффектор -> сам себе")
                    continue

                # Дополнительная проверка по имени узла (для Noise эффектора)
                if hasattr(to_node, 'name') and hasattr(last_effector_node, 'name'):
                    if to_node.name == last_effector_node.name:
                        print(f"[DEBUG] Пропущена связь (самоподключение по имени): {last_effector_node.name} -> {to_node.name}")
                        continue

                # Подключаем выход последнего эффектора
                if from_socket.name == 'Geometry' or 'Geometry' in from_socket.name:
                    print(f"[DEBUG] Попытка подключения: {last_effector_node.name}.{current_output.name} -> {to_node.name}.{to_socket.name}")
                    if safe_link_new(links, current_output, to_socket):
                        print(f"[DEBUG] Восстановлена исходящая связь: последний эффектор -> {to_node.name}.{to_socket.name}")
                else:
                    print(f"[DEBUG] Пропущена исходящая связь (не Geometry): {from_socket.name}")
            except Exception as e:
                print(f"[DEBUG] Не удалось восстановить исходящую связь: {e}")

    # Дополнительная проверка: убеждаемся, что эффектор подключен к Switch узлу
    if current_output:
        # Ищем Switch узел в клонере
        switch_node = None
        for node in nodes:
            if node.name == "Anti-Recursion Switch" or (hasattr(node, 'bl_idname') and 'Switch' in node.bl_idname):
                switch_node = node
                break

        if switch_node:
            # Проверяем, подключен ли эффектор к Switch
            connected_to_switch = False
            for link in links:
                if link.from_node.name.startswith('Effector_') and link.to_node == switch_node:
                    connected_to_switch = True
                    break

            if not connected_to_switch:
                # Пытаемся подключить к False входу Switch (обычно это индекс 1)
                try:
                    if len(switch_node.inputs) > 1:
                        links.new(current_output, switch_node.inputs[1])  # False вход
                        print(f"[DEBUG] Дополнительно подключен эффектор к Switch узлу (False вход)")
                    elif len(switch_node.inputs) > 0:
                        links.new(current_output, switch_node.inputs[0])  # Первый доступный вход
                        print(f"[DEBUG] Дополнительно подключен эффектор к Switch узлу (первый вход)")
                except Exception as e:
                    print(f"[DEBUG] Не удалось дополнительно подключить к Switch: {e}")


def restore_realize_node_for_anti_recursion(node_group, switch_node=None):
    """
    Восстанавливает Realize узел для анти-рекурсии, если его нет и есть Switch узел.
    ОБНОВЛЕНО: Поддерживает новую структуру с Final Realize Switch.

    Args:
        node_group: Группа узлов клонера
        switch_node: Узел Switch (может быть None, тогда ищем автоматически)
    """
    nodes = node_group.nodes
    links = node_group.links

    # Если Switch узел не передан, ищем его
    if not switch_node:
        for node in nodes:
            if node.name in ["Anti-Recursion Switch", "Final Realize Switch"]:
                switch_node = node
                break

    if not switch_node:
        print("[DEBUG] Switch узел не найден, Realize узел не нужен")
        return

    # Определяем тип Switch узла и соответствующий Realize узел
    is_final_realize_switch = switch_node.name == "Final Realize Switch"
    realize_node_name = "Final Realize Instances" if is_final_realize_switch else "Anti-Recursion Realize"

    # Проверяем, есть ли уже Realize узел
    realize_node = None
    for node in nodes:
        if node.name == realize_node_name:
            realize_node = node
            break

    if realize_node:
        print(f"[DEBUG] {realize_node_name} узел уже существует")
        return

    # Создаем новый Realize узел
    realize_node = nodes.new('GeometryNodeRealizeInstances')
    realize_node.name = realize_node_name
    realize_node.location = (switch_node.location.x - 150, switch_node.location.y + 100)

    # Находим что подключено к False входу Switch (обычно это прямой путь)
    false_input_source = None
    false_input_socket = None

    for link in links:
        if link.to_node == switch_node and link.to_socket.name == 'False':
            false_input_source = link.from_node
            false_input_socket = link.from_socket
            break

    if false_input_source and false_input_socket:
        # Подключаем источник к Realize узлу
        safe_link_new(links, false_input_socket, realize_node.inputs['Geometry'])
        # Подключаем Realize узел к True входу Switch
        safe_link_new(links, realize_node.outputs['Geometry'], switch_node.inputs['True'])
        print(f"[DEBUG] Восстановлен {realize_node_name} узел для анти-рекурсии")
    else:
        print("[DEBUG] Не найден источник для подключения Realize узла")


def restore_connections_bypassing_realize(node_group, realize_connections):
    """
    Восстанавливает связи, минуя удаленные Realize узлы.

    Args:
        node_group: Группа узлов
        realize_connections: Список связей удаленных Realize узлов
    """
    links = node_group.links

    # Группируем связи по входам и выходам
    inputs_to_realize = []  # Что было подключено К Realize узлу
    outputs_from_realize = []  # Что было подключено ОТ Realize узла

    for connection in realize_connections:
        if len(connection) == 3:
            if hasattr(connection[2], 'node'):  # to_socket
                # Это входящая связь К Realize узлу
                from_node, from_socket, to_socket = connection
                inputs_to_realize.append((from_node, from_socket))
            else:
                # Это исходящая связь ОТ Realize узла
                from_socket, to_node, to_socket = connection
                outputs_from_realize.append((to_node, to_socket))

    # Соединяем входы напрямую с выходами, минуя Realize
    for from_node, from_socket in inputs_to_realize:
        for to_node, to_socket in outputs_from_realize:
            if safe_link_new(links, from_socket, to_socket):
                print(f"[DEBUG] Восстановлена связь, минуя Realize: {from_node.name} -> {to_node.name}")
            else:
                print(f"[DEBUG] Не удалось восстановить связь, минуя Realize")


def create_standard_effector_chain(obj, node_group, linked_effectors):
    """
    Создает стандартную цепочку эффекторов (старая логика).

    Args:
        obj: Объект с модификатором
        node_group: Группа узлов клонера
        linked_effectors: Список связанных эффекторов
    """
    nodes = node_group.nodes
    links = node_group.links

    # Удаляем старые узлы эффекторов
    old_effector_nodes = [n for n in nodes if n.name.startswith('Effector_')]
    for node in old_effector_nodes:
        nodes.remove(node)
        print(f"[DEBUG] Удален старый узел эффектора: {node.name}")

    # Находим анти-рекурсию (старую или новую структуру)
    anti_recursion_switch = None
    final_realize_switch = None
    for node in nodes:
        if node.name == "Anti-Recursion Switch":
            anti_recursion_switch = node
        elif node.name == "Final Realize Switch":
            final_realize_switch = node

    # Используем Final Realize Switch если он есть, иначе Anti-Recursion Switch
    target_switch = final_realize_switch if final_realize_switch else anti_recursion_switch

    # Находим точку подключения эффекторов
    effector_insertion_point = find_effector_insertion_point(node_group, target_switch)

    if not effector_insertion_point:
        print("[DEBUG] Не найдена точка подключения эффекторов")
        return

    source_node, source_output, target_node, target_input = effector_insertion_point

    # Создаем цепочку эффекторов
    current_output = source_output
    pos_x = source_node.location.x + 200
    pos_y = source_node.location.y

    print(f"[DEBUG] Создаем стандартную цепочку из {len(linked_effectors)} эффекторов")

    for i, effector_name in enumerate(linked_effectors):
        effector_mod = obj.modifiers.get(effector_name)
        if not effector_mod or not effector_mod.node_group:
            print(f"[DEBUG] Пропускаем неверный эффектор: {effector_name}")
            continue

        # Создаем узел эффектора
        effector_node = nodes.new('GeometryNodeGroup')
        effector_node.name = f"Effector_{effector_name}"
        effector_node.node_tree = effector_mod.node_group
        effector_node.location = (pos_x + i * 250, pos_y)

        # Подключаем к цепочке
        if safe_link_new(links, current_output, effector_node.inputs['Geometry']):
            current_output = effector_node.outputs['Geometry']

        # Копируем параметры эффектора
        copy_effector_parameters(effector_mod, effector_node)

        # Отключаем рендер оригинального эффектора
        effector_mod.show_render = False
        effector_mod.show_viewport = True

        print(f"[DEBUG] Создан узел эффектора: {effector_name}")

    # Подключаем последний эффектор к целевому узлу
    if target_node and target_input:
        # Удаляем старую связь с целевым узлом
        links_to_remove = [link for link in links
                          if link.to_node == target_node and link.to_socket == target_input]
        for link in links_to_remove:
            links.remove(link)

        # Подключаем цепочку эффекторов
        safe_link_new(links, current_output, target_input)
        print(f"[DEBUG] Подключена цепочка эффекторов к {target_node.name}")

        # Если у нас есть анти-рекурсия, убеждаемся что True путь тоже настроен правильно
        if target_switch and target_node == target_switch:
            setup_anti_recursion_true_path(node_group, target_switch, current_output)


def find_effector_insertion_point(node_group, anti_recursion_switch):
    """
    Находит оптимальную точку для вставки эффекторов.
    ИСПРАВЛЕНО: Учитывает правильную структуру анти-рекурсии и новую структуру грид клонера.

    Args:
        node_group: Группа узлов
        anti_recursion_switch: Узел Switch для анти-рекурсии (может быть None)

    Returns:
        tuple: (source_node, source_output, target_node, target_input) или None
    """
    nodes = node_group.nodes
    links = node_group.links

    # Находим выходной узел
    group_output = None
    for node in nodes:
        if node.type == 'GROUP_OUTPUT':
            group_output = node
            break

    if not group_output:
        return None

    # Ищем узлы Switch для новой структуры анти-рекурсии (как в линейном и круговом клонерах)
    final_realize_switch = None
    switch_realize_mode = None

    for node in nodes:
        if node.name == "Final Realize Switch":
            final_realize_switch = node
        elif node.name == "Switch Realize Mode":
            switch_realize_mode = node

    # Если есть новая структура анти-рекурсии (Final Realize Switch)
    if final_realize_switch:
        print("[DEBUG] Поиск точки вставки для новой структуры анти-рекурсии (Final Realize Switch)")

        # Ищем узел, подключенный к False входу Final Realize Switch (прямой путь)
        source_node = None
        source_output = None

        for link in links:
            if (link.to_node == final_realize_switch and
                link.to_socket == final_realize_switch.inputs[False]):
                source_node = link.from_node
                source_output = link.from_socket
                break

        if source_node and source_output:
            return (source_node, source_output,
                   final_realize_switch, final_realize_switch.inputs[False])
        else:
            print("[DEBUG] Не найден источник для False входа Final Realize Switch")

    # Если есть старая структура анти-рекурсии (Anti-Recursion Switch)
    elif anti_recursion_switch:
        print("[DEBUG] Поиск точки вставки для старой структуры анти-рекурсии")

        # Ищем узел, подключенный к False входу Switch (прямой путь)
        source_node = None
        source_output = None

        for link in links:
            if (link.to_node == anti_recursion_switch and
                link.to_socket == anti_recursion_switch.inputs[False]):
                source_node = link.from_node
                source_output = link.from_socket
                break

        if source_node and source_output:
            return (source_node, source_output,
                   anti_recursion_switch, anti_recursion_switch.inputs[False])
        else:
            print("[DEBUG] Не найден источник для False входа анти-рекурсии")

    # Если нет узла анти-рекурсии, подключаем эффекторы перед выходом
    print("[DEBUG] Поиск точки вставки для системы без анти-рекурсии")

    # Ищем узел, подключенный к выходу
    source_node = None
    source_output = None

    for link in links:
        if link.to_node == group_output and link.to_socket.name == 'Geometry':
            source_node = link.from_node
            source_output = link.from_socket
            break

    if source_node and source_output:
        return (source_node, source_output,
               group_output, group_output.inputs['Geometry'])
    else:
        print("[DEBUG] Не найден источник для выходного узла")

        # Пытаемся найти любой подходящий узел
        for node in nodes:
            if (node != group_output and node.type != 'GROUP_INPUT' and
                not node.name.startswith('Effector_')):
                for output in node.outputs:
                    if output.name in ['Geometry', 'Instances']:
                        return (node, output, group_output, group_output.inputs['Geometry'])
        return None


def setup_anti_recursion_true_path(node_group, anti_recursion_switch, effector_chain_output):
    """
    Настраивает True путь для узла анти-рекурсии после подключения эффекторов.
    ИСПРАВЛЕНО: Учитывает существующие Realize узлы и новую структуру.

    Args:
        node_group: Группа узлов
        anti_recursion_switch: Узел Switch для анти-рекурсии
        effector_chain_output: Выходной сокет цепочки эффекторов
    """
    nodes = node_group.nodes
    links = node_group.links

    # Проверяем, какой тип Switch узла у нас есть
    is_final_realize_switch = anti_recursion_switch.name == "Final Realize Switch"

    if is_final_realize_switch:
        # Для новой структуры (Final Realize Switch) ищем Final Realize Instances
        existing_realize = None
        for node in nodes:
            if node.name == "Final Realize Instances":
                existing_realize = node
                break

        if existing_realize:
            # Обновляем вход Final Realize Instances
            links_to_remove = []
            for link in links:
                if link.to_node == existing_realize and link.to_socket.name == 'Geometry':
                    links_to_remove.append(link)

            for link in links_to_remove:
                links.remove(link)

            # Подключаем цепочку эффекторов к существующему Final Realize узлу
            links.new(effector_chain_output, existing_realize.inputs['Geometry'])
            print("[DEBUG] Обновлен существующий Final Realize узел для True пути")
        else:
            print("[DEBUG] Final Realize Instances узел не найден")
    else:
        # Для старой структуры (Anti-Recursion Switch) ищем Anti-Recursion Realize
        existing_realize = None
        for node in nodes:
            if node.name == "Anti-Recursion Realize":
                existing_realize = node
                break

        if existing_realize:
            # Используем существующий Realize узел
            # Обновляем его вход
            links_to_remove = []
            for link in links:
                if link.to_node == existing_realize and link.to_socket.name == 'Geometry':
                    links_to_remove.append(link)

            for link in links_to_remove:
                links.remove(link)

            # Подключаем цепочку эффекторов к существующему Realize узлу
            links.new(effector_chain_output, existing_realize.inputs['Geometry'])
            print("[DEBUG] Обновлен существующий Anti-Recursion Realize узел для True пути")
        else:
            # Проверяем, подключен ли уже True вход
            true_input_connected = False
            for link in links:
                if (link.to_node == anti_recursion_switch and
                    link.to_socket == anti_recursion_switch.inputs[True]):
                    true_input_connected = True
                    break

            if not true_input_connected:
                # Создаем новый Realize узел для True пути
                realize_true = nodes.new('GeometryNodeRealizeInstances')
                realize_true.name = "Effector Chain Realize"
                realize_true.location = (anti_recursion_switch.location.x - 150,
                                       anti_recursion_switch.location.y + 150)

                # Подключаем цепочку эффекторов к Realize узлу и далее к True входу
                links.new(effector_chain_output, realize_true.inputs['Geometry'])
                links.new(realize_true.outputs['Geometry'], anti_recursion_switch.inputs[True])

                print("[DEBUG] Создан новый Realize узел для True пути анти-рекурсии")


def copy_effector_parameters(effector_mod, effector_node):
    """
    Копирует параметры из модификатора эффектора в узел эффектора.

    Args:
        effector_mod: Модификатор эффектора
        effector_node: Узел эффектора в группе
    """
    try:
        effector_group = effector_mod.node_group
        for socket in effector_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
                if socket.name == 'Geometry':
                    continue

                if socket.identifier in effector_mod:
                    try:
                        effector_node.inputs[socket.name].default_value = effector_mod[socket.identifier]
                        print(f"[DEBUG] Скопирован параметр {socket.name} = {effector_mod[socket.identifier]}")
                    except (KeyError, TypeError, AttributeError) as e:
                        print(f"[DEBUG] Не удалось скопировать параметр {socket.name}: {e}")
    except Exception as e:
        print(f"[DEBUG] Ошибка при копировании параметров эффектора: {e}")


def restore_direct_connection_improved(node_group):
    """
    Улучшенная функция восстановления прямых связей.
    Корректно работает с новой системой анти-рекурсии.

    Args:
        node_group: Группа узлов для восстановления связей
    """
    nodes = node_group.nodes
    links = node_group.links

    # Находим выходной узел
    group_output = None
    for node in nodes:
        if node.type == 'GROUP_OUTPUT':
            group_output = node
            break

    if not group_output:
        print("[DEBUG] Не найден выходной узел для восстановления связей")
        return

    # Находим узел анти-рекурсии
    anti_recursion_switch = None
    for node in nodes:
        if node.name == "Anti-Recursion Switch":
            anti_recursion_switch = node
            break

    if anti_recursion_switch:
        print("[DEBUG] Восстановление связей для системы с анти-рекурсией")
        restore_anti_recursion_connections(node_group, anti_recursion_switch)
    else:
        print("[DEBUG] Восстановление связей для системы без анти-рекурсии")
        restore_direct_output_connection(node_group, group_output)


def restore_anti_recursion_connections(node_group, anti_recursion_switch):
    """
    Восстанавливает связи для системы с анти-рекурсией.

    Args:
        node_group: Группа узлов
        anti_recursion_switch: Узел Switch для анти-рекурсии
    """
    nodes = node_group.nodes
    links = node_group.links

    # Находим подходящий исходный узел
    source_candidates = []

    # Ищем узлы трансформации, инстансирования и другие подходящие
    for node in nodes:
        if (node.type != 'GROUP_OUTPUT' and node.type != 'GROUP_INPUT' and
            node != anti_recursion_switch and not node.name.startswith('Effector_')):

            # Проверяем типы узлов, которые обычно являются источниками
            if ('Transform' in node.bl_idname or
                'Instance' in node.bl_idname or
                'Scale' in node.bl_idname or
                'Rotate' in node.bl_idname or
                'Translate' in node.bl_idname):

                for output in node.outputs:
                    if output.name in ['Geometry', 'Instances']:
                        source_candidates.append((node, output))

    # Выбираем лучший кандидат (обычно последний в цепочке)
    if source_candidates:
        source_node, source_output = source_candidates[-1]

        print(f"[DEBUG] Выбран исходный узел: {source_node.name} с выходом {source_output.name}")

        # Удаляем существующие связи к False входу
        links_to_remove = [link for link in links
                          if (link.to_node == anti_recursion_switch and
                              link.to_socket == anti_recursion_switch.inputs[False])]
        for link in links_to_remove:
            links.remove(link)

        # Подключаем исходный узел к False входу
        links.new(source_output, anti_recursion_switch.inputs[False])

        print("[DEBUG] Восстановлены связи для анти-рекурсии")
    else:
        print("[DEBUG] Не найдены подходящие исходные узлы")


def restore_direct_output_connection(node_group, group_output):
    """
    Восстанавливает прямую связь с выходным узлом.

    Args:
        node_group: Группа узлов
        group_output: Выходной узел группы
    """
    nodes = node_group.nodes
    links = node_group.links

    # Ищем подходящий исходный узел
    for node in nodes:
        if (node.type != 'GROUP_OUTPUT' and node.type != 'GROUP_INPUT' and
            not node.name.startswith('Effector_')):

            for output in node.outputs:
                if output.name in ['Geometry', 'Instances']:
                    # Создаем прямую связь к выходу
                    links.new(output, group_output.inputs['Geometry'])
                    print(f"[DEBUG] Восстановлена прямая связь: {node.name}.{output.name} -> Output")
                    return

    print("[DEBUG] Не удалось найти узел для восстановления прямой связи")


def update_stacked_cloner_with_effectors(obj, cloner_mod):
    """
    Обновляет стековый клонер с эффекторами (существующая логика).

    Args:
        obj: Объект с модификатором
        cloner_mod: Модификатор стекового клонера
    """
    # Здесь должна быть существующая логика для стековых клонеров
    # Пока используем заглушку, которая вызывает существующую функцию

    node_group = cloner_mod.node_group
    linked_effectors = node_group.get("linked_effectors", [])

    print(f"[DEBUG] Обработка стекового клонера с {len(linked_effectors)} эффекторами")

    # Применяем каждый эффектор к стековому клонеру
    for effector_name in linked_effectors:
        effector_mod = obj.modifiers.get(effector_name)
        if effector_mod:
            print(f"[DEBUG] Применение эффектора {effector_name} к стековому клонеру")
            apply_effector_to_stacked_cloner(obj, cloner_mod, effector_mod)


# Алиас для обратной совместимости
restore_direct_connection = restore_direct_connection_improved


# СТАРАЯ ЛОГИКА ДЛЯ СТЕКОВЫХ КЛОНЕРОВ (сохраняем как есть)

def apply_effector_to_stacked_cloner(_, cloner_mod, effector_mod):
    """Применяет параметры эффектора к стековому клонеру

    Args:
        _: Неиспользуемый параметр (объект)
        cloner_mod: Модификатор стекового клонера
        effector_mod: Модификатор эффектора

    Returns:
        bool: True если эффектор успешно применен, False в случае ошибки
    """

    # Сохраняем важные настройки клонера чтобы они не потерялись
    cloner_settings = {}
    if cloner_mod.node_group:
        # Сохраняем тип клонера, чтобы его можно было восстановить
        if cloner_mod.get("cloner_type"):
            cloner_settings["cloner_type"] = cloner_mod["cloner_type"]
        elif cloner_mod.node_group.get("cloner_type"):
            cloner_settings["cloner_type"] = cloner_mod.node_group["cloner_type"]
            # Синхронизируем тип клонера
            cloner_mod["cloner_type"] = cloner_mod.node_group["cloner_type"]

        # Сохраняем флаг стекового клонера
        cloner_settings["is_stacked_cloner"] = True
        cloner_mod["is_stacked_cloner"] = True
        cloner_mod.node_group["is_stacked_cloner"] = True

        # Сохраняем важные параметры стекового клонера по типу
        cloner_type = cloner_settings.get("cloner_type", "")

        # Проверяем исходные имена параметров в клонере
        socket_params = {}
        for socket in cloner_mod.node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
                socket_params[socket.name] = socket.identifier

    # Фиксируем тип клонера, если он не определен
    if cloner_mod.get("is_stacked_cloner", False) and not cloner_mod.get("cloner_type"):
        # Определяем тип по имени группы
        node_group_name = cloner_mod.node_group.name
        if "_Grid_" in node_group_name or "Grid_Stack_" in node_group_name:
            cloner_mod["cloner_type"] = "GRID"
        elif "_Linear_" in node_group_name or "Linear_Stack_" in node_group_name:
            cloner_mod["cloner_type"] = "LINEAR"
        elif "_Circle_" in node_group_name or "Circle_Stack_" in node_group_name:
            cloner_mod["cloner_type"] = "CIRCLE"

    # Если тип клонера определен в node_group, но не в модификаторе, синхронизируем
    if not cloner_mod.get("cloner_type") and cloner_mod.node_group.get("cloner_type"):
        cloner_mod["cloner_type"] = cloner_mod.node_group["cloner_type"]

    # Активируем сокет Use Effector для стекового клонера
    # Это нужно для правильной работы эффекторов
    use_effector_activated = False
    try:
        # Найдем сокет Use Effector в интерфейсе клонера
        use_effector_socket = None
        for socket in cloner_mod.node_group.interface.items_tree:
            if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Use Effector":
                use_effector_socket = socket.identifier
                break

        # Если нашли сокет, активируем его
        if use_effector_socket:
            cloner_mod[use_effector_socket] = True
            use_effector_activated = True
            print(f"[DEBUG] Активирован сокет Use Effector ({use_effector_socket}) для {cloner_mod.name}")
        else:
            # Попробуем найти сокет по имени напрямую
            try:
                cloner_mod["Use Effector"] = True
                use_effector_activated = True
                print(f"[DEBUG] Активирован сокет Use Effector (прямой доступ) для {cloner_mod.name}")
            except Exception as inner_e:
                print(f"[DEBUG] Не найден сокет Use Effector для {cloner_mod.name}: {inner_e}")
    except Exception as e:
        print(f"[DEBUG] Ошибка при активации сокета Use Effector: {e}")

    # Если не удалось активировать Use Effector, пробуем найти его по индексу
    if not use_effector_activated:
        try:
            # Типичные индексы для Use Effector в разных типах клонеров
            common_indices = ["Socket_12", "Socket_13", "Socket_14", "Socket_15"]
            for idx in common_indices:
                try:
                    if idx in cloner_mod:
                        current_val = cloner_mod[idx]
                        # Если это булево значение, вероятно это Use Effector
                        if isinstance(current_val, bool) or current_val in [0, 1]:
                            cloner_mod[idx] = True
                            use_effector_activated = True
                            print(f"[DEBUG] Активирован предполагаемый сокет Use Effector ({idx}) для {cloner_mod.name}")
                            break
                except:
                    continue
        except Exception as e:
            print(f"[DEBUG] Ошибка при попытке активации Use Effector по индексу: {e}")

    # Используем альтернативный подход, основанный на старой версии кода,
    # для более стабильной работы с эффекторами
    try:
        print(f"[DEBUG] apply_effector_to_stacked_cloner: Применение {effector_mod.name} к {cloner_mod.name} (старый метод)")

        # Проверяем наличие необходимых элементов
        if not cloner_mod.node_group or not effector_mod.node_group:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Нет node_group в клонере или эффекторе")
            return False

        # Получаем группы узлов
        cloner_group = cloner_mod.node_group
        effector_group = effector_mod.node_group

        # Проверяем наличие нужных входов/выходов в эффекторе
        input_sockets = [s.name for s in effector_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']
        output_sockets = [s.name for s in effector_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'OUTPUT']

        # Убеждаемся, что у эффектора есть входы/выходы
        if 'Geometry' not in input_sockets or 'Geometry' not in output_sockets:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Эффектор не имеет нужных сокетов Geometry")
            return False

        # Проверяем, существует ли уже узел этого эффектора в клонере
        existing_effector_node = None
        for node in cloner_group.nodes:
            if node.name == f"Effector_{effector_mod.name}":
                existing_effector_node = node
                break

        # Если узел уже существует, обновляем его параметры
        if existing_effector_node:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Обновляем существующий узел эффектора")
            # Обновляем параметры
            for input_socket in [s for s in effector_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']:
                if input_socket.name in ['Geometry']:
                    continue  # Пропускаем вход геометрии

                # Если параметр не имеет установленного значения в модификаторе, пропускаем
                if input_socket.identifier not in effector_mod:
                    continue

                # Копируем значение параметра из модификатора в узел
                try:
                    existing_effector_node.inputs[input_socket.name].default_value = effector_mod[input_socket.identifier]
                except (KeyError, TypeError) as e:
                    print(f"[DEBUG] apply_effector_to_stacked_cloner: Не удалось установить значение для {input_socket.name}: {e}")
                    pass

            return True

        # Создаем новый узел эффектора
        print(f"[DEBUG] apply_effector_to_stacked_cloner: Создаем новый узел эффектора")

        # Найдем выходной узел и его входящую связь
        group_output = None
        for node in cloner_group.nodes:
            if node.type == 'GROUP_OUTPUT':
                group_output = node
                break

        if not group_output:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Нет выходного узла в клонере")
            return False

        # Найдем последний узел трансформации или первый с геометрией перед выходом
        source_node = None
        source_socket = None

        # Проверяем наличие узлов анти-рекурсии и Effector_Input
        anti_recursion_switch = None
        effector_input_node = None

        # Сначала ищем узел Anti-Recursion Switch
        for node in cloner_group.nodes:
            if node.name == "Anti-Recursion Switch":
                anti_recursion_switch = node
                print(f"[DEBUG] apply_effector_to_stacked_cloner: Найден узел анти-рекурсии")
                break

        # Затем ищем узел Effector_Input
        for node in cloner_group.nodes:
            if node.name == "Effector_Input":
                effector_input_node = node
                print(f"[DEBUG] apply_effector_to_stacked_cloner: Найден узел Effector_Input")
                break

        # Если есть узел Effector_Input и узел анти-рекурсии
        if effector_input_node and anti_recursion_switch:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Используем узел Effector_Input")

            # Находим исходный узел, который должен быть подключен к входу False узла анти-рекурсии
            # Ищем узел Transform или TransformGeometry
            for node in cloner_group.nodes:
                if 'Transform' in node.bl_idname and node.type != 'GROUP_OUTPUT':
                    # Проверяем, что у него есть выход Geometry
                    if 'Geometry' in [s.name for s in node.outputs]:
                        source_node = node
                        source_socket = node.outputs['Geometry']
                        print(f"[DEBUG] apply_effector_to_stacked_cloner: Найден исходный узел Transform: {source_node.name}")
                        break

            # Если не нашли узел трансформации, ищем любой узел с выходом Geometry
            if not source_node:
                for node in cloner_group.nodes:
                    if node.type != 'GROUP_OUTPUT' and node != effector_input_node and node != anti_recursion_switch:
                        for output in node.outputs:
                            if output.name == 'Geometry':
                                source_node = node
                                source_socket = output
                                print(f"[DEBUG] apply_effector_to_stacked_cloner: Найден исходный узел с выходом Geometry: {source_node.name}")
                                break
                        if source_node:
                            break

        # Если есть только узел анти-рекурсии, ищем узел, который подключен к его входу False
        elif anti_recursion_switch:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Используем вход False узла анти-рекурсии")

            for link in cloner_group.links:
                if link.to_node == anti_recursion_switch and link.to_socket == anti_recursion_switch.inputs[False]:
                    source_node = link.from_node
                    source_socket = link.from_socket
                    print(f"[DEBUG] apply_effector_to_stacked_cloner: Найден исходный узел через анти-рекурсию: {source_node.name}")
                    break

        # Если не нашли через анти-рекурсию, ищем стандартным способом
        if not source_node:
            # Сначала ищем узлы трансформации с выходом Geometry
            for node in cloner_group.nodes:
                if node != group_output and not node.name.startswith('Effector_'):
                    for output in node.outputs:
                        if output.name == 'Geometry' and any(link.to_node == group_output for link in output.links):
                            source_node = node
                            source_socket = output
                            break
                    if source_node:
                        break

        # Если не нашли, ищем любой узел перед выходом с геометрией
        if not source_node:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Не найден источник геометрии в клонере")
            return False

        # Создаем новый узел эффектора
        effector_node = cloner_group.nodes.new('GeometryNodeGroup')
        effector_node.name = f"Effector_{effector_mod.name}"
        effector_node.node_tree = effector_group

        # Устанавливаем положение узла между источником и выходом
        source_pos = source_node.location
        output_pos = group_output.location
        effector_node.location = (source_pos.x + (output_pos.x - source_pos.x) * 0.5, source_pos.y)

        # Копируем значения параметров из модификатора эффектора
        for input_socket in [s for s in effector_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']:
            if input_socket.name in ['Geometry']:
                continue  # Пропускаем вход геометрии

            # Если параметр не имеет установленного значения в модификаторе, пропускаем
            if input_socket.identifier not in effector_mod:
                continue

            # Копируем значение параметра из модификатора в узел
            try:
                effector_node.inputs[input_socket.name].default_value = effector_mod[input_socket.identifier]
            except (KeyError, TypeError) as e:
                print(f"[DEBUG] apply_effector_to_stacked_cloner: Не удалось установить значение для {input_socket.name}: {e}")
                pass

        # Удаляем существующую связь от источника к выходу
        links_to_remove = []
        for link in cloner_group.links:
            if link.from_node == source_node and link.to_node == group_output:
                links_to_remove.append(link)

        for link in links_to_remove:
            try:
                cloner_group.links.remove(link)
            except RuntimeError:
                pass

        # Создаем новые связи: источник -> эффектор -> (выход или анти-рекурсия)
        cloner_group.links.new(source_socket, effector_node.inputs['Geometry'])

        # Если есть узел анти-рекурсии
        if anti_recursion_switch:
            # Подключаем эффектор к входу False узла анти-рекурсии
            cloner_group.links.new(effector_node.outputs['Geometry'], anti_recursion_switch.inputs[False])
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Подключен эффектор к входу False узла анти-рекурсии")

            # Удаляем узел Effector_Input, если он есть
            if effector_input_node:
                try:
                    cloner_group.nodes.remove(effector_input_node)
                except RuntimeError:
                    # Узел уже был удален
                    pass
        else:
            # Иначе подключаем напрямую к выходу
            cloner_group.links.new(effector_node.outputs['Geometry'], group_output.inputs['Geometry'])
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Подключен эффектор к выходу")

        # Отключаем рендер эффектора, т.к. его эффект уже применен через клонер
        effector_mod.show_render = False

        # Убедимся, что сохранены флаги стекового клонера
        cloner_mod["is_stacked_cloner"] = True
        cloner_group["is_stacked_cloner"] = True

        # Получаем тип клонера
        cloner_type = cloner_mod.get("cloner_type", "")
        if not cloner_type and cloner_group.get("cloner_type"):
            cloner_type = cloner_group["cloner_type"]

        # Если определен тип клонера, фиксируем его
        if cloner_type:
            cloner_mod["cloner_type"] = cloner_type
            cloner_group["cloner_type"] = cloner_type

        print(f"[DEBUG] apply_effector_to_stacked_cloner: Эффектор успешно применен")
        return True

    except Exception as e:
        print(f"[DEBUG] apply_effector_to_stacked_cloner: Ошибка при применении старого метода: {e}")
        import traceback
        traceback.print_exc()

        # Восстанавливаем прямую связь в случае ошибки
        try:
            # Используем функцию restore_direct_connection для восстановления связей
            restore_direct_connection_improved(cloner_mod.node_group)
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Восстановлена прямая связь после ошибки")
        except Exception as restore_e:
            print(f"[DEBUG] apply_effector_to_stacked_cloner: Ошибка при восстановлении связи: {restore_e}")

        return False
