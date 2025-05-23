"""
Operations for Advanced Cloners addon.
"""

import bpy
from .cloner_ops import *  # Импортируем все операторы клонеров
from .effector_ops import * # Импортируем все операторы эффекторов
# Не импортируем .field_ops, так как его операторы дублируют операторы в ui/operators/field_ui_ops.py

def register():
    # Здесь мы вручную регистрируем нужные операторы
    from .cloner_ops import CLONER_OT_create_cloner, CLONER_OT_create_effector
    from .effector_ops import EFFECTOR_OT_create_effector
    
    # Регистрируем классы операторов
    bpy.utils.register_class(CLONER_OT_create_cloner)
    bpy.utils.register_class(CLONER_OT_create_effector)
    bpy.utils.register_class(EFFECTOR_OT_create_effector)
    
    # Не регистрируем FIELD_OT_create_field из field_ops.py!

def unregister():
    # Отмена регистрации в обратном порядке
    from .cloner_ops import CLONER_OT_create_cloner, CLONER_OT_create_effector
    from .effector_ops import EFFECTOR_OT_create_effector
    
    # Отменяем регистрацию классов операторов
    bpy.utils.unregister_class(EFFECTOR_OT_create_effector)
    bpy.utils.unregister_class(CLONER_OT_create_effector)
    bpy.utils.unregister_class(CLONER_OT_create_cloner)
    
    # Не отменяем регистрацию FIELD_OT_create_field из field_ops.py! 