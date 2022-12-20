import bpy


class CompifyCameraAlignPanel(bpy.types.Panel):
    """Align multiple tracked cameras to each other."""
    bl_label = "Align Cameras"
    bl_idname = "DATA_PT_compify_camera_align"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

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

            row = col.row()
            row.prop(point, "scene_point", text="Target Point")
            row.operator("scene.compify_align_set_scene_point_to_cursor", text="", icon="CURSOR")

            col.separator(factor=2.0)

            row = col.row()
            row.prop(point, "track_point", text="Tracker")
            row.operator("scene.compify_align_set_track_point_to_cursor", text="", icon="CURSOR")

        col = layout.column()
        col.separator(factor=2.0)

        col.operator("scene.compify_camera_align_transform")


class OBJECT_UL_compify_camera_align_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(text=item.name)
            row.label(text="{:.2f}".format(item.scene_point[0]))
            row.label(text="{:.2f}".format(item.scene_point[1]))
            row.label(text="{:.2f}".format(item.scene_point[2]))
        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


#========================================================

class CompifyCameraAlignTransform(bpy.types.Operator):
    """Transforms the active object to move the specified track points to the specified target points"""
    bl_idname = "scene.compify_camera_align_transform"
    bl_label = "Align Transform"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object != None and len(context.scene.compify_align_points) >= 3

    def execute(self, context):
        obj = context.active_object
        align_points = context.scene.compify_align_points

        # TODO: the actual alignment math.

        # Set the track points to be equal to the scene points, so
        # double-tapping the align button doesn't un-align after
        # aligning.
        for point in align_points:
            point.track_point[0] = point.scene_point[0]
            point.track_point[1] = point.scene_point[1]
            point.track_point[2] = point.scene_point[2]

        return {'FINISHED'}


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


class CompifyAlignSetScenePointToCursor(bpy.types.Operator):
    """Sets the target point to the current 3D cursor position"""
    bl_idname = "scene.compify_align_set_scene_point_to_cursor"
    bl_label = "Set target to 3D cursor"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_align_points_active_index < len(context.scene.compify_align_points)

    def execute(self, context):
        align_point = context.scene.compify_align_points[context.scene.compify_align_points_active_index]
        align_point.scene_point[0] = context.scene.cursor.location[0]
        align_point.scene_point[1] = context.scene.cursor.location[1]
        align_point.scene_point[2] = context.scene.cursor.location[2]
        return {'FINISHED'}


class CompifyAlignSetTrackPointToCursor(bpy.types.Operator):
    """Sets the tracking point to the current 3D cursor position"""
    bl_idname = "scene.compify_align_set_track_point_to_cursor"
    bl_label = "Set track point to 3D cursor"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_align_points_active_index < len(context.scene.compify_align_points)

    def execute(self, context):
        align_point = context.scene.compify_align_points[context.scene.compify_align_points_active_index]
        align_point.track_point[0] = context.scene.cursor.location[0]
        align_point.track_point[1] = context.scene.cursor.location[1]
        align_point.track_point[2] = context.scene.cursor.location[2]
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
    bpy.utils.register_class(CompifyAlignSetScenePointToCursor)
    bpy.utils.register_class(CompifyAlignSetTrackPointToCursor)
    bpy.utils.register_class(CompifyCameraAlignTransform)

    bpy.types.Scene.compify_align_points = bpy.props.CollectionProperty(type=CompifyAlignPoint)
    bpy.types.Scene.compify_align_points_active_index = bpy.props.IntProperty(name="Align Points List Active Item Index")

def camera_align_unregister():
    bpy.utils.unregister_class(CompifyCameraAlignPanel)
    bpy.utils.unregister_class(CompifyAlignPoint)
    bpy.utils.unregister_class(OBJECT_UL_compify_camera_align_items)
    bpy.utils.unregister_class(CompifyAlignPointAdd)
    bpy.utils.unregister_class(CompifyAlignPointRemove)
    bpy.utils.unregister_class(CompifyAlignPointMove)
    bpy.utils.unregister_class(CompifyAlignSetScenePointToCursor)
    bpy.utils.unregister_class(CompifyAlignSetTrackPointToCursor)
    bpy.utils.unregister_class(CompifyCameraAlignTransform)

    del bpy.types.Scene.compify_align_points
    del bpy.types.Scene.compify_align_points_active_index
