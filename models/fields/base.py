import bpy
from abc import ABC, abstractmethod

class FieldBase(ABC):
    """Базовый абстрактный класс для всех полей.
    
    Предоставляет общий интерфейс и функциональность для всех типов полей.
    Каждый конкретный тип поля должен наследоваться от этого класса и 
    реализовывать абстрактные методы.
    """
    
    @classmethod
    @abstractmethod
    def create_node_group(cls, name_suffix=""):
        """Создать полную группу узлов поля с правильной структурой.
        
        Args:
            name_suffix: Опциональный суффикс для имени группы
            
        Returns:
            Созданная группа узлов
        """
        pass
    
    @staticmethod
    def setup_common_interface(node_group):
        """Добавить общие сокеты интерфейса, используемые всеми полями.
        
        Args:
            node_group: Группа узлов, в которую добавляются сокеты
        """
        # Входной сокет геометрии (обязательный)
        node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        
        # Выходной сокет геометрии (обязательный)
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        # Выходной сокет поля
        field_socket = node_group.interface.new_socket(name="Field", in_out='OUTPUT', socket_type='NodeSocketFloat')
        field_socket.default_value = 0.0
        
        # Базовые параметры управления
        strength_socket = node_group.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
        strength_socket.default_value = 1.0
        strength_socket.min_value = 0.0
        strength_socket.max_value = 1.0
        
        falloff_socket = node_group.interface.new_socket(name="Falloff", in_out='INPUT', socket_type='NodeSocketFloat')
        falloff_socket.default_value = 0.0
        falloff_socket.min_value = 0.0
        falloff_socket.max_value = 1.0
    
    @staticmethod
    def setup_field_nodes(nodes, links, group_input, group_output):
        """Настроить базовые узлы для работы поля.
        
        Args:
            nodes: Коллекция узлов для добавления
            links: Коллекция связей для добавления
            group_input: Узел входа группы
            group_output: Узел выхода группы
        """
        # Прокидываем геометрию без изменений (обязательно для модификаторов)
        links.new(group_input.outputs["Geometry"], group_output.inputs["Geometry"])
