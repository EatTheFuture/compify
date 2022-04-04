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
    ensure_footage_group, \
    ensure_camera_project_group, \
    ensure_feathered_square_group

MAIN_NODE_NAME = "Compify Footage"
BAKE_IMAGE_NODE_NAME = "Baked Lighting"

# Gets the Compify Material name for the active scene.
def compify_mat_name(context):
    return "Compify Footage | " + context.scene.name


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

        col.template_ID(context.scene, "compify_footage", open="image.open")
        if context.scene.compify_footage != None:
            col.prop(context.scene.compify_footage.colorspace_settings, "name")

        col.separator_spacer()

        col.prop(context.scene, "compify_footage_camera")
        col.prop(context.scene, "compify_proxy_collection")
        col.prop(context.scene, "compify_lights_collection")

        col.separator_spacer()

        col.operator("material.compify_material_new")
        col.operator("material.compify_bake")


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

# Ensures that the Compify Footage material exists for this scene.
#
# It will create it if it doesn't exist, and returns the material.
def ensure_compify_material(context):
    name = compify_mat_name(context)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    else:
        return create_compify_material(
            name,
            context.scene.compify_footage_camera,
            context.scene.compify_footage,
        )


# Creates a Compify Footage material.
def create_compify_material(name, camera, footage):
    # Create a new completely empty node-based material.
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'HASHED'
    mat.shadow_method = 'HASHED'
    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

    # Create the nodes.
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    camera_project = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    input_footage = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    feathered_square = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    baked_lighting = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    compify_footage = mat.node_tree.nodes.new(type='ShaderNodeGroup')

    # Label and name the nodes.
    camera_project.label = "Camera Project"
    input_footage.label = "Input Footage"
    feathered_square.label = "Feathered Square"
    baked_lighting.label = BAKE_IMAGE_NODE_NAME
    compify_footage.label = MAIN_NODE_NAME

    camera_project.name = "Camera Project"
    input_footage.name = "Input Footage"
    feathered_square.name = "Feathered Square"
    baked_lighting.name = BAKE_IMAGE_NODE_NAME
    compify_footage.name = MAIN_NODE_NAME

    # Position the nodes.
    hs = 400.0
    x = 0.0

    camera_project.location = (x, 0.0)
    x += hs
    input_footage.location = (x, 400.0)
    feathered_square.location = (x, 0.0)
    baked_lighting.location = (x, -200.0)
    x += hs
    compify_footage.location = (x, 0.0)
    x += hs
    output.location = (x, 0.0)

    # Configure the nodes.
    camera_project.node_tree = ensure_camera_project_group(camera)
    camera_project.inputs['Aspect Ratio'].default_value = footage.size[0] / footage.size[1]

    input_footage.image = footage
    input_footage.interpolation = 'Closest'
    input_footage.projection = 'FLAT'
    input_footage.extension = 'EXTEND'
    input_footage.image_user.frame_duration = footage.frame_duration
    input_footage.image_user.use_auto_refresh = True

    feathered_square.node_tree = ensure_feathered_square_group()
    feathered_square.inputs['Feather'].default_value = 0.05
    feathered_square.inputs['Dilate'].default_value = 0.0

    baked_lighting.image = None # TODO
    compify_footage.node_tree = ensure_footage_group()

    # Hook up the nodes.
    mat.node_tree.links.new(camera_project.outputs['Vector'], input_footage.inputs['Vector'])
    mat.node_tree.links.new(camera_project.outputs['Vector'], feathered_square.inputs['Vector'])
    mat.node_tree.links.new(input_footage.outputs['Color'], compify_footage.inputs['Footage'])
    mat.node_tree.links.new(feathered_square.outputs['Value'], compify_footage.inputs['Footage-Background Mask'])
    mat.node_tree.links.new(baked_lighting.outputs['Color'], compify_footage.inputs['Baked Lighting'])
    mat.node_tree.links.new(compify_footage.outputs['Shader'], output.inputs['Surface'])


class CompifyMaterialNew(bpy.types.Operator):
    """Creates a new Compify material"""
    bl_idname = "material.compify_material_new"
    bl_label = "New Compify material"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        ensure_compify_material(context)
        return {'FINISHED'}


