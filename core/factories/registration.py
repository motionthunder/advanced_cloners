"""
Утилиты для автоматической регистрации модулей аддона.
"""

import bpy
import inspect
import importlib
import pkgutil
from typing import Type, List, Dict, Any, Optional, Callable, Union
import os.path

# Список устаревших файлов, которые нужно игнорировать при регистрации
DEPRECATED_FILES = [
    "advanced_cloners.src.ui.cloner_panel",
    "advanced_cloners.src.ui.effector_panel",
    "advanced_cloners.src.ui.field_panel"
]

def auto_register_modules(package_path: str, base_class: Optional[Type] = None) -> List[Any]:
    """
    Автоматически регистрирует все модули из указанного пакета и его подпакетов.
    
    Args:
        package_path: Путь к пакету (например, 'advanced_cloners.src.effectors')
        base_class: Если указан, регистрирует только классы-наследники этого класса
    
    Returns:
        Список зарегистрированных модулей или классов
    """
    registered_items = []
    
    try:
        # Импортируем пакет
        package = importlib.import_module(package_path)
        
        # Перебираем все модули и подпакеты в пакете
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
            # Пропускаем устаревшие файлы
            if name in DEPRECATED_FILES:
                print(f"Skipping deprecated module: {name}")
                continue

            if is_pkg:
                # Если это подпакет, рекурсивно регистрируем его
                try:
                    sub_package = importlib.import_module(name)
                    
                    # Проверяем, есть ли у подпакета методы register/unregister
                    if hasattr(sub_package, 'register'):
                        sub_package.register()
                        registered_items.append(sub_package)
                        print(f"Registered sub-package: {name}")
                    else:
                        # Если у подпакета нет методов register/unregister, рекурсивно обрабатываем его
                        sub_items = auto_register_modules(name, base_class)
                        registered_items.extend(sub_items)
                except Exception as e:
                    print(f"Error registering sub-package {name}: {e}")
            
            else:  # Если это модуль
                try:
                    # Импортируем модуль
                    module = importlib.import_module(name)
                    
                    # Если указан базовый класс, находим все классы-наследники
                    if base_class:
                        for obj_name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, base_class) and obj != base_class:
                                # Регистрируем найденный класс, если у него есть метод register
                                if hasattr(obj, 'register'):
                                    obj.register()
                                    registered_items.append(obj)
                                    print(f"Registered class: {obj.__name__}")
                    else:
                        # Регистрируем сам модуль, если у него есть метод register
                        if hasattr(module, 'register'):
                            module.register()
                            registered_items.append(module)
                            print(f"Registered module: {name}")
                
                except Exception as e:
                    print(f"Error registering module {name}: {e}")
    
    except Exception as e:
        print(f"Error during auto-registration: {e}")
    
    return registered_items


def auto_unregister_modules(package_path: str, base_class: Optional[Type] = None) -> None:
    """
    Автоматически отменяет регистрацию всех модулей из указанного пакета и его подпакетов.
    
    Args:
        package_path: Путь к пакету
        base_class: Если указан, отменяет регистрацию только классов-наследников этого класса
    """
    try:
        # Импортируем пакет
        package = importlib.import_module(package_path)
        
        # Перебираем все модули и подпакеты в пакете в обратном порядке
        modules = list(pkgutil.iter_modules(package.__path__, package.__name__ + '.'))
        modules.reverse()
        
        for _, name, is_pkg in modules:
            # Пропускаем устаревшие файлы
            if name in DEPRECATED_FILES:
                print(f"Skipping deprecated module: {name}")
                continue

            if is_pkg:
                # Если это подпакет, рекурсивно отменяем его регистрацию
                try:
                    sub_package = importlib.import_module(name)
                    
                    # Проверяем, есть ли у подпакета методы register/unregister
                    if hasattr(sub_package, 'unregister'):
                        sub_package.unregister()
                        print(f"Unregistered sub-package: {name}")
                    else:
                        # Если у подпакета нет методов register/unregister, рекурсивно обрабатываем его
                        auto_unregister_modules(name, base_class)
                except Exception as e:
                    print(f"Error unregistering sub-package {name}: {e}")
            
            else:  # Если это модуль
                try:
                    # Импортируем модуль
                    module = importlib.import_module(name)
                    
                    # Если указан базовый класс, находим все классы-наследники
                    if base_class:
                        for obj_name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, base_class) and obj != base_class:
                                # Отменяем регистрацию найденного класса
                                if hasattr(obj, 'unregister'):
                                    obj.unregister()
                                    print(f"Unregistered class: {obj.__name__}")
                    else:
                        # Отменяем регистрацию самого модуля
                        if hasattr(module, 'unregister'):
                            module.unregister()
                            print(f"Unregistered module: {name}")
                
                except Exception as e:
                    print(f"Error unregistering module {name}: {e}")
    
    except Exception as e:
        print(f"Error during auto-unregistration: {e}") 