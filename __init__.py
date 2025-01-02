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
    "blender": (4, 0, 0),
    "description": "Do compositing in 3D space.",
    "location": "Scene properties",
    # "doc_url": "",
    "category": "Compositing",
}

import re
import math

import bpy

from .names import \
    compify_mat_name, \
    compify_baked_texture_name, \
    MAIN_NODE_NAME, \
    BAKE_IMAGE_NODE_NAME, \
    UV_LAYER_NAME
from .node_groups import \
    ensure_footage_group, \
    ensure_camera_project_group, \
    ensure_feathered_square_group
from .uv_utils import leftmost_u
from .camera_align import camera_align_register, camera_align_unregister
from .bake import Baker

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

        #--------
        col = layout.column()
        col.label(text="    Footage:")
        box = col.box()
        box.template_ID(context.scene.compify_config, "footage", open="image.open")
        box.use_property_split = True
        if context.scene.compify_config.footage != None:
            box.prop(context.scene.compify_config.footage, "source")
            box.prop(context.scene.compify_config.footage.colorspace_settings, "name", text="  Color Space")
        box.prop(context.scene.compify_config, "camera", text="  Camera")

        layout.separator(factor=0.5)

        #--------
        col = layout.column()
        col.label(text="    Collections:")
        box = col.box()
        box.use_property_split = True

        row1 = box.row()
        row1.prop(context.scene.compify_config, "geo_collection", text="  Footage Geo")
        row1.operator("scene.compify_add_footage_geo_collection", text="", icon='ADD')

        row2 = box.row()
        row2.prop(context.scene.compify_config, "lights_collection", text="  Footage Lights")
        row2.operator("scene.compify_add_footage_lights_collection", text="", icon='ADD')

        layout.separator(factor=1.0)

        layout.use_property_split = True
        layout.prop(context.scene.compify_config, "bake_uv_margin")
        layout.prop(context.scene.compify_config, "bake_image_res")

        layout.separator(factor=1.0)

        #--------
        layout.operator("material.compify_prep_scene")
        layout.operator("material.compify_bake")
        layout.operator("render.compify_render")


class CompifyCameraPanel(bpy.types.Panel):
    """Configure cameras for 3D compositing."""
    bl_label = "Compify"
    bl_idname = "DATA_PT_compify_camera"
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


# Fetches the current scene's compify material if it exists.
#
# Returns the material if it exists and None if it doesn't.
def get_compify_material(context):
    name = compify_mat_name(context)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    else:
        return None


# Ensures that the Compify Footage material exists for this scene.
#
# It will create it if it doesn't exist, and returns the material.
def ensure_compify_material(context):
    mat = get_compify_material(context)
    if mat != None:
        return mat
    else:
        return create_compify_material(
            compify_mat_name(context),
            context.scene.compify_config.camera,
            context.scene.compify_config.footage,
        )


