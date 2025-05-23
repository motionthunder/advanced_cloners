"""
UI Constants for Advanced Cloners addon.

This module centralizes all UI-related constants used across the addon
to simplify maintenance and ensure consistent UI appearance.
"""

# Common UI scaling and padding
UI_SCALE_Y_STANDARD = 1.0
UI_SCALE_Y_LARGE = 1.2
UI_SCALE_Y_XLARGE = 1.5
UI_SCALE_Y_SMALL = 0.9

UI_STANDARD_PADDING = 5
UI_MEDIUM_PADDING = 10
UI_LARGE_PADDING = 20

# Panel margins and alignment
UI_STANDARD_MARGIN = 10
UI_PANEL_LEFT_MARGIN = 15
UI_PANEL_RIGHT_MARGIN = 15

# Alignment values
UI_ALIGN_LEFT = 0.0
UI_ALIGN_CENTER = 0.5
UI_ALIGN_RIGHT = 1.0

# Cloner panel constants
UI_CLONER_PANEL_CATEGORY = "Cloners"

# Stacked cloner UI constants
UI_STACKED_LABEL_TEXT = "Stacking Clones:"
UI_STACKED_CHECKBOX_SCALE_Y = 1.2
UI_STACK_PADDING = 25
UI_STACK_RIGHT_PADDING = 20
UI_STACK_ALIGNMENT = 0.95

# Cloner chain UI constants
UI_CHAIN_ACTIVE_ICON = "RADIOBUT_ON"
UI_CHAIN_INACTIVE_ICON = "RADIOBUT_OFF"
UI_CHAIN_BOX_PADDING = 5

# Effector panel constants
UI_EFFECTOR_PANEL_CATEGORY = "Cloners"
UI_EFFECTOR_PANEL_REGION = "UI"

# Effector UI constants
UI_EFFECTOR_STRENGTH_DEFAULT = 1.0
UI_EFFECTOR_STRENGTH_MIN = 0.0
UI_EFFECTOR_STRENGTH_MAX = 1.0

# Icons for different components
ICON_CLONER = "MOD_ARRAY"
ICON_EFFECTOR = "FORCE_FORCE"
ICON_FIELD = "LIGHT_AREA"
ICON_SETTINGS = "PREFERENCES"
ICON_ADD = "ADD"
ICON_REMOVE = "REMOVE"
ICON_LINK = "LINKED"
ICON_UNLINK = "UNLINKED"
ICON_REFRESH = "FILE_REFRESH"
ICON_EXPAND = "TRIA_DOWN"
ICON_COLLAPSE = "TRIA_RIGHT"

# Icons for cloner types
ICON_GRID_CLONER = "MESH_GRID"
ICON_LINEAR_CLONER = "SORTSIZE"
ICON_CIRCLE_CLONER = "MESH_CIRCLE"

# Icons for effector types
ICON_NOISE_EFFECTOR = "RNDCURVE"
ICON_RANDOM_EFFECTOR = "MOD_NOISE"

# Field type icons
ICON_SPHERE_FIELD = "SPHERE"

# UI colors (using Blender's theme color system)
COLOR_ACTIVE = (0.2, 0.6, 1.0, 1.0)  # Bright blue
COLOR_WARNING = (1.0, 0.6, 0.0, 1.0)  # Orange
COLOR_ERROR = (1.0, 0.3, 0.3, 1.0)    # Red
COLOR_SUCCESS = (0.3, 0.8, 0.3, 1.0)  # Green 