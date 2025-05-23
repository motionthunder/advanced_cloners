import bpy
from abc import ABC, abstractmethod

class ClonerBase(ABC):
    """Base abstract class for all cloners.

    Provides common interface and shared functionality for all cloner types.
    Each cloner implementation should extend this class and implement abstract methods.
    """

    @classmethod
    @abstractmethod
    def create_logic_group(cls, name_suffix=""):
        """Create the core logic node group for this cloner type.

        Args:
            name_suffix: Optional suffix to append to the logic group name

        Returns:
            The created node group
        """
        pass

    @classmethod
    @abstractmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Create the main interface node group that uses the logic group.

        Args:
            logic_group: The logic node group to use
            name_suffix: Optional suffix to append to the main group name

        Returns:
            The created node group
        """
        pass

    @classmethod
    def create_node_group(cls, name_suffix=""):
        """Create a complete cloner node group with the proper structure.

        This method implements the template pattern:
        1. Create the logic group
        2. Create the main group
        3. Return the main group

        Args:
            name_suffix: Optional suffix to append to the node group names

        Returns:
            The created main node group
        """
        # Create the core logic group
        logic_group = cls.create_logic_group(name_suffix)

        # Create the main interface group that uses the logic group
        main_group = cls.create_main_group(logic_group, name_suffix)

        return main_group

    @staticmethod
    def setup_common_global_interface(node_group):
        """Add common global interface sockets used by all cloners.

        Args:
            node_group: The node group to add interface sockets to

        Returns:
            None
        """
        # Global Transform Settings
        global_position_input = node_group.interface.new_socket(name="Global Position", in_out='INPUT', socket_type='NodeSocketVector')
        global_position_input.default_value = (0.0, 0.0, 0.0)

        global_rotation_input = node_group.interface.new_socket(name="Global Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        global_rotation_input.default_value = (0.0, 0.0, 0.0)
        global_rotation_input.subtype = 'EULER'

    @staticmethod
    def setup_common_random_interface(node_group):
        """Add common random settings interface sockets used by all cloners.

        Args:
            node_group: The node group to add interface sockets to

        Returns:
            None
        """
        # Random Settings
        random_position_input = node_group.interface.new_socket(name="Random Position", in_out='INPUT', socket_type='NodeSocketVector')
        random_position_input.default_value = (0.0, 0.0, 0.0)

        random_rotation_input = node_group.interface.new_socket(name="Random Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        random_rotation_input.default_value = (0.0, 0.0, 0.0)
        random_rotation_input.subtype = 'EULER'

        random_scale_input = node_group.interface.new_socket(name="Random Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        random_scale_input.default_value = 0.0
        random_scale_input.min_value = 0.0
        random_scale_input.max_value = 1.0

        seed_input = node_group.interface.new_socket(name="Random Seed", in_out='INPUT', socket_type='NodeSocketInt')
        seed_input.default_value = 0
        seed_input.min_value = 0
        seed_input.max_value = 10000

        # Instance Collection options
        pick_instance_input = node_group.interface.new_socket(name="Pick Random Instance", in_out='INPUT', socket_type='NodeSocketBool')
        pick_instance_input.default_value = False

    @staticmethod
    def setup_instance_input_nodes(nodes, links, group_input, realize_instances=False):
        """Set up common instance input nodes used by all cloners.

        Создает узлы для инстансинга объекта, используя подход аналогичный клонированию коллекций.
        Вместо получения геометрии напрямую, мы создаем инстанс объекта и используем его для клонирования.

        Args:
            nodes: The nodes collection to add to
            links: The links collection to add to
            group_input: The group input node
            realize_instances: Whether to add a Realize Instances node to prevent recursion depth issues

        Returns:
            A tuple containing (object_info_node, instances_output)
        """
        # Создаем узел ObjectInfo для получения инстансов объекта (аналогично работе с коллекцией)
        object_info = nodes.new('GeometryNodeObjectInfo')
        object_info.transform_space = 'RELATIVE'
        object_info.name = "Source Object Info"
        object_info.location = (-800, 0)

        # Очень важно - устанавливаем параметр как инстансы вместо геометрии
        # Эта опция есть в Blender 4.0+
        if hasattr(object_info, 'instance_mode'):
            object_info.instance_mode = True  # Используем инстансы объекта вместо его геометрии
            print("Set GeometryNodeObjectInfo to instance mode for proper cloning")

        # Соединяем вход Object с группой, чтобы он получал значение извне
        if 'Object' in group_input.outputs:
            try:
                links.new(group_input.outputs['Object'], object_info.inputs['Object'])
                print("Connected Object input to ObjectInfo node")
            except Exception as e:
                print(f"Warning: Could not connect Object to ObjectInfo: {e}")

        # Для совместимости с методом клонирования коллекций,
        # мы возвращаем выход инстансов вместо геометрии
        # В Blender 4.0+ это будет 'Instances', а в более старых версиях используем 'Geometry'
        output_socket = 'Instances' if 'Instances' in object_info.outputs else 'Geometry'

        # Если требуется "реализация" инстансов для предотвращения проблем с глубиной рекурсии
        if realize_instances:
            # Добавляем узел Realize Instances для преобразования инстансов в реальную геометрию
            realize_node = nodes.new('GeometryNodeRealizeInstances')
            realize_node.name = "Realize Instances (Anti-Recursion)"
            realize_node.location = (-650, 0)

            # Соединяем выход ObjectInfo с входом Realize Instances
            links.new(object_info.outputs[output_socket], realize_node.inputs['Geometry'])

            # Возвращаем узел ObjectInfo и выход Realize Instances
            return object_info, realize_node.outputs['Geometry']
        else:
            # Return both the node and its instances output for further connections
            return object_info, object_info.outputs[output_socket]