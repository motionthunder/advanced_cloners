import bpy
import bmesh
from ..core.common.constants import CLONER_MOD_NAMES
from ..core.utils.cloner_utils import get_cloner_chain_for_object
from ..core.utils.node_utils import find_socket_by_name
from ..core.factories.component_factory import ComponentFactory
from ..models.cloners.grid_cloner import GridCloner
from ..models.cloners.linear_cloner import LinearCloner
from ..models.cloners.circle_cloner import CircleCloner
from ..core.utils.collection_cloner import create_collection_cloner_nodetree
from ..core.utils.cloner_effector_utils import update_cloner_with_effectors

# Импортируем функции из новых модулей
from .helpers.object_cloner import (
    create_object_cloner,
    create_standard_object_cloner, 
    setup_basic_node_structure
)
from .helpers.collection_cloner import create_collection_cloner
from .helpers.chain_utils import (
    delete_cloner,
    move_cloner_modifier,
    ClonerChainUpdateHandler,
    select_previous_cloner_in_chain
)
from .helpers.params_utils import (
    setup_grid_cloner_params,
    setup_linear_cloner_params,
    setup_circle_cloner_params
)
from .helpers.stacked_cloner import create_stacked_cloner
from .helpers.common_utils import find_layer_collection

# Функции для создания и управления клонерами
# Объединяет функциональность из:
# - object_cloner.py
# - collection_cloner.py
# - cloner_management.py
# - chain_utils.py
# - cloner_params.py
# - stacked_cloner.py






