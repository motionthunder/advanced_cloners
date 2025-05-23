import bpy
from abc import ABC, abstractmethod

class EffectorBase(ABC):
    """Базовый абстрактный класс для всех эффекторов.
    
    Предоставляет общий интерфейс и функциональность для всех типов эффекторов.
    Каждый конкретный эффектор должен наследоваться от этого класса и реализовывать
    абстрактные методы.
    """
    
    @classmethod
    @abstractmethod
    def create_logic_group(cls, name_suffix=""):
        """Создать основную логическую группу узлов для этого типа эффектора.
        
        Args:
            name_suffix: Опциональный суффикс для имени группы
            
        Returns:
            Созданная группа узлов с логикой эффектора
        """
        pass
    
    @classmethod
    @abstractmethod
    def create_main_group(cls, logic_group, name_suffix=""):
        """Создать основную группу интерфейса, использующую логическую группу.
        
        Args:
            logic_group: Логическая группа узлов для использования
            name_suffix: Опциональный суффикс для имени группы
            
        Returns:
            Созданная основная группа узлов
        """
        pass
    
    @classmethod
    def create_node_group(cls, name_suffix=""):
        """Создать полную группу узлов эффектора с правильной структурой.
        
        Метод реализует шаблонный метод:
        1. Создать логическую группу
        2. Создать основную группу
        3. Вернуть основную группу
        
        Args:
            name_suffix: Опциональный суффикс для имени групп
            
        Returns:
            Созданная основная группа узлов
        """
        # Создаем базовую логическую группу
        logic_group = cls.create_logic_group(name_suffix)
        
        # Создаем основную группу интерфейса, использующую логическую группу
        main_group = cls.create_main_group(logic_group, name_suffix)
        
        return main_group
    
    @staticmethod
    def setup_common_interface(node_group):
        """Добавить общие сокеты интерфейса, используемые всеми эффекторами.
        
        Args:
            node_group: Группа узлов, в которую добавляются сокеты
        """
        # Входной сокет геометрии (обязательный)
        node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        
        # Выходной сокет геометрии (обязательный)
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        # Базовые параметры управления
        enable_input = node_group.interface.new_socket(name="Enable", in_out='INPUT', socket_type='NodeSocketBool')
        enable_input.default_value = True
        
        strength_input = node_group.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
        strength_input.default_value = 1.0
        strength_input.min_value = 0.0
        strength_input.max_value = 1.0
    
    @staticmethod
    def setup_transform_interface(node_group):
        """Добавить общий интерфейс для трансформаций.
        
        Args:
            node_group: Группа узлов, в которую добавляются сокеты
        """
        # Параметры трансформации
        position_input = node_group.interface.new_socket(name="Position", in_out='INPUT', socket_type='NodeSocketVector')
        position_input.default_value = (0.0, 0.0, 0.0)
        
        rotation_input = node_group.interface.new_socket(name="Rotation", in_out='INPUT', socket_type='NodeSocketVector')
        rotation_input.default_value = (0.0, 0.0, 0.0)
        rotation_input.subtype = 'EULER'
        
        scale_input = node_group.interface.new_socket(name="Scale", in_out='INPUT', socket_type='NodeSocketVector')
        scale_input.default_value = (0.0, 0.0, 0.0)
    
    @staticmethod
    def setup_field_interface(node_group):
        """Добавить интерфейс для управления полями.
        
        Args:
            node_group: Группа узлов, в которую добавляются сокеты
        """
        field_input = node_group.interface.new_socket(name="Field", in_out='INPUT', socket_type='NodeSocketFloat')
        field_input.default_value = 1.0
        field_input.min_value = 0.0
        field_input.max_value = 1.0
        
        use_field_input = node_group.interface.new_socket(name="Use Field", in_out='INPUT', socket_type='NodeSocketBool')
        use_field_input.default_value = False
    
    @staticmethod
    def setup_nodes_for_field_control(nodes, links, group_input, enable_path, field_path):
        """Настроить общие ноды для управления влиянием поля.
        
        Args:
            nodes: Коллекция узлов для добавления
            links: Коллекция связей для добавления
            group_input: Узел входа группы
            enable_path: Путь к входу Enable
            field_path: Путь к входу Field
            
        Returns:
            field_factor: Фактор влияния поля (выход узла для последующего использования)
        """
        # Смешивание между 1.0 и значением поля
        mix_field = nodes.new('ShaderNodeMixRGB')
        mix_field.blend_type = 'MIX'
        mix_field.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)  # Если поле не используется
        links.new(group_input.outputs['Use Field'], mix_field.inputs[0])  # Фактор смешивания - напрямую используем выход из group_input
        # Подключаем значение поля ко второму входу напрямую
        links.new(group_input.outputs['Field'], mix_field.inputs[2])
        
        # Смешивание с Enable параметром (можно отключить эффект)
        enable_factor = nodes.new('ShaderNodeMath')
        enable_factor.operation = 'MULTIPLY'
        links.new(group_input.outputs['Enable'], enable_factor.inputs[0])
        links.new(mix_field.outputs[0], enable_factor.inputs[1])
        
        # Смешивание с Strength параметром (можно регулировать силу)
        strength_factor = nodes.new('ShaderNodeMath')
        strength_factor.operation = 'MULTIPLY'
        links.new(enable_factor.outputs[0], strength_factor.inputs[0])
        links.new(group_input.outputs['Strength'], strength_factor.inputs[1])
        
        return strength_factor.outputs[0] 