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

import bpy

from .node_groups import \
    ensure_delight_baker_group, \
    ensure_camera_project_group, \
    ensure_feathered_square_group

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
        col.operator("material.compify_temp")


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


class CompifyTemp(bpy.types.Operator):
    """Temp for testing.."""
    bl_idname = "material.compify_temp"
    bl_label = "Compify Temp"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        ensure_feathered_square_group()
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
    bpy.utils.register_class(CompifyTemp)


def unregister():
    bpy.utils.unregister_class(CompifyPanel)
    bpy.utils.unregister_class(CompifyCameraPanel)
    bpy.utils.unregister_class(CompifyMaterialNew)
    bpy.utils.unregister_class(CompifyCameraProjectGroupNew)
    bpy.utils.unregister_class(CompifyTemp)


if __name__ == "__main__":
    register()
