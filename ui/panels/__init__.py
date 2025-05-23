"""
UI panels for Advanced Cloners addon.
"""

# Импортируем все панели для автоматической регистрации
from . import cloner_panel
from . import effector_panel
from . import field_panel

# Функции регистрации и отмены регистрации
def register():
    cloner_panel.register()
    effector_panel.register()
    field_panel.register()

def unregister():
    field_panel.unregister()
    effector_panel.unregister()
    cloner_panel.unregister() 