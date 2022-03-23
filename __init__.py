#====================== BEGIN GPL LICENSE BLOCK ======================
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
#======================= END GPL LICENSE BLOCK ========================

bl_info = {
    "name": "Compify",
    "version": (0, 1, 0),
    "author": "Nathan Vegdahl, Ian Hubert",
    "blender": (3, 0, 0),
    "description": "Do compositing in 3D space.",
    "location": "Scene properties",
    # "doc_url": "",
    "category": "Compositing",
}

import re
import math

import bpy

MATERIAL_NAME_PREFIX = "CompifyFootage"


#========================================================


class CompifyPanel(bpy.types.Panel):
    """Composite in 3D space."""
    bl_label = "Compify"
    bl_idname = "DATA_PT_compify"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        col = layout.column()
        col.operator("material.compify_material_new")


class CompifyCameraPanel(bpy.types.Panel):
    """Configure cameras for 3D compositing."""
    bl_label = "Comp Tools"
    bl_idname = "DATA_PT_comp_tools_camera"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'CAMERA'

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        col = layout.column()
        col.operator("material.compify_camera_project_new")

#========================================================


# Builds a material with the Compify footage configuration.
def make_compify_material(name, context):
    # Create a new completely empty node-based material.
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

    # Create the nodes we need.
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    footage = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    lighting_bake = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    diffuse = mat.node_tree.nodes.new(type='ShaderNodeBsdfDiffuse')
    delight_group = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    delight_group.node_tree = ensure_delight_baker_group()


# Ensures that the Delight Baker shader group exists.
#
# It will create it if it doesn't exist, and returns the group.
def ensure_delight_baker_group():
    NAME = "Delight Baker"
    if NAME in bpy.data.node_groups:
        return bpy.data.node_groups[NAME]
    else:
        group = bpy.data.node_groups.new(NAME, type='ShaderNodeTree')
        for node in group.nodes:
            group.nodes.remove(node)

        # Create the nodes.
        input = group.nodes.new(type='NodeGroupInput')
        output = group.nodes.new(type='NodeGroupOutput')
        lightpath = group.nodes.new(type='ShaderNodeLightPath')
        diffuse = group.nodes.new(type='ShaderNodeBsdfDiffuse')
        mix = group.nodes.new(type='ShaderNodeMixShader')

        # Position the nodes.
        input.location = (-400.0, 0.0)
        output.location = (200.0, 0.0)
        lightpath.location = (-200.0, 400.0)
        diffuse.location = (-200.0, -100.0)
        mix.location = (0.0, 0.0)

        # Configure the nodes.
        group.inputs.new(type="NodeSocketShader", name="Shader")
        group.outputs.new(type="NodeSocketShader", name="Shader")
        diffuse.inputs['Color'].default_value = [1.0, 1.0, 1.0, 1.0]
        diffuse.inputs['Roughness'].default_value = 0.0

        # Hook up the nodes.
        group.links.new(lightpath.outputs['Is Camera Ray'], mix.inputs['Fac'])
        group.links.new(input.outputs['Shader'], mix.inputs[1])
        group.links.new(diffuse.outputs['BSDF'], mix.inputs[2])
        group.links.new(mix.outputs['Shader'], output.inputs['Shader'])

        return group

