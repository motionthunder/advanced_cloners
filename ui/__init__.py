"""
UI components for Advanced Cloners addon.
"""

# Импортируем все UI компоненты для регистрации
from . import panels
from . import operators
from . import common

# Функции регистрации и отмены регистрации
def register():
    panels.register()
    operators.register()

def unregister():
    operators.unregister()
    panels.unregister() 