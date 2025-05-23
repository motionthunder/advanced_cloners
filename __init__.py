bl_info = {
    "name": "Advanced Cloners",
    "author": "Serhii Marchenko",
    "version": (0, 0, 1),
    "blender": (4, 4, 3),
    "location": "View3D > Sidebar > Cloners",
    "description": "Implements Cinema 4D-like cloner system using Geometry Nodes",
    "warning": "BETA",
    "wiki_url": "",
    "category": "Object",
}

import bpy

# Импортируем основные компоненты
from .core.factories.registration import auto_register_modules, auto_unregister_modules
# Импортируем обработчики событий напрямую из event_handlers
from .core.utils.event_handlers import (
    cloner_chain_update_handler,
    cloner_collection_update_handler,
    register_effector_update_handler,
    unregister_effector_update_handler
)
# Импортируем утилиты клонера из duplicator.py
from .core.utils.duplicator import (
    get_or_create_duplicate_for_cloner,
    restore_original_object,
    cleanup_empty_cloner_collections
)
# Импорт функций из различных модулей
from .core.utils.cloner_effector_utils import update_cloner_with_effectors
from .core.utils.service_utils import force_update_cloners
from .operations.cloner_helpers import ClonerChainUpdateHandler
# Импортируем операторы обновления клонеров
from .operations.fix_recursion import CLONER_OT_fix_recursion_depth, CLONER_OT_update_all_effectors
from .operations.fix_recursion_improved import CLONER_OT_fix_effector_issues

# Импортируем UI операторы
from .ui.operators.cloner_ui_ops import (
    CLONER_OT_add_effector,
    CLONER_OT_remove_effector,
    CLONER_OT_update_active_collection,
    CLONER_OT_toggle_expanded,
    CLONER_OT_link_effector,
    CLONER_OT_unlink_effector,
    CLONER_OT_add_effector_to_cloner,
    CLONER_OT_set_active_in_chain,
    CLONER_OT_refresh_effector
)
from .ui.operators.effector_ui_ops import (
    EFFECTOR_OT_toggle_expanded,
    EFFECTOR_OT_add_field,
    EFFECTOR_OT_remove_field,
    EFFECTOR_OT_auto_link,
    EFFECTOR_OT_update_stacked_cloners
)
from .ui.operators.field_ui_ops import (
    FIELD_OT_toggle_expanded,
    FIELD_OT_create_field,
    FIELD_OT_select_gizmo,
    FIELD_OT_create_sphere_gizmo,
    FIELD_OT_adjust_field_strength
)


# Свойства для UI
def register_ui_properties():
    from bpy.props import StringProperty, EnumProperty, BoolProperty
    import bpy

    # Свойства для создания клонеров
    bpy.types.Scene.source_type_for_cloner = EnumProperty(
        name="Source",
        description="What to clone: single object or entire collection",
        items=[
            ('OBJECT', "Object", "Clone selected object"),
            ('COLLECTION', "Collection", "Clone selected collection"),
        ],
        default='OBJECT'
    )

    bpy.types.Scene.collection_to_clone = StringProperty()

    # Свойства для отображения цепочки клонеров
    bpy.types.Scene.show_cloner_chain = BoolProperty(default=False)
    bpy.types.Scene.active_cloner_in_chain = StringProperty(default="")
    bpy.types.Scene.active_effector_for_cloner = StringProperty(default="")

    # Импортируем callback для стековых модификаторов
    from .core.utils.anti_recursion_utils import update_stacked_modifiers_callback

    # Свойство для стековых модификаторов
    bpy.types.Scene.use_stacked_modifiers = bpy.props.BoolProperty(
        default=False,
        name="Use Stacked Modifiers",
        description="Create all cloners as modifiers on a single object instead of creating a chain of objects. This allows you to reorder cloners by moving modifiers up/down.",
        update=update_stacked_modifiers_callback
    )

    # Импортируем callback для анти-рекурсии
    from .core.utils.anti_recursion_utils import update_anti_recursion_callback

    # Свойство для автоматического применения анти-рекурсии
    bpy.types.Scene.use_anti_recursion = bpy.props.BoolProperty(
        default=True,
        name="Anti-Recursion",
        description="Automatically apply anti-recursion fix to all new cloners. This prevents recursion depth issues when creating chains of cloners.",
        update=update_anti_recursion_callback
    )

    # Свойство для выбора эффектора в UI
    bpy.types.Scene.effector_to_link = StringProperty(
        name="Effector to Link",
        description="Select an effector to link to the cloner",
        default=""
    )

def unregister_ui_properties():
    import bpy

    # Удаляем свойства
    if hasattr(bpy.types.Scene, "source_type_for_cloner"):
        del bpy.types.Scene.source_type_for_cloner

    if hasattr(bpy.types.Scene, "collection_to_clone"):
        del bpy.types.Scene.collection_to_clone

    if hasattr(bpy.types.Scene, "show_cloner_chain"):
        del bpy.types.Scene.show_cloner_chain

    if hasattr(bpy.types.Scene, "active_cloner_in_chain"):
        del bpy.types.Scene.active_cloner_in_chain

    if hasattr(bpy.types.Scene, "active_effector_for_cloner"):
        del bpy.types.Scene.active_effector_for_cloner

    # Удаляем свойство стековых модификаторов
    if hasattr(bpy.types.Scene, "use_stacked_modifiers"):
        del bpy.types.Scene.use_stacked_modifiers

    # Удаляем свойство автоматического применения анти-рекурсии
    if hasattr(bpy.types.Scene, "use_anti_recursion"):
        del bpy.types.Scene.use_anti_recursion

    # Удаляем свойство для выбора эффектора
    if hasattr(bpy.types.Scene, "effector_to_link"):
        del bpy.types.Scene.effector_to_link

