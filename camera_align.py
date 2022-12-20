import bpy


class CompifyCameraAlignPanel(bpy.types.Panel):
    """Align multiple tracked cameras to each other."""
    bl_label = "Align Cameras"
    bl_idname = "DATA_PT_compify_camera_align"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        scene = context.scene

        row = layout.row()
        row.template_list(
            listtype_name="OBJECT_UL_compify_camera_align_items",
            list_id="",
            dataptr=scene,
            propname="compify_align_points",
            active_dataptr=scene,
            active_propname="compify_align_points_active_index",
        )
        col = row.column()
        col.operator("scene.compify_align_point_add", text="", icon='ADD')
        col.operator("scene.compify_align_point_remove", text="", icon='REMOVE')
        col.operator("scene.compify_align_point_move", text="", icon='TRIA_UP').type = 'UP'
        col.operator("scene.compify_align_point_move", text="", icon='TRIA_DOWN').type = 'DOWN'

        if scene.compify_align_points_active_index < len(scene.compify_align_points):
            point = scene.compify_align_points[scene.compify_align_points_active_index]
            col = layout.column()
            col.prop(point, "name")
            col.row().prop(point, "scene_point")
            col.row().prop(point, "track_point")

        # col.separator(factor=2.0)

        # row = layout.row()
        # row.alignment = 'LEFT'
        # header_text = "Misc Utilties"
        # if wm.camera_shake_show_utils:
        #     row.prop(wm, "camera_shake_show_utils", icon="DISCLOSURE_TRI_DOWN", text=header_text, expand=False, emboss=False)
        # else:
        #     row.prop(wm, "camera_shake_show_utils", icon="DISCLOSURE_TRI_RIGHT", text=header_text, emboss=False)
        # row.separator_spacer()

        # col = layout.column()
        # if wm.camera_shake_show_utils:
        #     col.operator("object.camera_shakes_fix_global")


class OBJECT_UL_compify_camera_align_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(text=item.name)
            row.prop(item, "scene_point", text="")
        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


#========================================================


class CompifyAlignPointAdd(bpy.types.Operator):
    """Adds an alignment point"""
    bl_idname = "scene.compify_align_point_add"
    bl_label = "Add Alignment Point"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        point = scene.compify_align_points.add()
        point.name = "Point {}".format(len(scene.compify_align_points))
        scene.compify_align_points_active_index = len(scene.compify_align_points) - 1
        return {'FINISHED'}


class CompifyAlignPointRemove(bpy.types.Operator):
    """Removes an alignment point"""
    bl_idname = "scene.compify_align_point_remove"
    bl_label = "Remove Alignment Point"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.compify_align_points) > 0

    def execute(self, context):
        scene = context.scene
        if scene.compify_align_points_active_index < len(scene.compify_align_points):
            scene.compify_align_points.remove(scene.compify_align_points_active_index)
            if scene.compify_align_points_active_index >= len(scene.compify_align_points) and scene.compify_align_points_active_index > 0:
                scene.compify_align_points_active_index -= 1
        return {'FINISHED'}


class CompifyAlignPointMove(bpy.types.Operator):
    """Moves an alignment point's order in the list"""
    bl_idname = "scene.compify_align_point_move"
    bl_label = "Move Alignment Point"
    bl_options = {'UNDO'}

    type: bpy.props.EnumProperty(items = [
        ('UP', "", ""),
        ('DOWN', "", ""),
    ])

    @classmethod
    def poll(cls, context):
        return len(context.scene.compify_align_points) > 1

    def execute(self, context):
        scene = context.scene
        index = int(scene.compify_align_points_active_index)
        if self.type == 'UP' and index > 0:
            scene.compify_align_points.move(index, index - 1)
            scene.compify_align_points_active_index -= 1
        elif self.type == 'DOWN' and (index + 1) < len(scene.compify_align_points):
            scene.compify_align_points.move(index, index + 1)
            scene.compify_align_points_active_index += 1
        return {'FINISHED'}

#========================================================


class CompifyAlignPoint(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name",
        default="",
    )
    scene_point: bpy.props.FloatVectorProperty(
        name="Scene Point",
        options=set(), # Not animatable.
        default=(0.0, 0.0, 0.0),
    )
    track_point: bpy.props.FloatVectorProperty(
        name="Track Point",
        options=set(), # Not animatable.
        default=(0.0, 0.0, 0.0),
    )


#========================================================


def camera_align_register():
    bpy.utils.register_class(CompifyCameraAlignPanel)
    bpy.utils.register_class(CompifyAlignPoint)
    bpy.utils.register_class(OBJECT_UL_compify_camera_align_items)
    bpy.utils.register_class(CompifyAlignPointAdd)
    bpy.utils.register_class(CompifyAlignPointRemove)
    bpy.utils.register_class(CompifyAlignPointMove)
    bpy.types.Scene.compify_align_points = bpy.props.CollectionProperty(type=CompifyAlignPoint)
    bpy.types.Scene.compify_align_points_active_index = bpy.props.IntProperty(name="Align Points List Active Item Index")

def camera_align_unregister():
    bpy.utils.unregister_class(CompifyCameraAlignPanel)
    bpy.utils.unregister_class(CompifyAlignPoint)
    bpy.utils.unregister_class(OBJECT_UL_compify_camera_align_items)
    bpy.utils.unregister_class(CompifyAlignPointAdd)
    bpy.utils.unregister_class(CompifyAlignPointRemove)
    bpy.utils.unregister_class(CompifyAlignPointMove)
    del bpy.types.Scene.compify_align_points
    del bpy.types.Scene.compify_align_points_active_index
