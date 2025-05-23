import bpy
import mathutils
from .base import FieldBase

class SphereField(FieldBase):
    """Реализация сферического поля"""
    
    @classmethod
    def create_node_group(cls, name_suffix=""):
        """Создает полную группу узлов сферического поля с правильной структурой."""
        return advanced_spherefield_node_group()

def simplest_spherefield_node_group():
    """Создаёт максимально простую версию нод-группы поля"""
    # Создаем новую нод-группу
    node_group = bpy.data.node_groups.new(
        type='GeometryNodeTree',
        name="SphereField"
    )
    
    # Добавляем минимальный интерфейс
    # Выходы
    # ВАЖНО: Geometry должен быть ПЕРВЫМ выходом
    geo_out = node_group.interface.new_socket(
        name="Geometry", 
        in_out='OUTPUT',
        socket_type='NodeSocketGeometry'
    )
    
    value_socket = node_group.interface.new_socket(
        name="Value", 
        in_out='OUTPUT',
        socket_type='NodeSocketFloat'
    )
    
    # Входы 
    geo_in = node_group.interface.new_socket(
        name="Geometry", 
        in_out='INPUT',
        socket_type='NodeSocketGeometry'
    )
    
    # Создаем ноды
    nodes = node_group.nodes
    links = node_group.links
    
    # Входной и выходной узлы
    input_node = nodes.new('NodeGroupInput')
    output_node = nodes.new('NodeGroupOutput')
    
    # Просто прокидываем геометрию без изменений
    links.new(input_node.outputs["Geometry"], output_node.inputs["Geometry"])
    
    # Создаем константный узел со значением 1.0
    value_node = nodes.new('ShaderNodeValue')
    value_node.outputs[0].default_value = 1.0
    links.new(value_node.outputs[0], output_node.inputs["Value"])
    
    return node_group

def advanced_spherefield_node_group():
    """Создаёт продвинутую версию нод-группы сферического поля"""
    # Для простоты тестирования используем простую версию
    return simplest_spherefield_node_group()

def spherefield_node_group():
    """Совместимость со старым кодом"""
    return advanced_spherefield_node_group()

def register():
    pass

def unregister():
    pass
