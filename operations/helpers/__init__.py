"""
Вспомогательные функции для операций клонирования.
"""

# Реэкспорт всех функций для обратной совместимости
from .object_cloner import (
    create_object_cloner,
    create_standard_object_cloner,
    setup_basic_node_structure
)

from .collection_cloner import (
    create_collection_cloner
)

from .chain_utils import (
    delete_cloner,
    move_cloner_modifier,
    ClonerChainUpdateHandler,
    update_cloner_chain,
    select_previous_cloner_in_chain
)

from .params_utils import (
    setup_grid_cloner_params,
    setup_linear_cloner_params,
    setup_circle_cloner_params
)

from .stacked_cloner import (
    create_stacked_cloner
)

from .common_utils import (
    find_layer_collection,
    register_chain_update
)

# Импортируем функции для работы с эффекторами и полями
try:
    from .effector_params_utils import (
        setup_random_effector_params,
        setup_noise_effector_params,
        setup_effector_params
    )
except ImportError:
    pass

try:
    from .field_params_utils import (
        setup_sphere_field_params,
        setup_field_params
    )
except ImportError:
    pass