# Классы UI операторов для регистрации
ui_operators_classes = (
    # Операторы клонеров
    CLONER_OT_add_effector,
    CLONER_OT_remove_effector,
    CLONER_OT_update_active_collection,
    CLONER_OT_toggle_expanded,
    CLONER_OT_link_effector,
    CLONER_OT_unlink_effector,
    CLONER_OT_add_effector_to_cloner,
    CLONER_OT_set_active_in_chain,
    CLONER_OT_refresh_effector,
    CLONER_OT_fix_recursion_depth,       # Оператор для исправления проблем с рекурсией
    CLONER_OT_update_all_effectors,      # Оператор для обновления всех клонеров с эффекторами
    CLONER_OT_fix_effector_issues,       # Оператор для исправления проблем с эффекторами

    # Операторы эффекторов
    EFFECTOR_OT_toggle_expanded,
    EFFECTOR_OT_add_field,
    EFFECTOR_OT_remove_field,
    EFFECTOR_OT_auto_link,
    EFFECTOR_OT_update_stacked_cloners,

    # Операторы полей
    FIELD_OT_toggle_expanded,
    FIELD_OT_create_field,
    FIELD_OT_select_gizmo,
    FIELD_OT_create_sphere_gizmo,
    FIELD_OT_adjust_field_strength,
)

# РЕГИСТРАЦИЯ

def register():
    print("Registering Advanced Cloners addon...")

    # Register UI properties
    print("Registering UI properties...")
    register_ui_properties()
    print("UI properties registered")

    # Напрямую регистрируем UI операторы
    print("Registering UI operators...")
    for cls in ui_operators_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Error registering {cls.__name__}: {e}")
    print("UI operators registered")

    # Register GN modules с использованием автоматической регистрации
    print("Registering GN modules...")

    # Автоматическая регистрация эффекторов, клонеров и полей
    auto_register_modules('advanced_cloners.models.effectors')
    auto_register_modules('advanced_cloners.models.cloners')
    auto_register_modules('advanced_cloners.models.fields')

    print("GN modules registered")

    # Register UI components с использованием улучшенной автоматической регистрации
    print("Registering UI components...")
    auto_register_modules('advanced_cloners.ui')
    print("UI components registered")

    # Register operators
    print("Registering operators...")
    auto_register_modules('advanced_cloners.operations')
    print("Operators registered")

    # Регистрация обработчика сцены для отслеживания выделения в цепочке клонеров
    if hasattr(bpy.app.handlers, 'depsgraph_update_post'):
        if cloner_chain_update_handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(cloner_chain_update_handler)

    # Регистрация обработчика для обновления выбранной коллекции
    if hasattr(bpy.app.handlers, 'scene_update_post'):
        if cloner_collection_update_handler not in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.append(cloner_collection_update_handler)
    elif hasattr(bpy.app.handlers, 'depsgraph_update_post'):
        if cloner_collection_update_handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(cloner_collection_update_handler)

    # Регистрация обработчика цепочки клонеров для синхронизации изменений параметров
    ClonerChainUpdateHandler.register()

    # Регистрация обработчика изменений эффекторов
    register_effector_update_handler()

    print("Advanced Cloners addon registered successfully")

def unregister():
    print("Unregistering Advanced Cloners addon...")

    # Напрямую отменяем регистрацию UI операторов
    print("Unregistering UI operators...")
    for cls in reversed(ui_operators_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {e}")
    print("UI operators unregistered")

    # Удаляем обработчики сцены
    if hasattr(bpy.app.handlers, 'depsgraph_update_post'):
        if cloner_chain_update_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(cloner_chain_update_handler)
        if cloner_collection_update_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(cloner_collection_update_handler)
    if hasattr(bpy.app.handlers, 'scene_update_post'):
        if cloner_collection_update_handler in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.remove(cloner_collection_update_handler)

    # Отмена регистрации обработчика цепочки клонеров
    ClonerChainUpdateHandler.unregister()

    # Отмена регистрации обработчика изменений эффекторов
    unregister_effector_update_handler()

    # Восстанавливаем все оригинальные объекты и удаляем дубликаты
    try:
        # Находим и восстанавливаем все объекты с оригинальными ссылками
        for obj in bpy.data.objects:
            if "original_obj" in obj:
                restore_original_object(obj)

        # Очищаем пустые коллекции клонеров
        cleanup_empty_cloner_collections()

    except Exception as e:
        print(f"Ошибка при восстановлении оригинальных объектов: {e}")

    # Unregister operators
    print("Unregistering operators...")
    auto_unregister_modules('advanced_cloners.operations')
    print("Operators unregistered")

    # Unregister UI components с использованием улучшенной автоматической отмены регистрации
    print("Unregistering UI components...")
    auto_unregister_modules('advanced_cloners.ui')
    print("UI components unregistered")

    # Unregister GN modules с использованием автоматической отмены регистрации
    print("Unregistering GN modules...")
    auto_unregister_modules('advanced_cloners.models.fields')
    auto_unregister_modules('advanced_cloners.models.cloners')
    auto_unregister_modules('advanced_cloners.models.effectors')
    print("GN modules unregistered")

    # Unregister UI properties
    print("Unregistering UI properties...")
    unregister_ui_properties()
    print("UI properties unregistered")

    print("Advanced Cloners addon unregistered successfully")

# Для поддержки запуска аддона напрямую из Blender Text Editor
if __name__ == "__main__":
    register()