# Takes a camera object, and ensures there is a node group for
# projecting textures from that camera.
#
# It will create it if it doesn't exist, and returns the group.
def ensure_camera_project_group(camera):
    name = "Camera Project | " + camera.name

    # Fetch or create group.
    group = None
    if name in bpy.data.node_groups:
        group = bpy.data.node_groups[name]
    else:
        group = bpy.data.node_groups.new(name, type='ShaderNodeTree')

    # Clear all nodes, to start from a clean slate.
    for node in group.nodes:
        group.nodes.remove(node)

    # Create the group inputs and outputs.
    if not "Aspect Ratio" in group.inputs:
        group.inputs.new(type="NodeSocketFloat", name="Aspect Ratio")
        group.inputs['Aspect Ratio'].default_value = 1.0
    if not "Rotation" in group.inputs:
        group.inputs.new(type="NodeSocketFloat", name="Rotation")
    if not "Loc X" in group.inputs:
        group.inputs.new(type="NodeSocketFloat", name="Loc X")
    if not "Loc Y" in group.inputs:
        group.inputs.new(type="NodeSocketFloat", name="Loc Y")
    if not "Vector" in group.outputs:
        group.outputs.new(type="NodeSocketVector", name="Vector")

    #-------------------
    # Create the nodes.
    input = group.nodes.new(type='NodeGroupInput')
    output = group.nodes.new(type='NodeGroupOutput')

    geometry = group.nodes.new(type='ShaderNodeNewGeometry')
    camera_loc = group.nodes.new(type='ShaderNodeCombineXYZ')
    camera_rot = group.nodes.new(type='ShaderNodeCombineXYZ')
    lens = group.nodes.new(type='ShaderNodeValue')
    sensor_width = group.nodes.new(type='ShaderNodeValue')
    lens_shift_x = group.nodes.new(type='ShaderNodeValue')
    lens_shift_y = group.nodes.new(type='ShaderNodeValue')

    zoom_1 = group.nodes.new(type='ShaderNodeMath')
    zoom_2 = group.nodes.new(type='ShaderNodeMath')
    lens_shift_1 = group.nodes.new(type='ShaderNodeCombineXYZ')
    user_rotation_1 = group.nodes.new(type='ShaderNodeMath')
    user_location = group.nodes.new(type='ShaderNodeCombineXYZ')

    camera_transform_1 = group.nodes.new(type='ShaderNodeVectorMath')
    camera_transform_2 = group.nodes.new(type='ShaderNodeVectorRotate')
    perspective_1 = group.nodes.new(type='ShaderNodeSeparateXYZ')
    perspective_2 = group.nodes.new(type='ShaderNodeMath')
    perspective_3 = group.nodes.new(type='ShaderNodeMath')
    perspective_4 = group.nodes.new(type='ShaderNodeCombineXYZ')
    zoom_3 = group.nodes.new(type='ShaderNodeVectorMath')
    lens_shift_2 = group.nodes.new(type='ShaderNodeVectorMath')

    user_translate = group.nodes.new(type='ShaderNodeVectorMath')
    user_rotation_2 = group.nodes.new(type='ShaderNodeVectorRotate')
    aspect_ratio = group.nodes.new(type='ShaderNodeCombineXYZ')
    user_transforms = group.nodes.new(type='ShaderNodeVectorMath')

    recenter = group.nodes.new(type='ShaderNodeVectorMath')

    #---------------------
    # Position the nodes.
    hs = 250.0
    x = 0.0

    geometry.location = (x, 0.0)
    camera_loc.location = (x, -300.0)
    camera_rot.location = (x, -500.0)
    lens.location = (x, -700.0)
    sensor_width.location = (x, -900.0)
    lens_shift_x.location = (x, -1100.0)
    lens_shift_y.location = (x, -1300.0)
    input.location = (x, -1500.0)

    x += hs
    zoom_1.location = (x, -700.0)
    lens_shift_1.location = (x, -1100.0)
    user_rotation_1.location = (x, -1500.0)
    user_location.location = (x, -1700.0)

    x += hs
    zoom_2.location = (x, -700.0)

    x += hs
    camera_transform_1.location = (x, 0.0)

    x += hs
    camera_transform_2.location = (x, 0.0)

    x += hs
    perspective_1.location = (x, 0.0)

    x += hs
    perspective_2.location = (x, 0.0)
    perspective_3.location = (x, -200.0)

    x += hs
    perspective_4.location = (x, 0.0)

    x += hs
    zoom_3.location = (x, 0.0)

    x += hs
    lens_shift_2.location = (x, 0.0)

    x += hs
    user_translate.location = (x, 0.0)

    x += hs
    user_rotation_2.location = (x, 0.0)
    aspect_ratio.location = (x, -300.0)

    x += hs
    user_transforms.location = (x, 0.0)

    x += hs
    recenter.location = (x, 0.0)

    x += hs
    output.location = (x, 0.0)

    #---------------------
    # Set up the drivers.

    # Camera location drivers.
    drv_loc_x = camera_loc.inputs['X'].driver_add("default_value").driver
    drv_loc_y = camera_loc.inputs['Y'].driver_add("default_value").driver
    drv_loc_z = camera_loc.inputs['Z'].driver_add("default_value").driver
    drv_loc_x.type = 'SUM'
    drv_loc_y.type = 'SUM'
    drv_loc_z.type = 'SUM'
    var_x = drv_loc_x.variables.new()
    var_y = drv_loc_y.variables.new()
    var_z = drv_loc_z.variables.new()
    var_x.type = 'TRANSFORMS'
    var_y.type = 'TRANSFORMS'
    var_z.type = 'TRANSFORMS'
    var_x.targets[0].id = camera
    var_y.targets[0].id = camera
    var_z.targets[0].id = camera
    var_x.targets[0].transform_type = 'LOC_X'
    var_y.targets[0].transform_type = 'LOC_Y'
    var_z.targets[0].transform_type = 'LOC_Z'
    var_x.targets[0].transform_space = 'WORLD_SPACE'
    var_y.targets[0].transform_space = 'WORLD_SPACE'
    var_z.targets[0].transform_space = 'WORLD_SPACE'

    # Camera rotation drivers.
    drv_rot_x = camera_rot.inputs['X'].driver_add("default_value").driver
    drv_rot_y = camera_rot.inputs['Y'].driver_add("default_value").driver
    drv_rot_z = camera_rot.inputs['Z'].driver_add("default_value").driver
    drv_rot_x.type = 'SUM'
    drv_rot_y.type = 'SUM'
    drv_rot_z.type = 'SUM'
    var_x = drv_rot_x.variables.new()
    var_y = drv_rot_y.variables.new()
    var_z = drv_rot_z.variables.new()
    var_x.type = 'TRANSFORMS'
    var_y.type = 'TRANSFORMS'
    var_z.type = 'TRANSFORMS'
    var_x.targets[0].id = camera
    var_y.targets[0].id = camera
    var_z.targets[0].id = camera
    var_x.targets[0].rotation_mode = 'XYZ'
    var_y.targets[0].rotation_mode = 'XYZ'
    var_z.targets[0].rotation_mode = 'XYZ'
    var_x.targets[0].transform_type = 'ROT_X'
    var_y.targets[0].transform_type = 'ROT_Y'
    var_z.targets[0].transform_type = 'ROT_Z'
    var_x.targets[0].transform_space = 'WORLD_SPACE'
    var_y.targets[0].transform_space = 'WORLD_SPACE'
    var_z.targets[0].transform_space = 'WORLD_SPACE'

    drv_lens = lens.outputs['Value'].driver_add("default_value").driver
    drv_lens.type = 'SUM'
    var = drv_lens.variables.new()
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'CAMERA'
    var.targets[0].id = camera.data
    var.targets[0].data_path = 'lens'

    drv_width = sensor_width.outputs['Value'].driver_add("default_value").driver
    drv_width.type = 'SUM'
    var = drv_width.variables.new()
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'CAMERA'
    var.targets[0].id = camera.data
    var.targets[0].data_path = 'sensor_width'

    drv_shift_x = lens_shift_x.outputs['Value'].driver_add("default_value").driver
    drv_shift_x.type = 'SUM'
    var = drv_shift_x.variables.new()
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'CAMERA'
    var.targets[0].id = camera.data
    var.targets[0].data_path = 'shift_x'

    drv_shift_y = lens_shift_y.outputs['Value'].driver_add("default_value").driver
    drv_shift_y.type = 'SUM'
    var = drv_shift_y.variables.new()
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'CAMERA'
    var.targets[0].id = camera.data
    var.targets[0].data_path = 'shift_y'

    #----------------------
    # Configure the nodes.
    zoom_1.operation = 'DIVIDE'
    zoom_1.use_clamp = False
    zoom_2.operation = 'MULTIPLY'
    zoom_2.use_clamp = False
    zoom_2.inputs[1].default_value = -1.0
    lens_shift_1.inputs[2].default_value = 0.0
    user_rotation_1.operation = 'MULTIPLY'
    user_rotation_1.use_clamp = False
    user_rotation_1.inputs[1].default_value = math.pi / 180.0
    user_location.inputs[2].default_value = 0.0

    camera_transform_1.operation = 'SUBTRACT'
    camera_transform_2.rotation_type = 'EULER_XYZ'
    camera_transform_2.invert = True
    camera_transform_2.inputs['Center'].default_value = (0.0, 0.0, 0.0)
    perspective_2.operation = 'DIVIDE'
    perspective_2.use_clamp = False
    perspective_3.operation = 'DIVIDE'
    perspective_3.use_clamp = False
    zoom_3.operation = 'MULTIPLY'
    lens_shift_2.operation = 'SUBTRACT'

    user_translate.operation = 'SUBTRACT'
    user_rotation_2.rotation_type = 'Z_AXIS'
    user_rotation_2.invert = False
    user_rotation_2.inputs['Center'].default_value = (0.0, 0.0, 0.0)
    aspect_ratio.inputs['X'].default_value = 1.0
    aspect_ratio.inputs['Z'].default_value = 0.0
    user_transforms.operation = 'MULTIPLY'

    recenter.operation = 'ADD'
    recenter.inputs[1].default_value = (0.5, 0.5, 0.0)

    #--------------------
    # Hook up the nodes.
    group.links.new(geometry.outputs['Position'], camera_transform_1.inputs[0])
    group.links.new(camera_loc.outputs['Vector'], camera_transform_1.inputs[1])
    group.links.new(camera_rot.outputs['Vector'], camera_transform_2.inputs['Rotation'])
    group.links.new(lens.outputs['Value'], zoom_1.inputs[0])
    group.links.new(sensor_width.outputs['Value'], zoom_1.inputs[1])
    group.links.new(zoom_1.outputs['Value'], zoom_2.inputs[0])
    group.links.new(zoom_2.outputs['Value'], zoom_3.inputs[1])
    group.links.new(lens_shift_x.outputs['Value'], lens_shift_1.inputs['X'])
    group.links.new(lens_shift_y.outputs['Value'], lens_shift_1.inputs['Y'])
    group.links.new(lens_shift_1.outputs['Vector'], lens_shift_2.inputs[1])

    group.links.new(input.outputs['Aspect Ratio'], aspect_ratio.inputs[1])
    group.links.new(input.outputs['Rotation'], user_rotation_1.inputs[0])
    group.links.new(user_rotation_1.outputs['Value'], user_rotation_2.inputs['Angle'])
    group.links.new(input.outputs['Loc X'], user_location.inputs['X'])
    group.links.new(input.outputs['Loc Y'], user_location.inputs['Y'])
    group.links.new(user_location.outputs['Vector'], user_translate.inputs[1])

    group.links.new(camera_transform_1.outputs['Vector'], camera_transform_2.inputs['Vector'])
    group.links.new(camera_transform_2.outputs['Vector'], perspective_1.inputs['Vector'])
    group.links.new(perspective_1.outputs['X'], perspective_2.inputs[0])
    group.links.new(perspective_1.outputs['Y'], perspective_3.inputs[0])
    group.links.new(perspective_1.outputs['Z'], perspective_2.inputs[1])
    group.links.new(perspective_1.outputs['Z'], perspective_3.inputs[1])
    group.links.new(perspective_1.outputs['Z'], perspective_4.inputs['Z'])
    group.links.new(perspective_2.outputs['Value'], perspective_4.inputs['X'])
    group.links.new(perspective_3.outputs['Value'], perspective_4.inputs['Y'])
    group.links.new(perspective_4.outputs['Vector'], zoom_3.inputs[0])
    group.links.new(zoom_3.outputs['Vector'], lens_shift_2.inputs[0])
    group.links.new(lens_shift_2.outputs['Vector'], user_translate.inputs[0])

    group.links.new(user_translate.outputs['Vector'], user_rotation_2.inputs['Vector'])
    group.links.new(user_rotation_2.outputs['Vector'], user_transforms.inputs[0])
    group.links.new(aspect_ratio.outputs['Vector'], user_transforms.inputs[1])
    group.links.new(user_transforms.outputs['Vector'], recenter.inputs[0])

    group.links.new(recenter.outputs['Vector'], output.inputs['Vector'])

    return group


class CompifyMaterialNew(bpy.types.Operator):
    """Creates a new Compify material"""
    bl_idname = "material.compify_material_new"
    bl_label = "New Compify material"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        make_compify_material(MATERIAL_NAME_PREFIX, context)
        return {'FINISHED'}


class CompifyCameraProjectGroupNew(bpy.types.Operator):
    """Creates a new camera projection node group from the current selected camera"""
    bl_idname = "material.compify_camera_project_new"
    bl_label = "New Camera Project Node Group"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object != None and context.active_object.type == 'CAMERA'

    def execute(self, context):
        ensure_camera_project_group(context.active_object)
        return {'FINISHED'}


#========================================================


def register():
    bpy.utils.register_class(CompifyPanel)
    bpy.utils.register_class(CompifyCameraPanel)
    bpy.utils.register_class(CompifyMaterialNew)
    bpy.utils.register_class(CompifyCameraProjectGroupNew)


def unregister():
    bpy.utils.unregister_class(CompifyPanel)
    bpy.utils.unregister_class(CompifyCameraPanel)
    bpy.utils.unregister_class(CompifyMaterialNew)
    bpy.utils.unregister_class(CompifyCameraProjectGroupNew)


if __name__ == "__main__":
    register()
