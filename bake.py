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

class Baker:
    def __init__(self):
        self.is_baking = False
        self.is_done = False
        self.proxy_objects = []
        self.hide_render_list = {}
        self.main_node = None

    def post(self, scene, context=None):
        self.is_baking = False
        self.is_done = True

    def cancelled(self, scene, context=None):
        self.is_baking = False
        self.is_done = True

    def execute(self, context):
        # Misc setup and checks.
        if context.scene.compify_config.geo_collection == None:
            return {'CANCELLED'}
        self.proxy_objects = context.scene.compify_config.geo_collection.objects
        proxy_lights = []
        if context.scene.compify_config.lights_collection != None:
            proxy_lights = context.scene.compify_config.lights_collection.objects
        material = bpy.data.materials[compify_mat_name(context)]
        self.main_node = material.node_tree.nodes[MAIN_NODE_NAME]
        delight_image_node = material.node_tree.nodes[BAKE_IMAGE_NODE_NAME]

        if len(self.proxy_objects) == 0:
            return {'CANCELLED'}

        # Ensure we have an image of the right resolution to bake to.
        bake_image_name = compify_baked_texture_name(context)
        bake_res = context.scene.compify_config.bake_image_res
        if bake_image_name in bpy.data.images \
        and bpy.data.images[bake_image_name].resolution[0] != bake_res:
            bpy.data.images.remove(bpy.data.images[bake_image_name])

        bake_image = None
        if bake_image_name in bpy.data.images:
            bake_image = bpy.data.images[bake_image_name]
        else:
            bake_image = bpy.data.images.new(
                bake_image_name,
                bake_res, bake_res,
                alpha=False,
                float_buffer=True,
                stereo3d=False,
                is_data=False,
                tiled=False,
            )
        delight_image_node.image = bake_image

        # Configure the material for baking mode.
        self.main_node.inputs["Do Bake"].default_value = 1.0
        self.main_node.inputs["Debug"].default_value = 0.0
        delight_image_node.select = True
        material.node_tree.nodes.active = delight_image_node

        # Deselect everything.
        for obj in context.scene.objects:
            obj.select_set(False)

        # Build a dictionary of the visibility of non-proxy objects so that
        # we can restore it afterwards.
        for obj in context.scene.objects:
            if obj.name not in self.proxy_objects and obj.name not in proxy_lights:
                self.hide_render_list[obj.name] = obj.hide_render

        # Make all non-proxy objects invisible.
        for obj_name in self.hide_render_list:
            bpy.data.objects[obj_name].hide_render = True

        # Set up the baking job event handlers.
        bpy.app.handlers.object_bake_complete.append(self.post)
        bpy.app.handlers.object_bake_cancel.append(self.cancelled)

        return {'RUNNING_MODAL'}


    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self.is_baking and not self.is_done:
                self.is_baking = True

                # Select objects for baking.
                for obj in self.proxy_objects:
                    obj.select_set(True)
                context.view_layer.objects.active = self.proxy_objects[0]

                # Do the bake.
                bpy.ops.object.bake(
                    "INVOKE_DEFAULT",
                    type='DIFFUSE',
                    pass_filter={'DIRECT', 'INDIRECT', 'COLOR'},
                    # filepath='',
                    # width=512,
                    # height=512,
                    margin=context.scene.compify_config.bake_uv_margin,
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
            elif self.is_done:
                # Clean up the handlers and timer.
                bpy.app.handlers.object_bake_complete.remove(self.post)
                bpy.app.handlers.object_bake_cancel.remove(self.cancelled)
                self._timer = None

                # Restore visibility of non-proxy objects.
                for obj_name in self.hide_render_list:
                    bpy.data.objects[obj_name].hide_render = self.hide_render_list[obj_name]
                self.hide_render_list = {}

                # Set material to non-bake mode.
                self.main_node.inputs["Do Bake"].default_value = 0.0
                self.main_node = None

                # Reset other self properties.
                self.is_baking = False
                self.is_done = False
                self.proxy_objects = []

                return {'FINISHED'}

        return {'PASS_THROUGH'}


    def reset(self):
        self.is_baking = False
        self.is_done = False