# Creates a Compify Footage material.
def create_compify_material(name, camera, footage):
    # Create a new completely empty node-based material.
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'HASHED'
    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

    # Create the nodes.
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    camera_project = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    baking_uv_map = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
    input_footage = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    feathered_square = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    baked_lighting = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    compify_footage = mat.node_tree.nodes.new(type='ShaderNodeGroup')

    # Label and name the nodes.
    camera_project.label = "Camera Project"
    baking_uv_map.label = "Baking UV Map"
    input_footage.label = "Input Footage"
    feathered_square.label = "Feathered Square"
    baked_lighting.label = BAKE_IMAGE_NODE_NAME
    compify_footage.label = MAIN_NODE_NAME

    camera_project.name = "Camera Project"
    baking_uv_map.label = "Baking UV Map"
    input_footage.name = "Input Footage"
    feathered_square.name = "Feathered Square"
    baked_lighting.name = BAKE_IMAGE_NODE_NAME
    compify_footage.name = MAIN_NODE_NAME

    # Position the nodes.
    hs = 400.0
    x = 0.0

    camera_project.location = (x, 0.0)
    baking_uv_map.location = (x, -200.0)
    x += hs
    input_footage.location = (x, 400.0)
    feathered_square.location = (x, 0.0)
    baked_lighting.location = (x, -200.0)
    x += hs
    compify_footage.location = (x, 0.0)
    compify_footage.width = 200.0
    x += hs
    output.location = (x, 0.0)

    # Configure the nodes.
    camera_project.node_tree = ensure_camera_project_group(camera)
    if footage.size[0] > 0 and footage.size[1] > 0:
        camera_project.inputs['Aspect Ratio'].default_value = footage.size[0] / footage.size[1]
    else:
        # Default to the output render aspect ratio if we're on a bogus footage frame.
        render_x = bpy.context.scene.render.resolution_x * bpy.context.scene.render.pixel_aspect_x
        render_y = bpy.context.scene.render.resolution_y * bpy.context.scene.render.pixel_aspect_y
        camera_project.inputs['Aspect Ratio'].default_value = render_x / render_y

    baking_uv_map.uv_map = UV_LAYER_NAME

    input_footage.image = footage
    input_footage.interpolation = 'Closest'
    input_footage.projection = 'FLAT'
    input_footage.extension = 'EXTEND'
    input_footage.image_user.frame_duration = footage.frame_duration
    input_footage.image_user.use_auto_refresh = True

    feathered_square.node_tree = ensure_feathered_square_group()
    feathered_square.inputs['Feather'].default_value = 0.05
    feathered_square.inputs['Dilate'].default_value = 0.0

    compify_footage.node_tree = ensure_footage_group()

    # Hook up the nodes.
    mat.node_tree.links.new(camera_project.outputs['Vector'], input_footage.inputs['Vector'])
    mat.node_tree.links.new(camera_project.outputs['Vector'], feathered_square.inputs['Vector'])
    mat.node_tree.links.new(baking_uv_map.outputs['UV'], baked_lighting.inputs['Vector'])
    mat.node_tree.links.new(input_footage.outputs['Color'], compify_footage.inputs['Footage'])
    mat.node_tree.links.new(feathered_square.outputs['Value'], compify_footage.inputs['Footage Alpha'])
    mat.node_tree.links.new(baked_lighting.outputs['Color'], compify_footage.inputs['Baked Lighting'])
    mat.node_tree.links.new(compify_footage.outputs['Shader'], output.inputs['Surface'])

    return mat


def change_footage_material_clip(config, context):
    if config.footage == None:
        return
    mat = get_compify_material(context)
    if mat != None:
        footage_node = mat.node_tree.nodes["Input Footage"]
        footage_node.image = config.footage
        footage_node.image_user.frame_duration = config.footage.frame_duration


def change_footage_camera(config, context):
    if config.camera == None or config.camera.type != 'CAMERA':
        return
    mat = get_compify_material(context)
    if mat != None:
        group = ensure_camera_project_group(config.camera)
        mat.node_tree.nodes["Camera Project"].node_tree = group


class CompifyPrepScene(bpy.types.Operator):
    """Prepares the scene for compification"""
    bl_idname = "material.compify_prep_scene"
    bl_label = "Prep Scene"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0

    def execute(self, context):
        proxy_collection = context.scene.compify_config.geo_collection
        lights_collection = context.scene.compify_config.lights_collection
        material = ensure_compify_material(context)

        # Deselect all objects.
        for obj in context.scene.objects:
            obj.select_set(False)

        # Set up proxy objects.
        for obj in proxy_collection.all_objects:
            if obj.type == 'MESH':
                # Select it.
                obj.select_set(True)
                context.view_layer.objects.active = obj

                # Ensure it has a compify UV layer and that
                # it's selected.
                if UV_LAYER_NAME not in obj.data.uv_layers:
                    obj.data.uv_layers.new(name=UV_LAYER_NAME)
                obj.data.uv_layers.active = obj.data.uv_layers[UV_LAYER_NAME]

                # Set it up with the footage material.
                obj.data.materials.clear()
                obj.data.materials.append(material)

        # UV unwrap the proxy objects.
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(
            angle_limit=(math.pi/180)*60, # 60 degrees
            island_margin=0.001,
            area_weight=0.0,
            correct_aspect=False,
            scale_to_bounds=False,
        )
        bpy.ops.object.mode_set(mode='OBJECT')

        # We have to do the UV island margins twice, because Blender's
        # `island_margin` is stupid beyond belief and corresponds to
        # nothing absolute that we can depend on.  So what we're doing
        # here is saying, "Hey, what was the actual margin achieved
        # with `island_margin=0.001`?  Okay, now let's redo it based on
        # that result."  It's still not 100% precise even with this,
        # but with a bit of buffer it's close enough.
        actual_margin = leftmost_u(context.selected_objects, UV_LAYER_NAME)
        actual_margin_pixels = actual_margin * context.scene.compify_config.bake_image_res
        target_margin_with_buffer = context.scene.compify_config.bake_uv_margin * (5.0 / 4.0)
        correction_factor = target_margin_with_buffer / actual_margin_pixels
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.select_all(action='SELECT') 
        bpy.ops.uv.pack_islands(rotate=False, margin = 0.001 * correction_factor)
        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}


