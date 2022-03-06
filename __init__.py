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
    "name": "GI Comp",
    "version": (0, 1, 0),
    "author": "Nathan Vegdahl, Ian Hubert",
    "blender": (3, 0, 0),
    "description": "Composite CG elements into your footage with GI lighting",
    "location": "Scene properties",
    # "doc_url": "",
    "category": "Compositing",
}

import re
import math

import bpy

MATERIAL_NAME_PREFIX = "GICompFootage"


#========================================================


class GICompPanel(bpy.types.Panel):
    """Composite with GI lighting."""
    bl_label = "GI Comp"
    bl_idname = "DATA_PT_gi_comp"
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
        col.operator("material.gi_comp_material_new")


#========================================================


# Builds a material with the GI Comp footage configuration..
def make_gi_comp_material(name, context):
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
    delight_group.node_tree = ensure_delight_bake_group()


# Ensures that the Delight Bake shader group exists.
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


class GICompMaterialNew(bpy.types.Operator):
    """Creates a new GI Comp material"""
    bl_idname = "material.gi_comp_material_new"
    bl_label = "New GI Comp material"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        make_gi_comp_material(MATERIAL_NAME_PREFIX, context)
        return {'FINISHED'}


#========================================================


def register():
    bpy.utils.register_class(GICompPanel)
    bpy.utils.register_class(GICompMaterialNew)


def unregister():
    bpy.utils.unregister_class(GICompPanel)
    bpy.utils.unregister_class(GICompMaterialNew)


if __name__ == "__main__":
    register()
