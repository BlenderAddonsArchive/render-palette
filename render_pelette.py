# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import ctypes
import datetime
import filecmp
import json
import os
import shutil
import threading
import time
import urllib.request
import webbrowser

from bpy.app.handlers import persistent
from bpy_extras.io_utils import ImportHelper
from bpy.props import (CollectionProperty, EnumProperty, FloatVectorProperty,
                       IntProperty, PointerProperty, StringProperty)
from bpy.types import (Menu, Operator, Panel, PropertyGroup, Scene, UIList)

  
bl_info = {
    "name": "Render Palette",
    "author": "Jishnu jithu",
    "version": (1, 9),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Render Palette",
    "description": "Adds a panel for centralized control of render settings",
    "doc_url": "https://github.com/Jishnu-jithu/render-palette/wiki/Render-Palette-Documentation",
    "tracker_url": "https://t.me/Blendyhub",
    "category": "3D View",
}


def is_admin():
    """
    Checks if the current user has administrative privileges.

    This function is used in the context of a LUT installation function,
    where Blender needs to run as an administrator.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Define layout separator
def layout_sep(layout, element_type, *args, **kwargs):
    getattr(layout, element_type)(*args, **kwargs)
    layout.separator()

# Define row with scale
def scaled_row(layout, label_text, data=None, prop=None, operator=None, operator_text=None):
    row = layout.row(align=True)
    row.label(text=label_text)
    row.scale_x = 3
    if operator:
        row.operator(operator, text=operator_text)
    else:
        row.prop(data, prop, text="")
    return row

# Define split row
def split_row(layout, label_text, data=None, prop=None, operator=None, operator_text=None):
    row = layout.row()
    split = row.split(factor=0.3)
    split.label(text=label_text)
    if operator:
        split.operator(operator, text=operator_text)
    else:
        split.prop(data, prop, text="")
    return split


# ----------------------------------------------------------------------------

class RENDER_PT_main_panel(Panel):
    """Main Panel"""
    bl_label = "Render"
    bl_idname = "RENDER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Render Palette"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.scale_y = 2.0
        
        if context.scene.render_palette_autosave_props.enable_autosave:
            row.operator("render.autosave_operator", text="Render Image", icon="RESTRICT_RENDER_OFF")
        else:
            op = row.operator("render.render", text="Render Image", icon="RENDER_STILL")
            op.write_still = False
            
        if context.scene.render_type == 'ANIMATION':
            row = layout.row()
            row.scale_y = 2.0
            op = row.operator("render.render", text="Render Animation", icon="RENDER_ANIMATION")
            op.animation = True

# ----------------------------------------------------------------------------

class RENDER_PT_settings_panel(Panel):
    """Render Settings Panel"""
    bl_label = "Render Settings"
    bl_idname = "RENDER_PT_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Render Palette"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout_sep(layout, 'prop', scene, 'render_type', expand=True)
        
        self.draw_animation_settings(layout, context)
        self.draw_render_settings(layout, context)
        self.draw_camera_settings(layout, context)
    
    def draw_animation_settings(self, layout, context):
        scene = context.scene
        
        if scene.render_type == 'ANIMATION':
            row = layout.row(align=True)
            row.label(text="Frame Start & End:")
            row.scale_x = 1.525
            row.prop(scene, 'frame_start', text='')
            row.prop(scene, 'frame_end', text='')

            layout.separator()

            scaled_row(layout, "Frame Rate:", scene, "framerate_preset")
            layout.separator()
            
            if scene.framerate_preset == 'CUSTOM':
                scaled_row(layout, "Custom:", scene.render, "fps")
                layout.separator()

    def draw_render_settings(self, layout, context):
        scene = context.scene

        layout.prop(scene, 'resolution_preset', text='Resolution')

        if scene.resolution_preset == 'Custom':
            layout.separator()
            row = layout.row(align=True)
            row.label(text="Custom:")
            row.scale_x = 1.525
            row.prop(scene.render, "resolution_x", text="X")
            row.prop(scene.render, "resolution_y", text="Y")

        layout.separator()

        layout_sep(layout, 'prop', scene.render, 'engine', text='Render Engine')

        if scene.render.engine == 'CYCLES':
            layout_sep(layout, 'prop', scene.cycles, "device", text="Device")
            layout_sep(layout, 'prop', scene, 'samples_preset', text='Samples')

            if scene.samples_preset == 'CUSTOM':
                scaled_row(layout, "Custom:", scene.cycles, 'samples')
                layout.separator()
                
        layout_sep(layout, 'prop', scene.view_settings, "view_transform", text="View Transform")
        layout_sep(layout, 'prop', scene.view_settings, "look", text="Contrast")

        layout_sep(layout, 'prop', scene, "render_file_format", text="Format")
        
    def draw_camera_settings(self, layout, context):
        scene = context.scene
        
        if any(obj.type == 'CAMERA' for obj in bpy.context.scene.objects):
            layout.prop(scene, "camera")
        else:
            scaled_row(layout, "Camera:", operator="render.create_camera_to_view", operator_text="New Camera to View")

        layout.separator()
        #layout_sep(layout, 'prop', scene.render, 'filepath', text='Output')
        layout.prop(context.scene.render, 'filepath', text='Output')
        
        if scene.render.engine != 'BLENDER_WORKBENCH':
            layout.separator()
            row = layout.row(align=True)
            row.label(text="Turn On:")
            row.scale_x = 1.53
            
            if scene.camera is not None:
                dof = scene.camera.data.dof
                row.operator("render.toggle_dof", text="Depth of Field", depress=dof.use_dof)
                if scene.render_type == 'IMAGE':
                    row.operator("render.toggle_autosave", text="Autosave", depress=scene.render_palette_autosave_props.enable_autosave)
            else:
                row.enabled = False
                row.operator("render.toggle_dof", text="Depth of Field")
                if scene.render_type == 'IMAGE':
                    row.operator("render.toggle_autosave", text="Autosave") 
                                   
            if scene.render_type == 'ANIMATION':
                if scene.render.engine in {'BLENDER_EEVEE', 'CYCLES'}:
                    props = scene.eevee if scene.render.engine == 'BLENDER_EEVEE' else scene.render
                    row.prop(props, "use_motion_blur", text="Motion Blur", toggle=True)

            if scene.camera is not None and dof.use_dof:
                layout.separator()
                scaled_row(layout, "Focus Object:", dof, 'focus_object')
                layout.separator()
                if dof.focus_object is None:
                    scaled_row(layout, "Focus Distance:", dof, 'focus_distance')

                scaled_row(layout, "F-Stop:", dof, 'aperture_fstop')

# ----------------------------------------------------------------------------

class RENDER_PT_environment_panel(Panel):
    """Environment Panel"""
    bl_label = "Environment Settings"
    bl_idname = "RENDER_PT_environment_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render Palette'
    
    @classmethod
    def poll(cls, context):
        return context.scene.render.engine not in {'BLENDER_WORKBENCH'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.render_palette_exr_props
        
        self.import_exr_files(context)
        
        exr_files = [img.name for img in bpy.data.images if img.filepath.endswith(".exr")]

        if exr_files:
            row = layout.row()
            row.prop(props, "exr_files", text="")
            layout.separator()

        is_environment_applied = self.is_environment_applied(context, exr_files)

        if len(exr_files) > 0 and not is_environment_applied:
            row.operator("render.apply_environment_texture", text="", icon='CHECKMARK')
        if len(exr_files) > 1 and is_environment_applied:
            row.operator("render_palette.next_exr", text="", icon='FILE_REFRESH')
        
        layout.operator("import.world_texture", text="Import World Texture")
        layout.operator("import.world_textures_from_folder", text="Import from Folder")

    def import_exr_files(self, context):
        """Automatically import EXR files from the selected folder."""
        preferences = context.preferences.addons[__name__].preferences
        
        exr_import_location = preferences.exr_import_location
        if os.path.isdir(exr_import_location):
            exr_files_to_load = [os.path.join(exr_import_location, file) for file in os.listdir(exr_import_location) if file.endswith(".exr")]
            
            for exr_file in exr_files_to_load:
                # Get the base name of the file
                exr_file_name = os.path.basename(exr_file)
                # Check if the image is already loaded to avoid duplicates
                if not any(img.name == exr_file_name for img in bpy.data.images):
                    bpy.data.images.load(exr_file)

    def is_environment_applied(self, context, exr_files):
        """Check if an EXR environment is applied."""
        world = context.scene.world

        if world is not None and world.use_nodes:
            env_node = next((node for node in world.node_tree.nodes if node.type == 'TEX_ENVIRONMENT'), None)
            return env_node is not None and env_node.image is not None and env_node.image.name in exr_files

        return False

class RENDER_PT_envset_panel(Panel):
    """Texture Settings"""
    bl_label = "Texture Settings"
    bl_idname = "RENDER_PT_envset_panel"
    bl_parent_id = "RENDER_PT_environment_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render Palette'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.render_palette_exr_props
        world = context.scene.world

        # Check if world and node tree exist
        if world and world.node_tree:
            background_node = world.node_tree.nodes.get("Background")
            
            if background_node and not background_node.inputs[0].is_linked:
                split_row(layout, "Color:", background_node.inputs[0], 'default_value')
                layout.separator()
                    
            split_row(layout, "Strength:", background_node.inputs[1], 'default_value')

            # Find TEX_ENVIRONMENT node
            env_node = next((node for node in world.node_tree.nodes if node.type == 'TEX_ENVIRONMENT'), None)
            
            # Draw Location, Rotation, and Scale if TEX_ENVIRONMENT node exists
            if env_node:
                layout.separator()
                split_row(layout, "Location:", props, "location")
                split_row(layout, "Rotation:", props, "rotation")
                split_row(layout, "Scale:", props, "scale")
            
            # Draw Remove Environment Texture button if TEX_ENVIRONMENT node exists
            if env_node:
                layout.separator()
                split_row(layout, "Environment Texture", operator="render_palette.remove_env_texture", operator_text="Remove")
                
# ------------------------------------

class IMPORT_OT_world_texture(Operator, ImportHelper):
    bl_idname = "import.world_texture"
    bl_label = "Import World Texture"
    bl_description = "Import a single EXR file"

    def execute(self, context):
        world = bpy.context.scene.world
        world.use_nodes = True
        env_node = next((node for node in world.node_tree.nodes if node.type == 'TEX_ENVIRONMENT'), None)

        if not env_node:
            env_node = world.node_tree.nodes.new(type='ShaderNodeTexEnvironment')
            env_node.location = (-300, 300)

        # Load and assign the selected EXR image to the environment texture node
        env_node.image = bpy.data.images.load(self.filepath)
        world.node_tree.links.new(world.node_tree.nodes['Background'].inputs['Color'], env_node.outputs['Color'])

        return {'FINISHED'}

class IMPORT_OT_world_textures_from_folder(Operator, ImportHelper):
    bl_idname = "import.world_textures_from_folder"
    bl_label = "Import World Textures from Folder"
    bl_description = "Import all EXR textures from a folder"

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        folder_path = self.directory
        exr_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".exr")]

        for exr_file in exr_files:
            bpy.data.images.load(exr_file)

        if exr_files:
            world = bpy.context.scene.world
            world.use_nodes = True
            env_node = world.node_tree.nodes.new(type='ShaderNodeTexEnvironment')
            env_node.location = (-300, 300)
            env_node.image = bpy.data.images[os.path.basename(exr_files[0])]
            world.node_tree.links.new(world.node_tree.nodes['Background'].inputs['Color'], env_node.outputs['Color'])

        return {'FINISHED'}
    
# ------------------------------------

def get_exr_files(self, context):
    """Return a list of EXR files for the UI property."""
    return [(img.name, img.name, "") for img in bpy.data.images if img.filepath.endswith(".exr")]

def set_world_texture(self, context):
    """Set up the world texture based on user preferences."""
    props = context.scene.render_palette_exr_props
    world = context.scene.world

    # Create a world if it doesn't exist
    world = context.scene.world or bpy.data.worlds.new("World")
    context.scene.world = world

    # Ensure nodes are enabled
    world.use_nodes = True

    # Find or create necessary nodes
    env_node = next((node for node in world.node_tree.nodes if node.type == 'TEX_ENVIRONMENT'), None)
    mapping_node = next((node for node in world.node_tree.nodes if node.type == 'MAPPING'), None)
    tex_coord_node = next((node for node in world.node_tree.nodes if node.type == 'TEX_COORD'), None)

    if not env_node:
        env_node = world.node_tree.nodes.new(type='ShaderNodeTexEnvironment')
        env_node.location = (-300, 300)

    if not mapping_node:
        mapping_node = world.node_tree.nodes.new(type='ShaderNodeMapping')
        mapping_node.location = (-510, 300)
        mapping_node.vector_type = 'POINT'

    if not tex_coord_node:
        tex_coord_node = world.node_tree.nodes.new(type='ShaderNodeTexCoord')
        tex_coord_node.location = (-710, 300)

    # Set node properties
    env_node.image = bpy.data.images[props.exr_files]
    mapping_node.inputs['Location'].default_value = props.location
    mapping_node.inputs['Rotation'].default_value = props.rotation
    mapping_node.inputs['Scale'].default_value = props.scale

    # Create links if they don't exist
    links = world.node_tree.links
    for output, input in [(env_node.outputs['Color'], world.node_tree.nodes['Background'].inputs['Color']),
                          (mapping_node.outputs['Vector'], env_node.inputs['Vector']),
                          (tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])]:
        if input not in [link.from_socket for link in links]:
            links.new(input, output)

class RENDER_OT_apply_env_texture(Operator):
    """Apply Environment Texture"""
    bl_idname = "render.apply_environment_texture"
    bl_label = "Apply Environment Texture"

    def execute(self, context):
        set_world_texture(self, context)
        return {'FINISHED'}

class RENDER_OT_remove_env_texture(Operator):
    bl_idname = "render_palette.remove_env_texture"
    bl_label = "Remove Environment Texture"
    bl_description = "Remove the environment texture and create a new world texture"
    
    def execute(self, context):
        # Clear existing world texture nodes
        world = context.scene.world
        world.use_nodes = True
        world.node_tree.nodes.clear()
    
        # Create a new world with default settings
        bpy.ops.world.new()
        new_world = context.scene.world
        new_world.use_nodes = True
        
        # Create background node
        background_node = new_world.node_tree.nodes.new(type='ShaderNodeBackground')
        background_node.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
        background_node.location = (0, 300)
        
        # Create world output node
        world_output_node = new_world.node_tree.nodes.new(type='ShaderNodeOutputWorld')
        world_output_node.location = (200, 300)
        
        # Link nodes
        new_world.node_tree.links.new(background_node.outputs["Background"], world_output_node.inputs["Surface"])
        
        self.report({'INFO'}, "Environment texture removed")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Are you sure you want to remove the environment texture?")

class RENDER_OT_next_exr(Operator):
    bl_idname = "render_palette.next_exr"
    bl_label = "Next EXR"
    bl_description = "Switch to the next environment texture"
    
    def execute(self, context):
        props = context.scene.render_palette_exr_props
        exr_files = [img.name for img in bpy.data.images if img.filepath.endswith(".exr")]
        
        if len(exr_files) > 1:
            index = exr_files.index(props.exr_files)
            next_index = (index + 1) % len(exr_files)
            props.exr_files = exr_files[next_index]
        
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_PG_exr_props(PropertyGroup):
    exr_files: EnumProperty(
        name="EXR Files",
        description="List of EXR files in the current Blender file",
        items=get_exr_files,
        update=lambda self, context: set_world_texture(self, context)
    )
    location: FloatVectorProperty(
        name="Location",
        description="Location of the environment texture",
        subtype='TRANSLATION',
        update=lambda self, context: set_world_texture(self, context)
    )
    rotation: FloatVectorProperty(
        name="Rotation",
        description="Rotation of the environment texture",
        subtype='EULER',
        update=lambda self, context: set_world_texture(self, context)
    )
    scale: FloatVectorProperty(
        name="Scale",
        description="Scale of the environment texture",
        subtype='XYZ',
        default=(1.0, 1.0, 1.0),
        update=lambda self, context: set_world_texture(self, context)
    )

# ----------------------------------------------------------------------------

class RENDER_PT_camera_controls(Panel):
    """Camera Settings Panel"""
    bl_label = "Camera Settings"
    bl_idname = "RENDER_PT_camera_controls"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render Palette'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[__name__].preferences
        return prefs.enable_cam_properties
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if scene.camera:
            row = layout.row()
            row.operator("object.camera_orientation", text="Change camera orientation")
            layout.separator()
            
            row = layout.row()
            row.operator("render.align_camera_to_view", text="Align Camera to View")
        else:
            row = layout.row()
            row.enabled = False
            row.operator("object.camera_orientation", text="Change camera orientation")
            layout.separator()
            
            row = layout.row()
            row.enabled = False
            row.operator("render.align_camera_to_view", text="Align Camera to View")
            
        row = layout.row()
        row.operator("render.create_camera_to_view", text="New Camera to View")
    
# ------------------------------------

def is_camera_selected(context):
    return context.scene.camera is not None

def is_lens_camera(context):
    return context.scene.camera.data.type in {'PERSP', 'PANO'}

class RENDER_PT_camera_properties(Panel):
    """Lens Properties Panel"""
    bl_label = "Lens Properties"
    bl_parent_id = "RENDER_PT_camera_controls"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[__name__].preferences
        return prefs.enable_lens_properties and is_camera_selected(context)
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        camera_data = scene.camera.data

        scaled_row(layout, "Type:", camera_data, 'type')
        layout.separator()

        if is_lens_camera(context):
            scaled_row(layout, "Focal Length:", camera_data, 'lens')
        else:
            scaled_row(layout, "Ortho Scale:", camera_data, 'ortho_scale')

        layout.separator()

        scaled_row(layout, "Shift X:", camera_data, 'shift_x')
        scaled_row(layout, "Shift Y:", camera_data, 'shift_y')
    
# ------------------------------------

class RENDER_PT_tracking_constraints(Panel):
    """Tracking Settings Panel"""
    bl_label = "Tracking Settings"
    bl_parent_id = "RENDER_PT_camera_controls"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'INSTANCED', 'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[__name__].preferences
        return prefs.enable_constraints and is_camera_selected(context)
    
    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        
        if scene.camera is not None:
            obj = context.object

            if obj:
                track_to_constraint = obj.constraints.get("Track To")

                if track_to_constraint:
                    layout.prop(track_to_constraint, "mute", text="", emboss=False)
    
    def draw(self, context):
        layout = self.layout

        aoc = context.active_object
        if aoc and aoc.type == 'CAMERA':
            show_add_track_button = 'Track To' not in aoc.constraints

            if show_add_track_button:
                row = layout.row(align=True)
                row.operator("object.constraint_add", text="Add Track To Constraint").type = 'TRACK_TO'

            if "Track To" in aoc.constraints:
                row = layout.row(align=True)
                row.label(text="Target:")
                row.scale_x = 2
                row.prop(aoc.constraints['Track To'], "target", text="")
                layout.separator()

                row = layout.row(align=True)
                row.label(text="Influence:")
                row.scale_x = 2
                row.prop(aoc.constraints['Track To'], "influence", text="")
                layout.separator()

                row = layout.row(align=True)
                row.operator("object.apply_remove_constraint", text="Apply").action = 'APPLY'
                row.operator("object.apply_remove_constraint", text="Remove").action = 'REMOVE'
        else:
            layout.label(text="Select a camera to add tracking constraints")

# ------------------------------------

class RENDER_OT_Camera_Orientation(Operator):
    bl_idname = "object.camera_orientation"
    bl_label = "Camera Orientation"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Change camera orientation"

    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Choose an orientation",
        items=[
            ("SQUARE", "Square", ""),
            ("PORTRAIT", "Portrait", ""),
            ("LANDSCAPE", "Landscape", ""),
        ],
        default='SQUARE',
    )

    def execute(self, context):
        scene = context.scene
        render = scene.render

        if not hasattr(self, 'original_res_x'):
            self.original_res_x = render.resolution_x
            self.original_res_y = render.resolution_y

        if self.orientation == 'SQUARE':
            render.resolution_x = min(self.original_res_x, self.original_res_y)
            render.resolution_y = min(self.original_res_x, self.original_res_y)
        elif self.orientation == 'PORTRAIT':
            render.resolution_x = min(self.original_res_x, self.original_res_y)
            render.resolution_y = max(self.original_res_x, self.original_res_y)
        elif self.orientation == 'LANDSCAPE':
            render.resolution_x = self.original_res_x
            render.resolution_y = self.original_res_y

        return {'FINISHED'}

# ------------------------------------

class OBJECT_OT_apply_remove_constraint(Operator):
    bl_idname = "object.apply_remove_constraint"
    bl_label = "Apply/Remove Constraint"

    action: bpy.props.EnumProperty(
        items=[
            ('APPLY', 'Apply', 'Apply the constraint'),
            ('REMOVE', 'Remove', 'Remove the constraint')
        ],
        default='APPLY'
    )

    def execute(self, context):
        active_obj = context.active_object

        if active_obj and active_obj.type == 'CAMERA':
            track_to_constraint = active_obj.constraints.get('Track To')

            if track_to_constraint:
                if self.action == 'APPLY':
                    bpy.ops.constraint.apply(constraint="Track To", owner='OBJECT')
                elif self.action == 'REMOVE':
                    bpy.ops.constraint.delete(constraint="Track To", owner='OBJECT')

        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_create_camera_to_view(Operator):
    bl_idname = "render.create_camera_to_view"
    bl_label = "Create Camera to View"
    bl_description = "Create a camera to view"
    
    def execute(self, context):
        region = context.region        
        scene = context.scene
        rv3d = context.region_data
        view_matrix = rv3d.view_matrix.inverted()

        cam_data = bpy.data.cameras.new("Camera")
        cam_ob = bpy.data.objects.new("Camera", cam_data)
        cam_data.lens = 35
        scene.collection.objects.link(cam_ob)

        cam_ob.matrix_world = view_matrix

        scene.camera = cam_ob
        bpy.ops.view3d.view_camera()

        return {'FINISHED'}

class RENDER_OT_align_camera_to_view(Operator):
    bl_idname = "render.align_camera_to_view"
    bl_label = "Align Camera to View"
    bl_description = "Align seletced camera to view"
    
    def execute(self, context):
        region = context.region
        rv3d = context.region_data
        scene = context.scene

        camera_objects = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']

        if len(camera_objects) == 1:
            context.view_layer.objects.active = camera_objects[0]
        
        active_camera = context.active_object

        if active_camera and active_camera.type == 'CAMERA':
            view_matrix = rv3d.view_matrix.inverted()

            active_camera.matrix_world = view_matrix
        else:
            self.report({'ERROR'}, "No selected camera or selected object is not a camera")

        return {'FINISHED'}
    
# ----------------------------------------------------------------------------

# define camera list
class RENDER_CAM_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", icon="CAMERA_DATA", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)            

class RENDER_PT_Batch_Render(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Batch Render"
    bl_idname = "OBJECT_PT_multicam"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Render Palette"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[__name__].preferences
        return prefs.enable_batch_render
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout_sep(layout, 'prop', scene, 'location_type', text="Save to")
        layout_sep(layout, 'prop', scene, 'render_option', text="Camera")
        
        row = layout.row(align=True)
        row.scale_x = 0.675
        row.label(text="Overwrite:")
              
        row.prop(scene, 'custom_overwrite', expand=True)
        layout.separator()

        if scene.render_option == 'CUSTOM':  
                     
            row = layout.row()
            rows = 4
            row.template_list("RENDER_CAM_UL_List", "", scene, "batch_render_cameras", scene, "active_camera_index", rows=rows)

            col = row.column(align=True)
            col.operator("render.camera_list_operators", icon='ADD', text="").action = 'ADD'
            col.operator("render.camera_list_operators", icon='REMOVE', text="").action = 'REMOVE'

            col.separator()
            col.separator()
            col.separator()
            col.operator("render.camera_list_operators", icon='TRIA_UP', text="").action = 'MOVE_UP'
            col.operator("render.camera_list_operators", icon='TRIA_DOWN', text="").action = 'MOVE_DOWN'
            layout.separator()
        
        layout.operator("render.render_multicam", text='Batch Render')

# ------------------------------------

class RENDER_OT_Batch_Render(Operator):
    bl_idname = "render.render_multicam"
    bl_description = "Start Batch render"
    bl_label = "Render from multiple cameras"

    def execute(self, context):
        scene = context.scene
        original_cam = scene.camera
        original_filepath = bpy.context.scene.render.filepath

        if scene.render_option == 'ALL_CAMERAS':
            # Render with all cameras in the scene
            cameras_to_render = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
        else:
            cameras_to_render = [bpy.data.objects.get(cam.name) for cam in scene.batch_render_cameras if bpy.data.objects.get(cam.name) is not None]

        total_frames = len(cameras_to_render) * (scene.frame_end - scene.frame_start + 1)
        current_frame = 0

        try:
            bpy.context.window_manager.progress_begin(0, total_frames)

            for i, cam in enumerate(cameras_to_render):
                scene.camera = cam

                if scene.render_type == 'ANIMATION':
                    self._render_animation_frames(scene, original_filepath, cam, total_frames, current_frame)
                else:
                    self._render_single_frame(scene, original_filepath, cam, total_frames, current_frame)

            self.report({'INFO'}, "Rendering completed")

        finally:
            bpy.context.window_manager.progress_end()
            scene.camera = original_cam
            bpy.context.scene.render.filepath = original_filepath

        return {'FINISHED'}

    def _render_animation_frames(self, scene, original_filepath, cam, total_frames, current_frame):
        for frame in range(scene.frame_start, scene.frame_end + 1):
            bpy.context.scene.frame_set(frame)

            bpy.context.scene.render_file_format = 'PNG'

            if scene.location_type == 'SEPARATE_FOLDERS':
                camera_folder = os.path.join(original_filepath, cam.name)
                os.makedirs(camera_folder, exist_ok=True)
                filepath = os.path.join(camera_folder, str(frame).zfill(4))
            else:
                filepath = os.path.join(original_filepath, cam.name + "_" + str(frame).zfill(4))

            filepath = self._get_non_overlapping_filepath(filepath)

            bpy.context.scene.render.filepath = filepath
            bpy.ops.render.render(write_still=True)

            current_frame += 1
            bpy.context.window_manager.progress_update(current_frame)

    def _render_single_frame(self, scene, original_filepath, cam, total_frames, current_frame):
        bpy.context.scene.render_file_format = 'PNG'

        if scene.location_type == 'SEPARATE_FOLDERS':
            camera_folder = os.path.join(original_filepath, cam.name)
            os.makedirs(camera_folder, exist_ok=True)
            filepath = os.path.join(camera_folder, cam.name)
        else:
            filepath = os.path.join(original_filepath, cam.name)

        filepath = self._get_non_overlapping_filepath(filepath)

        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)

        current_frame += 1
        bpy.context.window_manager.progress_update(current_frame)

    def _get_non_overlapping_filepath(self, filepath):
        if not bpy.context.scene.render.use_overwrite and os.path.isfile(filepath + ".png"):
            i = 1
            while os.path.isfile(filepath + "_" + str(i) + ".png"):
                i += 1
            filepath += "_" + str(i)
        return filepath
    
# ------------------------------------

class RENDER_OT_Camera_List(Operator):
    bl_idname = "render.camera_list_operators"
    bl_label = "Camera List Operators"

    action: bpy.props.EnumProperty(
        items=[
            ('ADD', 'Add selected camera to list or all cameras', 'Add selected camera to the list or all cameras'),
            ('REMOVE', 'Remove selected camera from list', 'Remove selected camera from the list'),
            ('MOVE_UP', 'Move selected camera up', 'Move the selected camera up in the list'),
            ('MOVE_DOWN', 'Move selected camera down', 'Move the selected camera down in the list'),
        ],
        default='ADD'
    )

    def execute(self, context):
        scene = context.scene

        if self.action == 'ADD':
            selected_objects = bpy.context.selected_objects

            if selected_objects:
                for obj in selected_objects:
                    if obj.type == 'CAMERA' and obj.name not in [cam.name for cam in scene.batch_render_cameras]:
                        item = scene.batch_render_cameras.add()
                        item.name = obj.name
            else:
                for obj in bpy.data.objects:
                    if obj.type == 'CAMERA' and obj.name not in [cam.name for cam in scene.batch_render_cameras]:
                        item = scene.batch_render_cameras.add()
                        item.name = obj.name

        elif self.action == 'REMOVE':
            idx = scene.active_camera_index

            if scene.batch_render_cameras:
                scene.batch_render_cameras.remove(idx)

        elif self.action == 'MOVE_UP':
            if scene.active_camera_index > 0:
                scene.batch_render_cameras.move(scene.active_camera_index, scene.active_camera_index - 1)
                scene.active_camera_index -= 1

        elif self.action == 'MOVE_DOWN':
            if scene.active_camera_index < len(scene.batch_render_cameras) - 1:
                scene.batch_render_cameras.move(scene.active_camera_index, scene.active_camera_index + 1)
                scene.active_camera_index += 1

        return {'FINISHED'}

# ----------------------------------------------------------------------------

class RENDER_PT_preset_panel(Panel):
    """Preset Panel"""
    bl_label = "Render Preset"
    bl_idname = "RENDER_PT_preset_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Render Palette"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[__name__].preferences
        return prefs.enable_render_preset and bool(prefs.preset_directory)
    
    def draw(self, context):
        layout = self.layout
        
        if context.scene.show_render_preset_panel:
            # UI list
            row = layout.row()
            row.template_list("RENDER_UL_presets", "", context.scene, "render_palette_presets", context.scene, "render_palette_presets_index")

            col = row.column(align=True)
            col.operator("renderpalette.add_preset", icon='ADD', text="")
            col.operator("renderpalette.remove_preset", icon='REMOVE', text="")
    
            col.separator()
            col.menu("RENDER_MT_preset_menu", icon='DOWNARROW_HLT', text="")

            col.separator()
            col.operator("renderpalette.move_preset", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("renderpalette.move_preset", icon='TRIA_DOWN', text="").direction = 'DOWN'
            
            row = layout.row()
            row.operator("renderpalette.apply_preset")
            
        else:
            layout.operator("renderpalette.initialize")

class RENDER_MT_preset_menu(Menu):
    """Preset Menu"""
    bl_label = 'Presets'
    bl_idname = "RENDER_MT_preset_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("renderpalette.refresh_presets", icon='FILE_REFRESH', text="Refresh Preset")
        layout.operator("renderpalette.save_preset", icon='FILE_TICK', text="Save Preset")
        layout.operator("renderpalette.export_preset", icon='EXPORT', text="Export Preset")
        layout.operator("renderpalette.import_preset", icon='IMPORT', text="Import Preset")
        layout.operator("renderpalette.show_preset_info", icon='QUESTION', text="Preset Info").index = context.scene.render_palette_presets_index
        layout.operator("renderpalette.open_preset_directory", icon='FILE_FOLDER', text="Open Preset Folder")
    
# ------------------------------------

class RENDER_OT_initialize(Operator):
    bl_idname = "renderpalette.initialize"
    bl_label = "Initialize"
    bl_description = "Inintialize the render preset)"
    
    def execute(self, context):
        context.scene.show_render_preset_panel = True
        
        bpy.ops.renderpalette.refresh_presets()
        
        return {'FINISHED'}

class RENDER_OT_open_preset_directory(Operator):
    bl_idname = "renderpalette.open_preset_directory"
    bl_label = "Open Preset Folder"
    bl_description = "Open the preset directory in Windows Explorer"
    
    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        preset_directory = addon_prefs.preset_directory

        import subprocess
        subprocess.Popen(f'explorer "{preset_directory}"', shell=True)
        
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_move_preset(Operator):
    bl_idname = "renderpalette.move_preset"
    bl_label = "Move Preset"
    bl_description = "Move selected preset up and down"
    
    direction: bpy.props.EnumProperty(
        items=[('UP', 'Up', ''), ('DOWN', 'Down', '')],
        name="Direction"
    )

    def execute(self, context):
        scene = context.scene
        presets = scene.render_palette_presets
        index = scene.render_palette_presets_index

        if self.direction == 'UP':
            if index > 0:
                presets.move(index, index - 1)
                scene.render_palette_presets_index -= 1
        elif self.direction == 'DOWN':
            if index < len(presets) - 1:
                presets.move(index, index + 1)
                scene.render_palette_presets_index += 1

        return {'FINISHED'}

class RENDER_OT_add_preset(Operator):
    bl_idname = "renderpalette.add_preset"
    bl_label = "Add Preset"
    bl_description = "Add a new preset"

    name: StringProperty(name="Name", default="New Preset")

    def execute(self, context):
        presets = context.scene.render_palette_presets
        preset = presets.add()
        self.update_preset_properties(preset, context.scene)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def update_preset_properties(self, preset, scene):
        scene = context.scene
        
        # Update preset properties based on the current scene
        preset.name = self.name
        preset.resolution_preset = scene.resolution_preset
        
        if scene.resolution_preset == 'Custom':
            preset.custom_resolution_x = scene.custom_resolution_x
            preset.custom_resolution_y = scene.custom_resolution_y
            
        preset.render_engine = scene.render.engine
        preset.device = scene.cycles.device
        
        preset.samples_preset = scene.samples_preset
        preset.custom_samples = scene.cycles.samples
        
        preset.look = scene.view_settings.look
        preset.view_transform = scene.view_settings.view_transform
        
        preset.render_file_format = scene.render_file_format
        preset.output = scene.render.filepath
        
        preset.render_type = scene.render_type
        
        if scene.render_type == 'ANIMATION':
            preset.frame_start = scene.frame_start
            preset.frame_end = scene.frame_end
            preset.framerate_preset = scene.framerate_preset
            
            if scene.framerate_preset == 'CUSTOM':
                preset.fps = scene.render.fps
        
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_remove_preset(Operator):
    bl_idname = "renderpalette.remove_preset"
    bl_label = "Remove Preset"
    bl_description = "Remove the selected preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render_palette_presets
    
    def execute(self, context):
        scene = context.scene
        presets = scene.render_palette_presets
        index = scene.render_palette_presets_index

        if 0 <= index < len(presets):
            # Store the name of the preset to report later
            preset_name = presets[index].name

            presets.remove(index)

            scene.render_palette_presets_index = min(max(0, index - 1), len(presets) - 1)

            self.report({'INFO'}, f"Preset '{preset_name}' removed")
        else:
            first_preset_name = presets[0].name
            presets.remove(0)
            self.report({'INFO'}, f"Preset '{first_preset_name}' removed")

        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_refresh_presets(Operator):
    bl_idname = "renderpalette.refresh_presets"
    bl_label = "Refresh Presets"
    bl_description = "Import all presets from the default Preset location"

    def execute(self, context):
        directory = context.preferences.addons[__name__].preferences.preset_directory
        scene = context.scene
        
        if not os.path.exists(directory):
            self.report({'WARNING'}, "Preset directory does not exist")
            return {'CANCELLED'}

        preset_files = [f for f in os.listdir(directory) if f.endswith('.json')]

        if not preset_files:
            self.report({'WARNING'}, "No presets found in the directory")
            return {'CANCELLED'}

        scene.render_palette_presets.clear()

        for file in preset_files:
            filepath = os.path.join(directory, file)
            with open(filepath, "r") as json_file:
                data = json.load(json_file)

                preset = scene.render_palette_presets.add()
                preset.name = data["name"]
                preset.render_type = data.get("render_type", "IMAGE")
                
                preset.frame_start = data.get("frame_start", 1)
                preset.frame_end = data.get("frame_end", 250)
                preset.framerate_preset = data.get("framerate_preset", "24")
                fps_value = data.get("fps", 24.0)
                if fps_value is not None:
                    preset.fps = float(fps_value)
                else:
                    preset.fps = 24.0
                    
                preset.resolution_preset = data["resolution_preset"]
                preset.render_engine = data["render_engine"]

                if preset.resolution_preset == 'Custom':
                    preset.custom_resolution_x = data.get("custom_resolution_x", 1920)
                    preset.custom_resolution_y = data.get("custom_resolution_y", 1080)

                if data["render_engine"] == 'CYCLES':
                    preset.device = data.get("device", "CPU")
                    preset.samples_preset = data["samples_preset"]
                    preset.custom_samples = data.get("custom_samples", scene.cycles.samples)
                else:
                    preset.device = "CPU"
                    preset.samples_preset = "PRESET"
                    preset.custom_samples = scene.cycles.samples

                preset.look = data["look"]
                preset.view_transform = data.get("view_transform", "Filmic")
                preset.render_file_format = data["render_file_format"]
                preset.output = data.get("output", "")

        self.report({'INFO'}, "Presets reloaded")
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_save_preset(Operator):
    bl_idname = "renderpalette.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the selected preset to default Preset location"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render_palette_presets
    
    def execute(self, context):
        presets = context.scene.render_palette_presets
        scene = context.scene
        rd = context.scene.render

        directory = context.preferences.addons[__name__].preferences.preset_directory

        os.makedirs(directory, exist_ok=True)

        index = scene.render_palette_presets_index
        selected_preset = presets[index]

        filepath = os.path.join(directory, f"{selected_preset.name}.json")

        # Create a dictionary with the preset data
        data = {
            "name": selected_preset.name,
            "render_type": scene.render_type,
            "resolution_preset": scene.resolution_preset,
            "render_engine": scene.render.engine,
            "look": scene.view_settings.look,
            "view_transform": scene.view_settings.view_transform,
            "render_file_format": scene.render_file_format,
            "output": scene.render.filepath,
        }

        if scene.render_type == 'ANIMATION':
            data["frame_start"] = scene.frame_start
            data["frame_end"] = scene.frame_end
            data["framerate_preset"] = scene.framerate_preset
            data["fps"] = scene.render.fps if scene.framerate_preset == 'CUSTOM' else None

        if scene.resolution_preset == 'Custom':
            data["custom_resolution_x"] = rd.resolution_x
            data["custom_resolution_y"] = rd.resolution_y

        if scene.render.engine == 'CYCLES':
            data["device"] = scene.cycles.device
            data["samples_preset"] = scene.samples_preset

            if scene.samples_preset == 'CUSTOM':
                data["custom_samples"] = scene.cycles.samples

        try:
            with open(filepath, "w") as file:
                json.dump(data, file, indent=4)

            self.report({'INFO'}, f"Preset '{selected_preset.name}' saved to {directory}")
        except Exception as e:
            self.report({'ERROR'}, f"Error saving preset: {str(e)}")

        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_export_preset(Operator):
    bl_idname = "renderpalette.export_preset"
    bl_label = "Export Preset"
    bl_description = "Export the selected preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render_palette_presets
    
    filepath: StringProperty(subtype='FILE_PATH')
    
    def execute(self, context):
        scene = context.scene
        presets = scene.render_palette_presets
        index = scene.render_palette_presets_index
        preset = presets[index]
        
        directory = context.preferences.addons[__name__].preferences.preset_directory

        # Create a dictionary with the preset data
        data = {
            "name": preset.name,
            "render_type": scene.render_type,
            "resolution_preset": scene.resolution_preset,
            "render_engine": scene.render.engine,
            "look": scene.view_settings.look,
            "view_transform": scene.view_settings.view_transform,
            "render_file_format": scene.render_file_format,
            "output": scene.render.filepath,
        }
        
        if scene.render_type == 'ANIMATION':
            data["frame_start"] = scene.frame_start
            data["frame_end"] = scene.frame_end
            data["framerate_preset"] = scene.framerate_preset
            data["fps"] = scene.render.fps if scene.framerate_preset == 'CUSTOM' else None
        
        if scene.resolution_preset == 'Custom':
            data["custom_resolution_x"] = scene.render.resolution_x
            data["custom_resolution_y"] = scene.render.resolution_y
        
        if scene.render.engine == 'CYCLES':
            data["samples_preset"] = scene.samples_preset
            data["device"] = scene.cycles.device
            if scene.samples_preset == 'CUSTOM':
                data["custom_samples"] = scene.cycles.samples
        
        try:
            with open(self.filepath, "w") as file:
                json.dump(data, file, indent=4)
            
            self.report({'INFO'}, f"Preset '{preset.name}' exported to {directory}")
        except Exception as e:
            self.report({'ERROR'}, f"Error exporting preset: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        presets = context.scene.render_palette_presets
        index = context.scene.render_palette_presets_index
        preset = presets[index]

        self.filepath = bpy.path.abspath("//") + preset.name + ".json"

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# ------------------------------------

class RENDER_OT_import_preset(Operator):
    bl_idname = "renderpalette.import_preset"
    bl_label = "Import Preset"
    bl_description = "Import a preset"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    data = {
        "render_type": "IMAGE",
        "frame_start": 1,
        "frame_end": 250,
        "framerate_preset": "24",
        "fps": 24,
        "device": "CPU",
        "samples_preset": "PRESET",
        "view_transform": "Filmic",
        "output": "",
        "custom_samples": 128
    }

    def import_single_preset(self, context, file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
        
        scene = context.scene
        rd = context.scene.render

        # Extract the preset data from the dictionary
        name = data.get("name", "Unnamed")

        render_type = data.get("render_type", self.data["render_type"])
        frame_start = data.get("frame_start", self.data["frame_start"])
        frame_end = data.get("frame_end", self.data["frame_end"])
        framerate_preset = data.get("framerate_preset", self.data["framerate_preset"])
        fps = data.get("fps", self.data["fps"])

        resolution_preset = data.get("resolution_preset", "HD")
        render_engine = data.get("render_engine", "BLENDER_EEVEE")
        device = data.get("device", self.data["device"])

        samples_preset = data.get("samples_preset", self.data["samples_preset"])

        look = data.get("look", "None")
        valid_look_options = ['None', 'AgX - Punchy', 'AgX - Greyscale', 'AgX - Very High Contrast', 'AgX - High Contrast', 'AgX - Medium High Contrast', 'AgX - Base Contrast', 'AgX - Medium Low Contrast', 'AgX - Low Contrast', 'AgX - Very Low Contrast']
        if look not in valid_look_options:
            look = 'None'

        view_transform = data.get("view_transform", "Standard")  # Set "Standard" as the default view_transform

        render_file_format = data.get("render_file_format", "PNG")
        output = data.get("output", self.data["output"])

        presets = scene.render_palette_presets
        presets.add()
        new_preset = presets[-1]
        new_preset.name = name

        if new_preset.render_type == 'ANIMATION':
            new_preset.frame_start = frame_start
            new_preset.frame_end = frame_end
            new_preset.framerate_preset = framerate_preset
            if framerate_preset == 'CUSTOM':
                new_preset.fps = fps
        
        if scene.resolution_preset == 'Custom':
            rd.resolution_x = data.get("custom_resolution_x", 1920)
            rd.resolution_y = data.get("custom_resolution_y", 1080)
        
        if scene.render.engine == 'CYCLES':
            scene.cycles.device = device
            scene.samples_preset = samples_preset

            if samples_preset == 'CUSTOM':
                custom_samples = data.get("custom_samples", self.data["custom_samples"])
                scene.cycles.samples = custom_samples

        scene.view_settings.look = look
        scene.view_settings.view_transform = view_transform
        scene.render_file_format = render_file_format
        scene.render.filepath = output

        self.report({'INFO'}, f"Preset '{new_preset.name}' imported")

    def import_multiple_presets(self, context, folder_path):
        preset_files = [os.path.join(folder_path, filename) for filename in os.listdir(folder_path) if filename.endswith(".json")]
        for file_path in preset_files:
            self.import_single_preset(context, file_path)

        self.report({'INFO'}, f"All presets from '{folder_path}' imported")

    def execute(self, context):
        if os.path.isdir(self.filepath):
            self.import_multiple_presets(context, self.filepath)
        else:
            self.import_single_preset(context, self.filepath)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# ------------------------------------

class RENDER_OT_apply_preset(Operator):
    bl_idname = "renderpalette.apply_preset"
    bl_label = "Apply Preset"
    bl_description = "Apply the selected preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render_palette_presets
    
    def execute(self, context):
        index = context.scene.render_palette_presets_index
        scene = context.scene
        preset = context.scene.render_palette_presets[index]
        preset_name = preset.name

        directory = context.preferences.addons[__name__].preferences.preset_directory

        filepath = os.path.join(directory, f"{preset_name}.json")

        # Check if the file exists
        if not os.path.isfile(filepath):
            self.report({'WARNING'}, "Please save the current preset before applying it.")
            return {'CANCELLED'}

        with open(filepath, "r") as file:
            data = json.load(file)

        # Extract the preset data from the dictionary
        name = data["name"]
        render_type = data.get("render_type", "IMAGE")
        frame_start = data.get("frame_start", 1)
        frame_end = data.get("frame_end", 250)
        framerate_preset = data.get("framerate_preset", "24")
        fps = data.get("fps", 24)
        resolution_preset = data["resolution_preset"]
        render_engine = data["render_engine"]
        device = data.get("device", "CPU")
        samples_preset = data.get("samples_preset", "LOW")
        look = data.get("look", "None")
        view_transform = data.get("view_transform", "Filmic")

        # Set default value to 'Standard' if the provided value is not in the enum
        if look not in {'None', 'AgX - Punchy', 'AgX - Greyscale', 'AgX - Very High Contrast', 'AgX - High Contrast',
                        'AgX - Medium High Contrast', 'AgX - Base Contrast', 'AgX - Medium Low Contrast',
                        'AgX - Low Contrast', 'AgX - Very Low Contrast'}:
            bpy.context.scene.view_settings.view_transform = 'Standard'

        # Apply the values
        if scene.render_type == 'ANIMATION':
            scene.frame_start = frame_start
            scene.frame_end = frame_end
            scene.framerate_preset = framerate_preset
            if framerate_preset == 'CUSTOM':
                scene.render.fps = fps

        scene.resolution_preset = resolution_preset
        scene.render.engine = render_engine

        if resolution_preset == 'Custom':
            rd = scene.render
            rd.resolution_x = data.get("custom_resolution_x", 1920)
            rd.resolution_y = data.get("custom_resolution_y", 1080)

        if render_engine == 'CYCLES':
            scene.cycles.device = device
            scene.samples_preset = samples_preset

            if samples_preset == 'CUSTOM':
                custom_samples = data.get("custom_samples", 64)
                scene.cycles.samples = custom_samples

        scene.view_settings.look = look
        scene.view_settings.view_transform = view_transform

        self.report({'INFO'}, f"'{preset.name}' Preset applied")
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_show_preset_info(Operator):
    bl_idname = "renderpalette.show_preset_info"
    bl_label = "Preset Info"
    bl_description = "Displays information about the selected render preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render_palette_presets
    
    index: bpy.props.IntProperty()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        preset = context.scene.render_palette_presets[self.index]

        layout.label(text=f"Name: {preset.name}")

        layout.label(text=f"Render Type: {preset.render_type}")

        if preset.render_type == 'ANIMATION':
            layout.label(text=f"Frame Start: {preset.frame_start}")
            layout.label(text=f"Frame End: {preset.frame_end}")
            layout.label(text=f"FPS Preset: {preset.framerate_preset}")
            if preset.framerate_preset == 'CUSTOM':
                layout.label(text=f"Custom FPS: {preset.fps}")

        layout.label(text=f"Resolution Preset: {preset.resolution_preset}")

        if preset.resolution_preset == 'Custom':
            layout.label(text=f"Custom Resolution: {preset.custom_resolution_x}x{preset.custom_resolution_y}")

        layout.label(text=f"Render Engine: {preset.render_engine}")

        if preset.render_engine == 'CYCLES':
            layout.label(text=f"Device: {preset.device}")
            layout.label(text=f"Samples Preset: {preset.samples_preset}")
            if preset.samples_preset == 'CUSTOM':
                layout.label(text=f"Custom Samples: {preset.custom_samples}")

        layout.label(text=f"Contrast: {preset.look}")
        layout.label(text=f"View Transform: {preset.view_transform}")
        layout.label(text=f"Render File Format: {preset.render_file_format}")
        layout.label(text=f"Output: {preset.output}")
    
# ------------------------------------

# Preset Property Group
class RENDER_PG_preset(PropertyGroup):
    name: StringProperty(name="Name", default="New Preset")
    render_type: StringProperty(name="Render Type", default="IMAGE")
    frame_start: bpy.props.IntProperty(name="Frame Start", default=1)
    frame_end: bpy.props.IntProperty(name="Frame End", default=250)
    framerate_preset: StringProperty(name="FPS Preset", default="24")
    fps: bpy.props.FloatProperty(name="Custom FPS", default=24.0)
    resolution_preset: StringProperty(name="Resolution Preset", default="")
    custom_resolution_x: bpy.props.IntProperty(name="Custom Resolution X")
    custom_resolution_y: bpy.props.IntProperty(name="Custom Resolution Y")
    render_engine: StringProperty(name="Render Engine", default="")
    device: StringProperty(name="Device", default="")
    samples_preset: StringProperty(name="Samples Preset", default="")
    custom_samples: bpy.props.IntProperty(name="Custom Samples")
    look: StringProperty(name="Look", default="")
    view_transform: StringProperty(name="View Transform", default="")
    render_file_format: StringProperty(name="Render File Format", default="")
    output: bpy.props.StringProperty(name="Output")
    
# ------------------------------------

# Preset UI List
class RENDER_UL_presets(UIList):    
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, index):
        
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)

# ----------------------------------------------------------------------------

class RENDER_OT_lut_apply(Operator):
    bl_idname = "object.apply_luts"
    bl_label = "Apply LUTs"

    def execute(self, context):
        # Directory containing the LUT files
        lut_dir = bpy.context.scene.lut_tool.lut_dir

        # Get the paths
        blender_dir = bpy.utils.resource_path('LOCAL')
        luts_dir = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'luts')
        config_file = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'config.ocio')
        backup_luts_dir = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'backup')

        backup_config_dir = os.path.dirname(config_file)

        # Create the backup directories
        try:
            os.makedirs(backup_luts_dir, exist_ok=True)
            os.makedirs(backup_config_dir, exist_ok=True)
        except PermissionError:
            if "WindowsApps" in blender_dir:
                self.report({'ERROR'}, "Permission denied when trying to create backup directories. Blender installed from the Microsoft Store may have restricted permissions. Please install Blender from the official website and try again.")
            else:
                self.report({'ERROR'}, "Permission denied when trying to create backup directories. Please run Blender as an administrator or choose a different backup location.")
            return {'CANCELLED'}

        # Backup the config.ocio file if it exists
        if os.path.exists(config_file):
            shutil.copy(config_file, os.path.join(backup_config_dir, 'config.ocio.backup'))
            self.report({'INFO'}, f"Backup of config.ocio created in {backup_config_dir}")
        else:
            # Create an empty config.ocio.backup file if it doesn't exist
            open(os.path.join(backup_config_dir, 'config.ocio.backup'), 'w').close()
            self.report({'INFO'}, f"Backup of config.ocio created in {backup_config_dir}")

        # Read all the LUT files, converting the extensions to lowercase
        lut_files = [f for f in os.listdir(lut_dir) if f.lower().endswith(('.cube'))]
        if not lut_files:
            self.report({'ERROR'}, f"No LUT files found in {lut_dir}. Please add LUT files and try again.")
            return {'CANCELLED'}

        with open(config_file, 'a') as f:
            
            for lut in os.listdir(luts_dir):
                shutil.copy(os.path.join(luts_dir, lut), os.path.join(backup_luts_dir, lut))
            self.report({'INFO'}, f"Backup of LUTs created in {backup_luts_dir}")
            
            for lut in lut_files:
                # Copy the LUT file to the luts directory
                shutil.copy(os.path.join(lut_dir, lut), os.path.join(luts_dir, lut))
                
                # Write the LUT to the config.ocio file
                f.write(f"""
  
  - !<Look>
    name: {os.path.splitext(lut)[0].replace('_', ' ').title()}
    process_space: sRGB
    transform: !<FileTransform> {{src: {lut}, interpolation: tetrahedral}}