class CompifyBake(bpy.types.Operator):
    """Does the Compify lighting baking for proxy geometry."""
    bl_idname = "material.compify_bake"
    bl_label = "Bake Footage Lighting"
    bl_options = {'UNDO'}

    # Operator fields, for keeping track of state during modal operation.
    _timer = None
    is_started = False
    hide_render_list = {}
    main_node = None

    # Note: we use a modal technique inspired by this to keep the baking
    # from blocking the UI:
    # https://blender.stackexchange.com/questions/71454/is-it-possible-to-make-a-sequence-of-renders-and-give-the-user-the-option-to-can

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        # Clear operator fields.  Not strictly necessary, since they
        # should be cleared at the end of the bake.  But just in case.
        self._timer = None
        self.is_started = False
        self.hide_render_list = {}
        self.main_node = None

        # Misc setup and checks.
        if context.scene.compify_proxy_collection == None:
            return {'CANCELLED'}
        proxy_objects = context.scene.compify_proxy_collection.objects
        proxy_lights = []
        if context.scene.compify_lights_collection != None:
            proxy_lights = context.scene.compify_lights_collection.objects
        material = bpy.data.materials[compify_mat_name(context)]
        self.main_node = material.node_tree.nodes[MAIN_NODE_NAME]
        delight_image_node = material.node_tree.nodes[BAKE_IMAGE_NODE_NAME]

        if len(proxy_objects) == 0:
            return {'CANCELLED'}

        # Configure the material for baking mode.
        self.main_node.inputs["Do Bake"].default_value = 1.0
        self.main_node.inputs["Debug"].default_value = 0.0
        delight_image_node.select = True
        material.node_tree.nodes.active = delight_image_node

        # Select all proxy geometry objects, and nothing else.
        for obj in context.scene.objects:
            obj.select_set(False)
        for obj in proxy_objects:
            obj.select_set(True)
        context.view_layer.objects.active = proxy_objects[0]

        # Build a dictionary of the visibility of non-proxy objects so that
        # we can restore it afterwards.
        for obj in context.scene.objects:
            if obj.name not in proxy_objects and obj.name not in proxy_lights:
                self.hide_render_list[obj.name] = obj.hide_render

        # Make all non-proxy objects invisible.
        for obj_name in self.hide_render_list:
            bpy.data.objects[obj_name].hide_render = True

        # Set up the timer.
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self.is_started:
                self.is_started = True
                # Do the bake.
                bpy.ops.object.bake(
                    "INVOKE_DEFAULT",
                    type='DIFFUSE',
                    # pass_filter={},
                    # filepath='',
                    # width=512,
                    # height=512,
                    margin=4,
                    margin_type='EXTEND',
                    use_selected_to_active=False,
                    max_ray_distance=0.0,
                    cage_extrusion=0.0,
                    cage_object='',
                    normal_space='TANGENT',
                    normal_r='POS_X',
                    normal_g='POS_Y',
                    normal_b='POS_Z',
                    target='IMAGE_TEXTURES',
                    save_mode='INTERNAL',
                    use_clear=True,
                    use_cage=False,
                    use_split_materials=False,
                    use_automatic_name=False,
                    uv_layer='',
                )
            # elif not self.is_baking:
            else:
                # Clean up the handlers and timer.
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None

                # Restore visibility of non-proxy objects.
                for obj_name in self.hide_render_list:
                    bpy.data.objects[obj_name].hide_render = self.hide_render_list[obj_name]
                self.hide_render_list = {}

                # Set material to non-bake mode.
                self.main_node.inputs["Do Bake"].default_value = 0.0
                self.main_node = None

                # Reset other self properties.
                self.is_started = False

                return {'FINISHED'}

        return {'PASS_THROUGH'}


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
    bpy.utils.register_class(CompifyBake)
    bpy.utils.register_class(CompifyCameraProjectGroupNew)

    # Custom properties.
    bpy.types.Scene.compify_footage_camera = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Footage Camera",
    )
    bpy.types.Scene.compify_footage = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Footage Texture",
    )
    bpy.types.Scene.compify_proxy_collection = bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Proxy Collection",
    )
    bpy.types.Scene.compify_lights_collection = bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Lights Collection",
    )

def unregister():
    bpy.utils.unregister_class(CompifyPanel)
    bpy.utils.unregister_class(CompifyCameraPanel)
    bpy.utils.unregister_class(CompifyMaterialNew)
    bpy.utils.unregister_class(CompifyBake)
    bpy.utils.unregister_class(CompifyCameraProjectGroupNew)


if __name__ == "__main__":
    register()
