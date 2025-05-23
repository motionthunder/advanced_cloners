"""
Operators for creating and managing effectors.
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty, BoolProperty

# Импортируем фабрику компонентов и константы
from ..core.factories.component_factory import ComponentFactory
from ..core.common.constants import EFFECTOR_MOD_NAMES, CLONER_NODE_GROUP_PREFIXES
from ..models.effectors import EFFECTOR_TYPES
from .helpers.effector_params_utils import setup_effector_params

class EFFECTOR_OT_create_effector(bpy.types.Operator):
    """Create a new effector"""
    bl_idname = "object.create_effector"
    bl_label = "Create Effector"
    bl_options = {'REGISTER', 'UNDO'}

    effector_type: bpy.props.StringProperty(default="RANDOM")
    use_custom_group: bpy.props.BoolProperty(default=True,
                                          name="Use Custom Group",
                                          description="Create the effector in a custom node group")

    def execute(self, context):
        if not context.active_object:
            self.report({'ERROR'}, "Please select an object")
            return {'CANCELLED'}

        obj = context.active_object

        # Проверяем, есть ли уже клонеры на активном объекте или в сцене
        has_cloner = False

        # Отладочная информация
        print(f"[DEBUG] Searching for cloners. CLONER_NODE_GROUP_PREFIXES = {CLONER_NODE_GROUP_PREFIXES}")

        # Функция для определения является ли группа узлов клонером
        def is_cloner_node_group(node_group_name):
            # Проверяем наличие в списке префиксов
            if node_group_name in CLONER_NODE_GROUP_PREFIXES or any(node_group_name.startswith(p) for p in CLONER_NODE_GROUP_PREFIXES):
                return True

            # Проверяем на другие известные префиксы
            prefixes = ["ObjectCloner", "CollectionCloner", "Grid_Stack", "Linear_Stack", "Circle_Stack"]
            if any(node_group_name.startswith(p) for p in prefixes):
                return True

            # Общая проверка на наличие слова "Cloner" в имени
            if "Cloner" in node_group_name:
                return True

            return False

        # Сначала проверяем на текущем объекте
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                if is_cloner_node_group(mod.node_group.name):
                    print(f"[DEBUG] Found cloner on current object: {mod.name}, node_group: {mod.node_group.name}")
                    has_cloner = True
                    break
                else:
                    print(f"[DEBUG] Modifier {mod.name} with node_group {mod.node_group.name} is not a cloner")

        # Если на активном объекте нет клонера, проверяем всю сцену
        if not has_cloner:
            print("[DEBUG] No cloners found on active object, checking scene...")
            for scene_obj in bpy.context.scene.objects:
                if scene_obj.modifiers:
                    for mod in scene_obj.modifiers:
                        if mod.type == 'NODES' and mod.node_group:
                            if is_cloner_node_group(mod.node_group.name):
                                print(f"[DEBUG] Found cloner in scene on object {scene_obj.name}: {mod.name}, node_group: {mod.node_group.name}")
                                has_cloner = True
                                break
                    if has_cloner:
                        break

        # Если нет клонеров ни на текущем объекте, ни в сцене вообще, показываем сообщение
        if not has_cloner:
            # Как временное решение - пропустим проверку, чтобы дать пользователю возможность создать эффектор
            print("[DEBUG] No cloners found in scene")
            self.report({'ERROR'}, "Please create a cloner first. Effectors can only affect cloners.")
            return {'CANCELLED'}

        # Используем фабрику для создания эффектора
        node_group = ComponentFactory.create_effector(
            effector_type=self.effector_type,
            use_custom_group=self.use_custom_group,
            obj=obj
        )

        if node_group is None:
            self.report({'ERROR'}, f"Failed to create node group for {self.effector_type} effector")
            return {'CANCELLED'}

        # Получаем базовое имя модификатора
        base_mod_name = EFFECTOR_MOD_NAMES[self.effector_type]

        # Создаем уникальное имя для модификатора
        modifier_name = base_mod_name
        counter = 1
        while modifier_name in obj.modifiers:
            modifier_name = f"{base_mod_name}.{counter:03d}"
            counter += 1

        # Добавляем модификатор, но НЕ АКТИВИРУЕМ его автоматически
        modifier = obj.modifiers.new(name=modifier_name, type='NODES')

        # Выключаем модификатор временно до привязки к клонеру
        # Это предотвратит исчезновение геометрии
        modifier.show_viewport = False  # Отключаем отображение эффектора вообще

        # Теперь безопасно устанавливаем группу узлов
        modifier.node_group = node_group

        # Устанавливаем параметры эффектора из конфигурационного файла
        try:
            # Временно отключаем эффектор
            for socket in node_group.interface.items_tree:
                if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Enable":
                    try:
                        modifier[socket.identifier] = False
                    except:
                        pass

            # Применяем параметры из конфигурационного файла
            setup_effector_params(modifier, self.effector_type)

            # Оставляем эффектор выключенным до привязки к клонеру
            for socket in node_group.interface.items_tree:
                if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT' and socket.name == "Enable":
                    try:
                        modifier[socket.identifier] = False
                    except:
                        pass
        except Exception as e:
            print(f"Ошибка при установке параметров эффектора: {e}")

        # По Cinema 4D подходу, эффекторы не имеют эффекта сами по себе,
        # они должны быть связаны с клонером, чтобы работать.
        # Для удобства настройки показываем в интерфейсе, но скрываем в viewport
        modifier.show_render = True
        modifier.show_viewport = False  # Отключаем отображение эффектора вообще

        # ВАЖНО: сбрасываем активный клонер в цепочке при создании эффектора
        # Это предотвратит зацикливание интерфейса, когда в меню цепочки
        # выбран клонер, не соответствующий активному объекту, на котором создается эффектор
        if hasattr(context.scene, "active_cloner_in_chain") and context.scene.active_cloner_in_chain:
            print(f"[DEBUG] Сбрасываем выбор клонера в цепочке при создании эффектора")
            context.scene.active_cloner_in_chain = ""

        self.report({'INFO'}, f"{base_mod_name} '{modifier_name}' создан. Свяжите его с клонером для использования.")
        return {'FINISHED'}


class EFFECTOR_OT_delete_effector(bpy.types.Operator):
    """Delete this effector"""
    bl_idname = "object.delete_effector"
    bl_label = "Delete Effector"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.active_object
        if obj and self.modifier_name in obj.modifiers:
            modifier = obj.modifiers[self.modifier_name]
            node_group = modifier.node_group

            # Удаляем модификатор
            obj.modifiers.remove(modifier)

            # Удаляем группу узлов, если она больше не используется
            if node_group and node_group.users == 0:
                bpy.data.node_groups.remove(node_group)

        return {'FINISHED'}


class EFFECTOR_OT_move_modifier(bpy.types.Operator):
    """Move modifier up or down"""
    bl_idname = "object.move_effector"
    bl_label = "Move Effector"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty()
    direction: bpy.props.EnumProperty(
        items=[
            ('UP', 'Up', 'Move up'),
            ('DOWN', 'Down', 'Move down')
        ]
    )

    def execute(self, context):
        obj = context.active_object
        if obj and self.modifier_name in obj.modifiers:
            if self.direction == 'UP':
                bpy.ops.object.modifier_move_up(modifier=self.modifier_name)
            else:
                bpy.ops.object.modifier_move_down(modifier=self.modifier_name)
        return {'FINISHED'}

# Список классов для регистрации
classes = (
    EFFECTOR_OT_create_effector,
    EFFECTOR_OT_delete_effector,
    EFFECTOR_OT_move_modifier
)

# Функции регистрации и отмены регистрации
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