""")
        self.report({'INFO'}, f"Applied {len(lut_files)} LUTs from {lut_dir}. Please restart Blender for the changes to take effect.")
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_lut_restore(Operator):
    bl_idname = "object.restore_backup"
    bl_label = "Restore Backup"

    def execute(self, context):
        # Get the paths
        blender_dir = bpy.utils.resource_path('LOCAL')
        luts_dir = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'luts')
        config_file = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'config.ocio')
        backup_luts_dir = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'backup')

        # Backup directory for config.ocio
        backup_config_dir = os.path.dirname(config_file)

        # Remove the current LUT files
        for lut in os.listdir(luts_dir):
            if os.path.isfile(os.path.join(luts_dir, lut)):
                try:
                    os.remove(os.path.join(luts_dir, lut))                
                except PermissionError:
                    if "WindowsApps" in blender_dir:
                        self.report({'ERROR'}, "Permission denied. Blender installed from the Microsoft Store may have restricted permissions. Please install Blender from the official website and try again.")
                    else:
                        self.report({'ERROR'}, "Permission denied. Please run Blender as an administrator and try again.")
                    return {'CANCELLED'}

        # Restore the LUT files from the backup
        for lut in os.listdir(backup_luts_dir):
            shutil.copy(os.path.join(backup_luts_dir, lut), os.path.join(luts_dir, lut))

        # Restore the config.ocio file from the backup
        config_backup_file = os.path.join(backup_config_dir, 'config.ocio.backup')
        if os.path.isfile(config_backup_file):
            shutil.copy(config_backup_file, config_file)

        self.report({'INFO'}, "Backup restoration complete. Please restart Blender for the changes to take effect.")
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_PT_lut_properties(PropertyGroup):
    
    # Define default directories
    home = os.path.expanduser("~")
    downloads_dir = os.path.join(home, "Downloads")

    lut_dir: bpy.props.StringProperty(
        name="LUT Directory",
        subtype='DIR_PATH',
        default=downloads_dir
    )
    
    blender_dir = bpy.utils.resource_path('LOCAL')
    
    luts_dir: bpy.props.StringProperty(
        name="Blender LUTs Directory",
        subtype='DIR_PATH',
        default=os.path.join(blender_dir, 'datafiles', 'colormanagement', 'luts')
    )
    
# ------------------------------------
    
class RENDER_OT_lut_info(bpy.types.Operator):
    bl_idname = "render_palette.lut_info"
    bl_label = "Lut Installation"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = bpy.context.window_manager

        # Show the instructions in the popup
        wm.invoke_props_dialog(self, width=300)

        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout

        # Display instructions in the panel
        layout.label(text="1. First create a folder for .cube LUTs")
        layout.label(text="2. Run Blender as an administrator.")
        layout.label(text="3. Set a location for the .cube LUT files.")
        layout.label(text="4. Click 'Install LUTs' to install and create a backup.")
        layout.label(text="5. Restart Blender to see the changes.")
        layout.label(text="6. Go to Render Properties > Color Management")
        layout.label(text="7. Choose 'Standard' or 'Filmic' in View Transform.")
        layout.label(text="LUTs will appear in the Look dropdown menu.")

# ----------------------------------------------------------------------------

class RENDER_OT_autosave(Operator):
    """Autosave Operator"""
    bl_idname = "render.autosave_operator"
    bl_label = "Render and Save Image"

    render_counter = 1
    render_timer = None
    progress_value = 0.0

    is_rendering: bpy.props.BoolProperty(default=False)

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self.is_rendering:
                self.report({'INFO'}, "Rendering completed or canceled.")
                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        self.is_rendering = True
        if not hasattr(self.__class__, 'original_output_path'):
            self.__class__.original_output_path = bpy.context.scene.render.filepath
            
        AutosaveOperator = RENDER_OT_autosave

        output_path = self.__class__.original_output_path
        
        bpy.context.scene.render_file_format = 'PNG'

        if bpy.data.is_saved:
            base_name = bpy.path.basename(bpy.context.blend_data.filepath)
            project_name = os.path.splitext(base_name)[0]
        else:
            project_name = "Render"

        if os.path.isdir(bpy.path.abspath(output_path)):
            directory = output_path
        else:
            directory = os.path.dirname(output_path)

        filename = f"{project_name}_{AutosaveOperator.render_counter}.png"
        output_path = os.path.join(directory, filename)

        abs_output_path = bpy.path.abspath(output_path)

        while os.path.isfile(abs_output_path):
            AutosaveOperator.render_counter += 1
            filename = f"{project_name}_{AutosaveOperator.render_counter}.png"
            output_path = os.path.join(directory, filename)
            abs_output_path = bpy.path.abspath(output_path)

        bpy.context.scene.render.filepath = output_path

        bpy.ops.render.render("INVOKE_DEFAULT", animation=False, write_still=True)

        self.render_timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self.render_timer:
            context.window_manager.event_timer_remove(self.render_timer)

        self.progress_value = 0.0

class RENDER_OT_toggle_autosave(Operator):
    bl_idname = "render.toggle_autosave"
    bl_label = "Toggle Autosave"
    bl_description = "Enable autosave for rendered image"

    def execute(self, context):
        scene = context.scene
        scene.render_palette_autosave_props.enable_autosave = not scene.render_palette_autosave_props.enable_autosave
        return {'FINISHED'}

class RENDER_PG_autosave_props(PropertyGroup):
    enable_autosave: bpy.props.BoolProperty(name="Enable Autosave", default=False)

# ----------------------------------------------------------------------------

class RENDER_OT_toggle_dof(Operator):
    bl_idname = "render.toggle_dof"
    bl_label = "Toggle Depth of Field"
    bl_description = "Toggles depth of field on and off for the active camera"

    def execute(self, context):
        scene = context.scene
        if scene.camera is not None:
            dof = scene.camera.data.dof
            dof.use_dof = not dof.use_dof
        return {'FINISHED'}

# define overwrite function(batch render)
def custom_overwrite_update(self, context):
    scene = context.scene
    if scene.custom_overwrite == 'ON':
        scene.render.use_overwrite = True
    else:
        scene.render.use_overwrite = False

# define file format presets
def update_file_format(self, context):
    bpy.context.scene.render.image_settings.file_format = context.scene.file_format
    
    rd = context.scene.render
    if self.render_file_format == 'MP4':
        rd.image_settings.file_format = 'FFMPEG'
        rd.ffmpeg.format = 'MPEG4'
        rd.ffmpeg.codec = 'H264'
        rd.ffmpeg.constant_rate_factor = 'HIGH'
    else:
        rd.image_settings.file_format = self.render_file_format

Scene.render_file_format = EnumProperty(
    name="File Format",
    description="Choose the desired file format for rendering",
    items=[
        ('PNG', 'PNG', 'PNG image format'),
        ('JPEG', 'JPEG', 'JPEG image format'),
        ('BMP', 'BMP', 'BMP image format'),
        ('TIFF', 'TIFF', 'TIFF image format'),
        ('TARGA', 'TARGA', 'TARGA image format'),
        ('OPEN_EXR', 'OpenEXR', 'OpenEXR image format'),
        ('MP4', 'MP4', 'MP4 video format'),
    ],
    default='PNG',
    update=update_file_format
)


# define resolution presetss
def update_resolution(self, context):
    resolution_presets = {
        '720p': (1280, 720),
        '1080p': (1920, 1080),
        '1440p': (2560, 1440),
        '4K': (3840, 2160),
        '8K': (7680, 4320),
    }
    if context.scene.resolution_preset == 'Custom':
        resolution = (context.scene.custom_resolution_x, context.scene.custom_resolution_y)
    else:
        resolution = resolution_presets[context.scene.resolution_preset]
    context.scene.render.resolution_x = resolution[0]
    context.scene.render.resolution_y = resolution[1]

# define samples presets
def get_samples_items(self, context):
    items = [
        ('LOW', 'Low (64)', 'Low quality samples'),
        ('MEDIUM', 'Medium (128)', 'Medium quality samples'),
        ('HIGH', 'High (256)', 'High quality samples'),
        ('CUSTOM', 'Custom Sample', 'Custom render samples'),
    ]

    # Add the 'Current' option with the current value
    current_samples = context.scene.cycles.samples
    items.insert(0, ('CURRENT', f'Current ({current_samples})', f'Current render samples ({current_samples})'))

    return items

def update_samples(self, context):
    samples_presets = {
        'LOW': 64,
        'MEDIUM': 128,
        'HIGH': 256,
    }
    
    if self.samples_preset != 'CUSTOM':
        context.scene.cycles.samples = samples_presets.get(self.samples_preset)

# define framerate presets
def update_fps(self, context):
    fps_mapping = {
        '23.98': (24, 1.001),
        '24': (24, 1.0),
        '25': (25, 1.0),
        '29.97': (30, 1.001),
        '30': (30, 1.0),
        '50': (50, 1.0),
        '59.94': (60, 1.001),
        '60': (60, 1.0),
        '120': (120, 1.0),
        '240': (240, 1.0),
        'CUSTOM': (context.scene.custom_fps, 1.0)
    }

    fps, fps_base = fps_mapping.get(self.framerate_preset, (24, 1.0))
    
    context.scene.render.fps = fps
    context.scene.render.fps_base = fps_base

# ---------------------------------------------------------------------------- #


def open_update_page():
    webbrowser.open("https://www.blendermarket.com/account/orders")

# Open Blendermarket page
class RENDER_OT_open_update_page(Operator):
    bl_idname = "render_palette.open_update_page"
    bl_label = "Open Update Page"
    bl_description = "Open the webpage to download the update"
    
    def execute(self, context):
        open_update_page()
        return {'FINISHED'}

# -------------------------------
    
# check for updates
class RENDER_OT_check_for_updates(Operator):
    bl_idname = "render_palette.check_for_updates"
    bl_label = "Check for updates"
    bl_description = "Checks for available updates for the Render Palette addon."

    def execute(self, context):
        message = context.preferences.addons[__name__].preferences.check_for_updates()
        return {'FINISHED'}

# -------------------------------
 
# automatic update check
@persistent
def show_update_popup(dummy):
    prefs = bpy.context.preferences.addons[__name__].preferences
    prefs.check_for_updates()
    if prefs.update_check_status == "New Update Available":
        bpy.ops.render_palette.show_update_popup('INVOKE_DEFAULT')

def delayed_popup():
    time.sleep(1)
    show_update_popup(None)

t1 = threading.Thread(target=delayed_popup)

t1.start()

class RENDER_OT_show_update_popup(bpy.types.Operator):
    bl_idname = "render_palette.show_update_popup"
    bl_label = "Update Render Palette Addon"
    #bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        open_update_page()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        prefs = bpy.context.preferences.addons[__name__].preferences
        col = layout.column()
        col.label(text=f"Update {prefs.latest_version_number} ready!", icon="LOOP_FORWARDS",)
        col.label(text="Press OK to install, What's New to see updates,", icon="BLANK1")
        col.label(text="or click outside window to cancel", icon="BLANK1")
        col.operator("wm.url_open", text="What's New").url = "https://github.com/Jishnu-jithu/render-palette/wiki/Changelog"

# automatic backup restore 
def auto_restore_paths(dummy):
    prefs = bpy.context.preferences.addons[__name__].preferences
    
    documents_dir = os.path.expanduser("~\Documents\Render palette")
    backup_file_path = os.path.join(documents_dir, "backup.json")
    if os.path.exists(backup_file_path) and not prefs.settings_restored:
        # Call the restore function
        bpy.ops.render.restore_paths()

# ---------------------------------------------------------------------------- #


def draw_enable_panel_settings(layout, preferences, context):
    """Draw the enable or disable preferences section"""
    
    box = layout.box()
    row = box.row()

    icon = 'TRIA_DOWN' if context.scene.expand_prop else 'TRIA_RIGHT'
    row.prop(context.scene, "expand_prop", icon=icon, text="", emboss=False)
    row.label(text="Enable or disable Panels")

    if context.scene.expand_prop:
        sub_box = box.box()

        row = sub_box.row()
        row.label(text="Enable Batch Render panel:", icon="RENDERLAYERS")
        row.prop(preferences, "enable_batch_render", text="")

        row = sub_box.row()
        row.label(text="Enable Camera Settings panel:", icon="OUTLINER_OB_CAMERA")
        row.prop(preferences, "enable_cam_properties", text="")
        
        if preferences.enable_cam_properties:
            row = sub_box.row()
            row.label(text="Enable Lens Properties panel:", icon="PIVOT_BOUNDBOX")
            row.prop(preferences, "enable_lens_properties", text="")

            row = sub_box.row()
            row.label(text="Enable Tracking Settings panel:", icon="CON_TRACKTO")
            row.prop(preferences, "enable_constraints", text="")

        row = sub_box.row()
        row.label(text="Enable Render Preset panel:", icon="COLOR")
        row.prop(preferences, "enable_render_preset", text="")

# ----------------------------------------------------------------------------

class RENDER_OT_lut_warning(bpy.types.Operator):
    bl_idname = "render_palette.lut_warning"
    bl_label = "Lut Warning"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = bpy.context.window_manager

        # Show the instructions in the popup
        wm.invoke_props_dialog(self, width=500)

        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.label(text="To install more LUTs,")
        layout.label(text="you need to first remove the currently installed LUTs and try reinstall after removing")

def draw_luts_properties(layout, preferences, context):
    """Draw the luts preferences section"""
    
    scene = context.scene
    box = layout.box()
    col = box.column()
    row = col.row()
    sub = row.row()
    icon = 'TRIA_DOWN' if scene.expand_luts else 'TRIA_RIGHT'
    sub.prop(scene, "expand_luts", icon=icon, text="", emboss=False)
    sub.label(text="Color Management")
    
    # Get Blender directory
    blender_dir = bpy.utils.resource_path('LOCAL')
    path_blender_dir = os.path.dirname(bpy.utils.resource_path('LOCAL'))

    # Restore/Reset button
    config_file = os.path.join(blender_dir, 'datafiles', 'colormanagement', 'config.ocio')
    config_backup_file = config_file + '.backup'
    
    # Check if both files exist before comparing
    if os.path.exists(config_file) and os.path.isfile(config_backup_file):
        backup_same = filecmp.cmp(config_file, config_backup_file)
    else:
        backup_same = True

    # Check if both files exist before comparing
    if os.path.exists(config_file) and os.path.isfile(config_backup_file):
        backup_different = not filecmp.cmp(config_file, config_backup_file)
    else:
        backup_different = False
    
    if backup_same:
        sub = row.row()
        sub.alignment = 'RIGHT'
        sub.operator("render_palette.lut_info", text="", icon="QUESTION", emboss=False)
    elif backup_different:
        sub = row.row()
        sub.alignment = 'RIGHT'
        sub.operator("render_palette.lut_warning", text="", icon="QUESTION", emboss=False)

    if scene.expand_luts:        
        lut_tool = scene.lut_tool

        if not is_admin():
            row = box.row(align=True)
            row.label(text="To use this function, run Blender as administrator.", icon="FAKE_USER_ON")

            # Add a button to open the Blender directory
            row = box.row()
            row.operator("wm.path_open", text="Open Blender Directory", icon="FOLDER_REDIRECT").filepath = path_blender_dir
            return
        
        row = box.row()
        row.prop(lut_tool, "lut_dir", text="Lut Directory")
        row = box.row()
        row.enabled=False
        row.prop(lut_tool, "luts_dir", text="LUT Install directory")
        
        split = box.split()
        split = box.split(align=True)
        
        if lut_tool.lut_dir:            
            if backup_different:
                col = split.column(align=True)
                col.enabled=False
                col.operator("object.apply_luts", text="Install LUTs")
            elif backup_same:
                col = split.column(align=True)
                col.operator("object.apply_luts", text="Install LUTs")

        if backup_different:
            col = split.column(align=True)
            col.operator("object.restore_backup", text="Remove LUTs")

# ----------------------------------------------------------------------------

def draw_backup_restore(layout, preferences, context):
    """Draw the backup and restore preferences section."""
    
    box = layout.box()
    col = box.column()
    row = col.row()
    sub = row.row()
    icon = 'TRIA_DOWN' if bpy.context.scene.expand_backup else 'TRIA_RIGHT'
    sub.prop(bpy.context.scene, "expand_backup", icon=icon, text="", emboss=False)
    sub.label(text="Backup & Restore")

    backup_file_path = os.path.join(os.path.expanduser("~\Documents\Render palette"), "backup.json")

    # Display checkmark if backup file exists and settings are restored
    if os.path.exists(backup_file_path):
        if preferences.settings_restored:
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text="", icon="CHECKMARK")

    if bpy.context.scene.expand_backup:
        row = box.row(align=True)
        # Display backup and restore buttons
        row.operator("render.backup_paths", text="Backup Settings", icon="FILE_CACHE")

        if os.path.exists(backup_file_path):
            restore_text = "Settings Restored" if preferences.settings_restored else "Restore Settings"
            row.operator("render.restore_paths", text=restore_text, icon="CHECKMARK" if preferences.settings_restored else "LOOP_BACK")
        else:
            row.operator("render.restore_paths", text="Restore Settings")

# ----------------------------------------------------------------------------

def draw_check_updates(layout, preferences, context):
    """Draw the check for updates preferences section."""
    
    box = layout.box()
    row = box.row()
    icon = 'TRIA_DOWN' if bpy.context.scene.expand_update else 'TRIA_RIGHT'
    row.prop(bpy.context.scene, "expand_update", icon=icon, text="", emboss=False)
    row.label(text="Check for Updates")

    # Display appropriate icons based on update status
    icon_status = {
        "Add-on is Up to Date": "CHECKMARK",
        "New Update Available": "IMPORT",
    }

    status = preferences.update_check_status
    if not bpy.context.scene.expand_update:
        if status in icon_status:
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text="", icon=icon_status[status])

    if bpy.context.scene.expand_update:
        row = box.row()
                
        # Add a checkbox for enabling/disabling auto-check for updates
        row.prop(preferences, "auto_check_for_updates", text="Auto Check for Updates")
        
        row = box.row()
        col = row.column()
        sub_col = col.row(align=False)
        split = sub_col.split(align=False)
        split.scale_y = 2
        
        # Display buttons based on update status
        if status == "Checking...":
            split.enabled = False
            split.operator("render_palette.check_for_updates", text="Checking...")
            
        elif status == "New Update Available":
            split.operator("render_palette.open_update_page", text="Update Now", icon="FILE_PARENT")
            
            split = sub_col.split(align=False)
            split.scale_y = 2
            split.enabled = False
            split.operator("render_palette.check_for_updates", text="Check Now for updates")
            
        elif status == "Add-on is Up to Date":
            split.enabled = False
            split.operator("render_palette.check_for_updates", text="Add-on is Up to Date")
            
            split = sub_col.split(align=False)
            split.scale_y = 2
            split.operator("render_palette.check_for_updates", text="Check Now for updates")
            
        elif status == "No Internet Connection":
            split.enabled = False
            split.operator("render_palette.check_for_updates", text="URL error, check internet connection")
            
            split = sub_col.split(align=False)
            split.scale_y = 2
            split.operator("render_palette.check_for_updates", text="Check Now for updates")
            
        else:
            split.scale_y = 2
            split.operator("render_palette.check_for_updates", text="Check Now for updates")

        # Display last update check time
        if preferences.last_update_check:
            row = box.row()
            row.label(text="Last Update Check: " + preferences.last_update_check)
        else:
            row = box.row()
            row.label(text="Last Update Check: Never")

# ---------------------------------------------------------------------------- #

backup_data = {}

class RENDER_OT_backup_paths(Operator):
    bl_idname = "render.backup_paths"
    bl_label = "Backup Paths"
    bl_description = "Backup the current paths and settings to a backup file"

    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        backup_data = {
            "exr_location": preferences.exr_import_location,
            "preset_location": preferences.preset_directory,
            "enable_showhide_panel": preferences.enable_showhide_panel,
            "enable_cam_properties": preferences.enable_cam_properties,
            "enable_lens_properties": preferences.enable_lens_properties,
            "enable_constraints": preferences.enable_constraints,
            "enable_batch_render": preferences.enable_batch_render,
            "enable_render_preset": preferences.enable_render_preset
        }

        documents_dir = os.path.expanduser("~\Documents\Render palette")
        os.makedirs(documents_dir, exist_ok=True)
        backup_file = os.path.join(documents_dir, "backup.json")

        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=4)

        self.report({'INFO'}, f"Paths and settings backed up successfully to: {backup_file}")
        return {'FINISHED'}
    
# ------------------------------------

class RENDER_OT_restore_paths(Operator):
    bl_idname = "render.restore_paths"
    bl_label = "Restore Paths"
    bl_description = "Restore the paths and settings from a backup file"

    def execute(self, context):
        documents_dir = os.path.expanduser("~\Documents\Render palette")
        backup_file = os.path.join(documents_dir, "backup.json")

        if os.path.exists(backup_file):
            with open(backup_file, "r") as f:
                backup_data = json.load(f)

                preferences = context.preferences.addons[__name__].preferences
                if "exr_location" in backup_data:
                    preferences.exr_import_location = backup_data["exr_location"]
                if "preset_location" in backup_data:
                    preferences.preset_directory = backup_data["preset_location"]

                # Restore the boolean settings
                if "enable_showhide_panel" in backup_data:
                    preferences.enable_showhide_panel = backup_data["enable_showhide_panel"]
                if "enable_cam_properties" in backup_data:
                    preferences.enable_cam_properties = backup_data["enable_cam_properties"]
                if "enable_lens_properties" in backup_data:
                    preferences.enable_lens_properties = backup_data["enable_lens_properties"]
                if "enable_constraints" in backup_data:
                    preferences.enable_constraints = backup_data["enable_constraints"]
                if "enable_batch_render" in backup_data:
                    preferences.enable_batch_render = backup_data["enable_batch_render"]
                if "enable_render_preset" in backup_data:
                    preferences.enable_render_preset = backup_data["enable_render_preset"]                

            self.report({'INFO'}, f"Paths and settings restored successfully from: {backup_file}")
        else:
            self.report({'ERROR'}, f"Backup file not found at: {backup_file}")
        
        context.preferences.addons[__name__].preferences.settings_restored = True

        return {'FINISHED'}

# ---------------------------------------------------------------------------- #

class RENDERPALATTE_Preferences(bpy.types.AddonPreferences):
    """Preferences for the RENDERPALETTE add-on."""

    bl_idname = __name__

    # Define default directories
    home = os.path.expanduser("~")
    downloads_dir = os.path.join(home, "Downloads")

    # Property to track whether settings have been restored
    settings_restored: bpy.props.BoolProperty(default=False)

    # Properties related to update checking
    last_update_check: bpy.props.StringProperty(name="Last Update Check")
    update_check_status: bpy.props.StringProperty(default="")
    latest_version_number: bpy.props.StringProperty(default="")

    # Directory for automatically importing EXR files
    exr_import_location: bpy.props.StringProperty(
        name="EXR Import Location",
        description="Set the location from which to automatically import EXR files",
        subtype='DIR_PATH',
        default=downloads_dir,
    )

    # Directory for saving and importing presets
    preset_directory: bpy.props.StringProperty(
        name="Preset Directory",
        description="Set the directory where presets are saved and imported from",
        subtype='DIR_PATH',
        default="",
    )

    # Toggle options for various panels
    enable_batch_render: bpy.props.BoolProperty(
        name="Enable Batch Render panel",
        description="Enable or disable the batch render panel",
        default=True,
    )

    enable_cam_properties: bpy.props.BoolProperty(
        name="Enable Camera Settings panel",
        description="Enable or disable the camera settings panel",
        default=True,
    )

    enable_lens_properties: bpy.props.BoolProperty(
        name="Enable Lens Properties panel",
        description="Enable or disable the lens properties panel",
        default=True,
    )

    enable_constraints: bpy.props.BoolProperty(
        name="Enable Tracking Settings panel",
        description="Enable or disable the tracking settings panel",
        default=True,
    )

    enable_render_preset: bpy.props.BoolProperty(
        name="Enable Render Preset panel",
        description="Enable or disable the render preset panel",
        default=True,
    )
    
    auto_check_for_updates: bpy.props.BoolProperty(
        name="Auto Check for Updates",
        description="Automatically check for updates on startup",
        default=True
    )
    
    bpy.types.Scene.interval_days = bpy.props.IntProperty(
        name="Interval Days", 
        default=1, 
        min=0, 
        max=31
    )
    
    bpy.types.Scene.interval_weeks = bpy.props.IntProperty(
        name="Interval Weeks", 
        default=1, 
        min=0, 
        max=4
    )
    
    def check_for_updates(self):
        self.update_check_status = "Checking..."
        
        try:
            url = "https://raw.githubusercontent.com/Jishnu-jithu/render-palette/main/latest_version.txt"
            response = urllib.request.urlopen(url)
            self.latest_version_number = response.read().decode('utf-8').strip()
        except urllib.error.URLError:
            self.update_check_status = "No Internet Connection"
            return
        
        now = datetime.datetime.now()
        self.last_update_check = now.strftime("%Y-%m-%d %H:%M:%S")

        # Compare with current version
        current_version = '.'.join(map(str, bl_info["version"]))
        if self.latest_version_number > current_version:
            self.update_check_status = "New Update Available"
        else:
            self.update_check_status = "Add-on is Up to Date"
                
    def draw(self, context):
        layout = self.layout
        
        blender_dir = bpy.utils.resource_path('LOCAL')
        documents_dir = os.path.expanduser("~\Documents\Render palette")
        backup_file_path = os.path.join(documents_dir, "backup.json")
        
        box = layout.box()
        box.label(text="Paths:")
        box.prop(self, "exr_import_location", text="EXR Location")
        box.prop(self, "preset_directory", text="Preset Location")
        
        draw_enable_panel_settings(layout, self, context)
    
        if not "WindowsApps" in blender_dir:
            draw_luts_properties(layout, self, context)
        
        draw_backup_restore(layout, self, context)
        draw_check_updates(layout, self, context)
        
# ----------------------------------------------------------------------------

# define render palette menu (3D view> View Menu> Render Palette)
class RENDER_MT_palette_menu(bpy.types.Menu):
    bl_label = "Render Palette"
    bl_idname = "RENDER_MT_palette_menu"

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__name__].preferences
        
        layout.prop(prefs, "enable_batch_render", text="Batch Render Panel")
        layout.prop(prefs, "enable_cam_properties", text="Camera Properties Panel")
        layout.prop(prefs, "enable_lens_properties", text="Lens Properties Panel")
        layout.prop(prefs, "enable_constraints", text="Tracking Settings Panel")
        layout.prop(prefs, "enable_render_preset", text="Render Preset Panel")

def draw_func(self, context):
    layout = self.layout
    layout.menu(RENDER_MT_palette_menu.bl_idname)

# ----------------------------------------------------------------------------

classes = [
    RENDER_PT_main_panel,
    RENDER_PT_settings_panel,
    
    RENDER_PT_environment_panel,
    RENDER_PT_envset_panel,
    RENDER_OT_apply_env_texture,
    RENDER_OT_remove_env_texture,
    IMPORT_OT_world_texture,
    IMPORT_OT_world_textures_from_folder,
    RENDER_OT_next_exr,
    RENDER_PG_exr_props,
    
    RENDER_PT_camera_controls,
    RENDER_PT_camera_properties,
    RENDER_PT_tracking_constraints,
    RENDER_OT_Camera_Orientation,
    OBJECT_OT_apply_remove_constraint,
    RENDER_OT_create_camera_to_view,
    RENDER_OT_align_camera_to_view,
    
    RENDER_PT_Batch_Render,
    RENDER_OT_Batch_Render,
    RENDER_CAM_UL_List,
    RENDER_OT_Camera_List,
    
    RENDER_PT_preset_panel,
    RENDER_OT_initialize,
    RENDER_OT_open_preset_directory,
    RENDER_OT_add_preset,
    RENDER_OT_remove_preset,
    RENDER_OT_export_preset,
    RENDER_OT_import_preset,
    RENDER_OT_apply_preset,
    RENDER_OT_save_preset,
    RENDER_OT_move_preset,
    RENDER_MT_preset_menu,
    RENDER_OT_refresh_presets,
    RENDER_UL_presets,
    RENDER_PG_preset,
    RENDER_OT_show_preset_info,
    
    RENDER_OT_autosave,
    RENDER_OT_toggle_autosave,
    RENDER_PG_autosave_props,
    RENDER_OT_toggle_dof,
    
    RENDER_PT_lut_properties, 
    RENDER_OT_lut_apply, 
    RENDER_OT_lut_restore,
    RENDER_OT_lut_info,
    RENDER_OT_lut_warning,
    
    RENDERPALATTE_Preferences,
    RENDER_OT_check_for_updates,
    RENDER_OT_open_update_page,
    RENDER_OT_backup_paths,
    RENDER_OT_restore_paths,
    RENDER_MT_palette_menu,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Call auto_restore_paths after a delay
    bpy.app.timers.register(lambda: auto_restore_paths(None))
    
    bpy.types.Scene.render_type = bpy.props.EnumProperty(
        name="Render Type",
        description="Select render type",
        items=[
            ('IMAGE', 'Image', 'Properties for Rendering Image'),
            ('ANIMATION', 'Animation', 'Properties for Rendering animation'),
        ],
        default='IMAGE',
    )

    bpy.types.Scene.framerate_preset = EnumProperty(
        name="FPS",
        description="Frames per second",
        items=[
            ('23.98', "23.98", ""),
            ('24', "24 fps", ""),
            ('25', "25", ""),
            ('29.97', "29.97", ""),
            ('30', "30", ""),
            ('50', "50", ""),
            ('59.94', "59.94", ""),
            ('60', "60", ""),
            ('120', "120", ""),
            ('240', "240", ""),
            ('CUSTOM', "Custom", "")
        ],
        default='24',
        update=update_fps
    )

    bpy.types.Scene.custom_fps = bpy.props.IntProperty(
        name="Custom FPS",
        description="Set a custom value for frames per second",
        default=24,
        min=1,
        update=update_fps,
    )

    bpy.types.Scene.resolution_preset = bpy.props.EnumProperty(
        name="Resolution Preset",
        description="Select the camera resolution from a list of predefined options",
        items=[
            ('720p', '720p', '1280x720'),
            ('1080p', '1080p', '1920x1080'),
            ('1440p', '1440p', '2560x1440'),
            ('4K', '4K QHD', '3840x2160'),
            ('8K', '8K QHD', '7680x4320'),
            ('Custom', 'Custom', 'Set a custom resolution'),
        ],
        default='1080p',
        update=update_resolution,
    )

    bpy.types.Scene.samples_preset = bpy.props.EnumProperty(
        name="Render Samples Preset",
        description="Select the render samples from a list of predefined options. Only for Cycles engine",
        items=get_samples_items,
        update=update_samples,
    )
    
    bpy.types.Scene.file_format = bpy.props.EnumProperty(
        name="File Format",
        description="Select the output file format",
        items=[
            ('PNG', 'PNG', 'Portable Network Graphics'),
            ('JPEG', 'JPEG', 'Joint Photographic Experts Group'),
            ('TIFF', 'TIFF', 'Tagged Image File Format'),
            ('OPEN_EXR', 'OpenEXR', 'OpenEXR High Dynamic Range Image'),
            ('BMP', 'BMP', 'Bitmap Image'),
            ('FFMPEG', 'FFMPEG', 'FFmpeg video format'),
            ('MP4', 'MP4', 'MPEG-4 video format'),
        ],
        default='PNG',
        update=update_file_format,
    )
    
    bpy.types.Scene.location_type = bpy.props.EnumProperty(
        items=[
            ('DEFAULT', 'Default Folder', "Save Renders in the output folder"),
            ('SEPARATE_FOLDERS', 'Separate Folders', "Save each camera's renders in separate folders")
        ],
        default='DEFAULT',
        name="Location Type",
        description="Choose the location type for renders",
    )

    bpy.types.Scene.render_option = bpy.props.EnumProperty(
        items=[('ALL_CAMERAS', 'All Camera', 'Render with all cameras in the scene'),
               ('CUSTOM', 'Custom', 'Render with a custom list of cameras')],
        default='ALL_CAMERAS',
        name="Camera",
        description="Choose how to render cameras",
    )
    
    bpy.types.Scene.custom_overwrite = bpy.props.EnumProperty(
        name="Overwrite",
        items=[('OFF', 'Off', 'Overwrite is OFF', 0),
               ('ON', 'On', 'Overwrite is ON', 1)],
        default='ON',
        update=custom_overwrite_update
    )
    
    bpy.types.Scene.show_render_preset_panel = bpy.props.BoolProperty(
        name="Show Render Preset Panel",
        default=False,
    )

    bpy.types.VIEW3D_MT_view.append(draw_func)
    
    # Register Batch Render Camera List
    bpy.types.Scene.batch_render_cameras = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.active_camera_index = bpy.props.IntProperty()
    
    # Register World Properties
    bpy.types.Scene.render_palette_exr_props = PointerProperty(type=RENDER_PG_exr_props)
    
    # Register Autosave Properties
    bpy.types.Scene.render_palette_autosave_props = PointerProperty(type=RENDER_PG_autosave_props)
    
    # Register Lut Properties
    bpy.types.Scene.lut_tool = bpy.props.PointerProperty(type=RENDER_PT_lut_properties)
    
    # Register Presets Properties
    bpy.types.Scene.render_palette_presets = CollectionProperty(type=RENDER_PG_preset)
    bpy.types.Scene.render_palette_presets_index = IntProperty()
    
    # Register addon preference bool properties
    bpy.types.Scene.expand_prop = bpy.props.BoolProperty(name="Expand Box", default=False)
    bpy.types.Scene.expand_backup = bpy.props.BoolProperty(name="Expand Box", default=False)
    bpy.types.Scene.expand_luts = bpy.props.BoolProperty(name="Expand Box", default=False)
    bpy.types.Scene.expand_update = bpy.props.BoolProperty(name="Expand Box", default=False)
    
    bpy.app.handlers.load_post.append(show_update_popup)
        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    bpy.types.VIEW3D_HT_header.remove(draw_func)
    
    del bpy.types.Scene.expand_prop
    del bpy.types.Scene.expand_backup
    del bpy.types.Scene.expand_luts
    del bpy.types.Scene.expand_update
    
    del bpy.types.Scene.lut_tool
    
    del bpy.types.Scene.render_palette_exr_props
    del bpy.types.Scene.render_palette_autosave_props

    del bpy.types.Scene.resolution_preset
    del bpy.types.Scene.samples_preset
    del bpy.types.Scene.framerate_preset
    
    del bpy.types.Scene.batch_render_cameras
    del bpy.types.Scene.active_camera_index
    del bpy.types.Scene.render_type
    del bpy.types.Scene.location_type
    del bpy.types.Scene.render_option
    
    del bpy.types.Scene.custom_overwrite

if __name__ == "__main__":
    register()