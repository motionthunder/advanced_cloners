"""
Функции для работы с клонерами.
"""

# Импортируем функции из соответствующих модулей
from .base_utils import convert_array_to_tuple, get_active_cloner
from .globals import (
    _effector_last_parameters,
    _effector_handler_blocked,
    _effector_handler_call_count,
    _EFFECTOR_HANDLER_MAX_CALLS
)
from .cloner_effector_utils import (
    update_cloner_with_effectors, 
    restore_direct_connection,
    apply_effector_to_stacked_cloner
)
# Импортируем функции из event_handlers
from .event_handlers import (
    register_effector_update_handler,
    unregister_effector_update_handler
)
from .service_utils import (
    force_update_cloners
)
from .duplicator import (
    get_cloner_chain_for_object,
    get_or_create_duplicate_for_cloner,
    restore_original_object,
    cleanup_empty_cloner_collections
) 