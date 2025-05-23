"""
Глобальные переменные для отслеживания состояния эффекторов.
"""

# Глобальные переменные для отслеживания состояния эффекторов
_effector_last_parameters = {}
_effector_handler_blocked = False
_effector_handler_call_count = 0
_EFFECTOR_HANDLER_MAX_CALLS = 3 