class CompifyBake(bpy.types.Operator):
    """Does the Compify lighting baking for proxy geometry"""
    bl_idname = "material.compify_bake"
    bl_label = "Bake Footage Lighting"
    bl_options = {'UNDO'}

    _timer = None
    baker = None

    # Note: we use a modal technique inspired by this to keep the baking
    # from blocking the UI:
    # https://blender.stackexchange.com/questions/71454/is-it-possible-to-make-a-sequence-of-renders-and-give-the-user-the-option-to-can

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0 \
            and compify_mat_name(context) in bpy.data.materials

    def post(self, scene, context=None):
        self.baker.post(scene, context)

    def cancelled(self, scene, context=None):
        self.baker.cancelled(scene, context)

    def execute(self, context):
        self.baker = Baker()
        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return self.baker.execute(context)

    def modal(self, context, event):
        result = self.baker.modal(context, event)
        if result == {'FINISHED'} or result == {'CANCELLED'}:
            context.window_manager.event_timer_remove(self._timer)
        return result


class CompifyRender(bpy.types.Operator):
    """Render, but with Compify baking before rendering each frame"""
    bl_idname = "render.compify_render"
    bl_label = "Render Animation with Compify Integration"

    _timer = None
    render_started = False
    render_done = False
    frame_range = None
    stage = ""
    baker = None

    is_finished = False
    is_cancelled = False

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0 \
            and compify_mat_name(context) in bpy.data.materials

    def render_post_callback(self, scene, context=None):
        self.render_done = True

    def cancelled_callback(self, scene, context=None):
        self.is_cancelled = True

    def execute(self, context):
        self.render_started = False
        self.render_done = False
        self.frame_range = (context.scene.frame_start, context.scene.frame_end)
        self.stage = "bake"
        self.baker = Baker()

        self.is_finished = False
        self.is_cancelled = False

        bpy.app.handlers.render_post.append(self.render_post_callback)
        bpy.app.handlers.render_cancel.append(self.cancelled_callback)
        bpy.app.handlers.object_bake_cancel.append(self.cancelled_callback)

        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)

        context.scene.frame_set(self.frame_range[0])

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self.is_cancelled or self.is_finished:
            bpy.app.handlers.render_post.remove(self.render_post_callback)
            bpy.app.handlers.render_cancel.remove(self.cancelled_callback)
            bpy.app.handlers.object_bake_cancel.remove(self.cancelled_callback)

        if self.is_cancelled:
            return {'CANCELLED'}

        if self.is_finished:
            return {'FINISHED'}

        if event.type == 'TIMER':
            # Bake stage.
            if self.stage == "bake":
                if not self.baker.is_baking and not self.baker.is_done:
                    self.baker.execute(context)
                result = self.baker.modal(context, event)
                if result == {'FINISHED'}:
                    self.baker.reset()
                    self.stage = "render"
                else:
                    if result == {'CANCELLED'}:
                        self.is_cancelled = True
                    return result
            # Render stage.
            elif self.stage == "render":
                if not self.render_started:
                    self.render_started = True
                    bpy.ops.render.render("INVOKE_DEFAULT", animation=False)
                elif self.render_done:
                    image_path_start = bpy.path.abspath(context.scene.render.filepath)
                    image_ext = context.scene.render.file_extension
                    image_path = "{}{:04}{}".format(image_path_start, context.scene.frame_current, image_ext)
                    print("Saving image \"{}\"".format(image_path))
                    bpy.data.images['Render Result'].save_render(filepath=image_path)

                    if context.scene.frame_current >= self.frame_range[1]:
                        self.is_finished = True
                    else:
                        context.scene.frame_set(context.scene.frame_current + 1)
                        self.render_started = False
                        self.render_done = False
                        self.stage = "bake"

        return {'PASS_THROUGH'}


class CompifyAddFootageGeoCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for footage geometry"""
    bl_idname = "scene.compify_add_footage_geo_collection"
    bl_label = "Add Footage Geo Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.geo_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Footage Geo")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.geo_collection = collection
        return {'FINISHED'}


class CompifyAddFootageLightsCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for footage lights"""
    bl_idname = "scene.compify_add_footage_lights_collection"
    bl_label = "Add Footage Lights Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.lights_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Footage Lights")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.lights_collection = collection
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
        x_res = context.scene.render.resolution_x
        y_res = context.scene.render.resolution_y
        x_asp = context.scene.render.pixel_aspect_x
        y_asp = context.scene.render.pixel_aspect_y

        ensure_camera_project_group(context.active_object, (x_res * x_asp) / (y_res * y_asp))
        return {'FINISHED'}


#========================================================


class CompifyFootageConfig(bpy.types.PropertyGroup):
    footage: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Footage Texture",
        update=change_footage_material_clip,
    )
    camera: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Footage Camera",
        poll=lambda scene, obj : obj.type == 'CAMERA',
        update=change_footage_camera,
    )
    geo_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Geo Collection",
    )
    lights_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Lights Collection",
    )
    bake_uv_margin: bpy.props.IntProperty(
        name="Bake UV Margin",
        subtype='PIXEL',
        options=set(), # Not animatable.
        default=4,
        min=0,
        max=2**16,
        soft_max=32,
    )
    bake_image_res: bpy.props.IntProperty(
        name="Bake Resolution",
        subtype='PIXEL',
        options=set(), # Not animatable.
        default=1024,
        min=64,
        max=2**16,
        soft_max=8192,
    )


#========================================================


def register():
    bpy.utils.register_class(CompifyPanel)
    bpy.utils.register_class(CompifyCameraPanel)
    bpy.utils.register_class(CompifyAddFootageGeoCollection)
    bpy.utils.register_class(CompifyAddFootageLightsCollection)
    bpy.utils.register_class(CompifyPrepScene)
    bpy.utils.register_class(CompifyBake)
    bpy.utils.register_class(CompifyRender)
    bpy.utils.register_class(CompifyCameraProjectGroupNew)
    bpy.utils.register_class(CompifyFootageConfig)

    # Custom properties.
    bpy.types.Scene.compify_config = bpy.props.PointerProperty(type=CompifyFootageConfig)

    # Other modules.
    camera_align_register()

def unregister():
    bpy.utils.unregister_class(CompifyPanel)
    bpy.utils.unregister_class(CompifyCameraPanel)
    bpy.utils.unregister_class(CompifyAddFootageGeoCollection)
    bpy.utils.unregister_class(CompifyAddFootageLightsCollection)
    bpy.utils.unregister_class(CompifyPrepScene)
    bpy.utils.unregister_class(CompifyBake)
    bpy.utils.unregister_class(CompifyRender)
    bpy.utils.unregister_class(CompifyCameraProjectGroupNew)
    bpy.utils.unregister_class(CompifyFootageConfig)

    # Custom properties.
    del bpy.types.Scene.compify_config

    # Other modules.
    camera_align_unregister()


if __name__ == "__main__":
    register()
