import bpy
import math

def hide_sockets(node):
    for input in node.inputs:
        input.hide = True
    for output in node.outputs:
        output.hide = True

# Ensures that the Compify Footage shader group exists.
#
# It will create it if it doesn't exist, and returns the group.
def ensure_footage_group():
    NAME = "Compify Footage"
    if NAME in bpy.data.node_groups:
        return bpy.data.node_groups[NAME]

    # Create the group.
    group = bpy.data.node_groups.new(NAME, type='ShaderNodeTree')
    for node in group.nodes:
        group.nodes.remove(node)

    # Create the group inputs and outputs.
    socket = group.interface.new_socket(name="Footage", socket_type="NodeSocketColor", in_out='INPUT')
    socket.default_value = (1.0, 0.0, 1.0, 1.0)
    socket.hide_value = True

    socket = group.interface.new_socket(name="Footage Alpha", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 1.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    socket = group.interface.new_socket(name="Footage Emit", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    socket = group.interface.new_socket(name="Background", socket_type="NodeSocketColor", in_out='INPUT')
    socket.default_value = (1.0, 0.0, 1.0, 1.0)
    socket.hide_value = True

    socket = group.interface.new_socket(name="Background Alpha", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    socket = group.interface.new_socket(name="Background Emit", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    socket = group.interface.new_socket(name="Baked Lighting", socket_type="NodeSocketColor", in_out='INPUT')
    socket.default_value = (1.0, 1.0, 1.0, 1.0)
    socket.hide_value = True

    socket = group.interface.new_socket(name="Do Bake", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    socket = group.interface.new_socket(name="Debug", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0

    group.interface.new_socket(name="Shader", socket_type="NodeSocketShader", in_out='OUTPUT')

    #-------------------
    # Footage nodes.

    # Create the nodes.
    footage_frame = group.nodes.new(type='NodeFrame')
    footage_input = group.nodes.new(type='NodeGroupInput')
    footage_debug = group.nodes.new(type='ShaderNodeMath')
    footage_delight = group.nodes.new(type='ShaderNodeMixRGB')
    footage_1 = group.nodes.new(type='ShaderNodeBsdfDiffuse')
    footage_2 = group.nodes.new(type='ShaderNodeMixShader')

    # Label the nodes.
    footage_frame.label = "Footage"
    footage_input.label = "Footage Input"
    footage_debug.label = "Footage Debug"
    footage_delight.label = "Footage Delight"
    footage_1.label = "Footage 1"
    footage_2.label = "Footage 2"

    # Put the nodes in their frame.
    footage_input.parent = footage_frame
    footage_debug.parent = footage_frame
    footage_delight.parent = footage_frame
    footage_1.parent = footage_frame
    footage_2.parent = footage_frame

    # Position the nodes.
    hs = 200.0
    x = 200.0
    y = -330.0

    footage_input.location = (x, y)
    x += hs
    footage_delight.location = (x, y)
    footage_debug.location = (x, y + 50.0)
    x += hs
    footage_1.location = (x, y)
    x += hs
    footage_2.location = (x, y)

    # Configure the nodes.
    for socket in footage_input.outputs:
        socket.hide = True
    footage_input.outputs["Footage"].hide = False
    footage_input.outputs["Footage Emit"].hide = False
    footage_input.outputs["Baked Lighting"].hide = False
    footage_input.outputs["Do Bake"].hide = False

    footage_delight.blend_type = 'DIVIDE'
    footage_delight.use_clamp = False
    footage_delight.inputs[0].default_value = 1.0

    footage_1.inputs['Roughness'].default_value = 0.0
    footage_1.hide = True

    footage_debug.operation = 'MAXIMUM'
    footage_debug.use_clamp = True
    footage_debug.hide = True

    # Hook up the nodes.
    group.links.new(footage_input.outputs['Footage'], footage_delight.inputs['Color1'])
    group.links.new(footage_input.outputs['Footage'], footage_2.inputs[2])
    group.links.new(footage_input.outputs['Footage Emit'], footage_debug.inputs[0])
    group.links.new(footage_input.outputs['Baked Lighting'], footage_delight.inputs['Color2'])
    group.links.new(footage_input.outputs['Do Bake'], footage_debug.inputs[1])
    group.links.new(footage_delight.outputs['Color'], footage_1.inputs['Color'])
    group.links.new(footage_1.outputs['BSDF'], footage_2.inputs[1])
    group.links.new(footage_debug.outputs['Value'], footage_2.inputs['Fac'])

    #-------------------
    # Background nodes.

    # Create the nodes.
    background_frame = group.nodes.new(type='NodeFrame')
    background_input = group.nodes.new(type='NodeGroupInput')
    background_debug = group.nodes.new(type='ShaderNodeMath')
    background_delight = group.nodes.new(type='ShaderNodeMixRGB')
    background_transparent = group.nodes.new(type='ShaderNodeBsdfTransparent')
    background_1 = group.nodes.new(type='ShaderNodeBsdfDiffuse')
    background_2 = group.nodes.new(type='ShaderNodeMixShader')
    background_3 = group.nodes.new(type='ShaderNodeMixShader')

    # Label the nodes.
    background_frame.label = "Background"
    background_input.label = "Background Input"
    background_debug.label = "Background Debug"
    background_delight.label = "Background Delight"
    background_transparent.label = "Background Transparent"
    background_1.label = "Background 1"
    background_2.label = "Background 2"
    background_3.label = "Background 3"

    # Put the nodes in their frame.
    background_input.parent = background_frame
    background_debug.parent = background_frame
    background_delight.parent = background_frame
    background_transparent.parent = background_frame
    background_1.parent = background_frame
    background_2.parent = background_frame
    background_3.parent = background_frame

    # Position the nodes.
    hs = 200.0
    x = 0.0
    y = 0.0

    background_input.location = (x, y)
    x += hs
    background_delight.location = (x, y)
    background_debug.location = (x, y + 80.0)
    x += hs
    background_1.location = (x, y + 30)
    x += hs
    background_transparent.location = (x, y - 80.0)
    background_2.location = (x, y + 100.0)
    x += hs
    background_3.location = (x, y)

    # Configure the nodes.
    for socket in background_input.outputs:
        socket.hide = True
    background_input.outputs["Background"].hide = False
    background_input.outputs["Background Alpha"].hide = False
    background_input.outputs["Background Emit"].hide = False
    background_input.outputs["Baked Lighting"].hide = False
    background_input.outputs["Do Bake"].hide = False

    background_delight.blend_type = 'DIVIDE'
    background_delight.use_clamp = False
    background_delight.inputs[0].default_value = 1.0

    background_transparent.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

    background_1.inputs['Roughness'].default_value = 0.0
    background_1.hide = True

    background_debug.operation = 'MAXIMUM'
    background_debug.use_clamp = True
    background_debug.hide = True

    # Hook up the nodes.
    group.links.new(background_input.outputs['Background'], background_delight.inputs['Color1'])
    group.links.new(background_input.outputs['Background'], background_2.inputs[2])
    group.links.new(background_input.outputs['Background Alpha'], background_3.inputs['Fac'])
    group.links.new(background_input.outputs['Background Emit'], background_debug.inputs[0])
    group.links.new(background_input.outputs['Baked Lighting'], background_delight.inputs['Color2'])
    group.links.new(background_input.outputs['Do Bake'], background_debug.inputs[1])
    group.links.new(background_delight.outputs['Color'], background_1.inputs['Color'])
    group.links.new(background_1.outputs['BSDF'], background_2.inputs[1])
    group.links.new(background_debug.outputs['Value'], background_2.inputs['Fac'])
    group.links.new(background_transparent.outputs['BSDF'], background_3.inputs[1])
    group.links.new(background_2.outputs['Shader'], background_3.inputs[2])

    #-------------------
    # Camera Ray nodes.

    # Create the nodes.
    camera_ray_frame = group.nodes.new(type='NodeFrame')
    camera_input = group.nodes.new(type='NodeGroupInput')
    light_path = group.nodes.new(type='ShaderNodeLightPath')
    debug_invert = group.nodes.new(type='ShaderNodeMath')
    camera_ray = group.nodes.new(type='ShaderNodeMath')

    # Label the nodes.
    camera_ray_frame.label = "Camera Ray"
    camera_input.label = "Camera Input"
    light_path.label = "Light Path"
    debug_invert.label = "Debug Invert"
    camera_ray.label = "Camera Ray"

    # Put the nodes in their frame.
    camera_input.parent = camera_ray_frame
    light_path.parent = camera_ray_frame
    debug_invert.parent = camera_ray_frame
    camera_ray.parent = camera_ray_frame

    # Position the nodes.
    hs = 200.0
    x = 400.0
    y = 260.0

    camera_input.location = (x, y)
    x += hs
    light_path.location = (x, y)
    debug_invert.location = (x, y + 50.0)
    x += hs
    camera_ray.location = (x, y)

    # Configure the nodes.
    for socket in camera_input.outputs:
        socket.hide = True
    camera_input.outputs["Debug"].hide = False

    for socket in light_path.outputs:
        socket.hide = True
    light_path.outputs["Is Camera Ray"].hide = False

    debug_invert.operation = 'MULTIPLY_ADD'
    debug_invert.use_clamp = True
    debug_invert.inputs[1].default_value = -1.0
    debug_invert.inputs[2].default_value = 1.0
    debug_invert.hide = True

    camera_ray.operation = 'MINIMUM'
    camera_ray.use_clamp = True
    camera_ray.hide = True

    # Hook up the nodes.
    group.links.new(camera_input.outputs['Debug'], debug_invert.inputs['Value'])
    group.links.new(light_path.outputs['Is Camera Ray'], camera_ray.inputs[0])
    group.links.new(debug_invert.outputs['Value'], camera_ray.inputs[1])

    #---------------
    # Baking nodes.

    # Create the nodes.
    baking_frame = group.nodes.new(type='NodeFrame')
    baking_input = group.nodes.new(type='NodeGroupInput')
    baking_transparent = group.nodes.new(type='ShaderNodeBsdfTransparent')
    baking_diffuse = group.nodes.new(type='ShaderNodeBsdfDiffuse')
    baking_1 = group.nodes.new(type='ShaderNodeMixShader')
    baking_2 = group.nodes.new(type='ShaderNodeMixShader')
    baking_3 = group.nodes.new(type='ShaderNodeMixShader')

    # Label the nodes.
    baking_frame.label = "Baking"
    baking_input.label = "Baking Input"
    baking_transparent.label = "Baking Transparent"
    baking_diffuse.label = "Baking Diffuse"
    baking_1.label = "Baking 1"
    baking_2.label = "Baking 2"
    baking_3.label = "Baking 3"

    # Put the nodes in their frame.
    baking_input.parent = baking_frame
    baking_transparent.parent = baking_frame
    baking_diffuse.parent = baking_frame
    baking_1.parent = baking_frame
    baking_2.parent = baking_frame
    baking_3.parent = baking_frame

    # Position the nodes.
    hs = 200.0
    x = 850.0
    y = 700.0

    x += hs
    baking_transparent.location = (x, y)
    baking_input.location = (x, y - 140.0)

    x += hs
    baking_1.location = (x, y)

    x += hs
    baking_2.location = (x, y)
    baking_diffuse.location = (x, y - 140.0)

    x += hs
    baking_3.location = (x, y)

    # Configure the nodes.
    for socket in baking_input.outputs:
        socket.hide = True
    baking_input.outputs["Footage"].hide = False
    baking_input.outputs["Background"].hide = False
    baking_input.outputs["Background Alpha"].hide = False
    baking_input.outputs["Footage Alpha"].hide = False

    baking_transparent.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

    baking_diffuse.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    baking_diffuse.inputs['Roughness'].default_value = 0.0

    # Hook up the nodes.
    group.links.new(baking_transparent.outputs['BSDF'], baking_1.inputs[1])
    group.links.new(baking_input.outputs['Footage'], baking_2.inputs[2])
    group.links.new(baking_input.outputs['Background'], baking_1.inputs[2])
    group.links.new(baking_input.outputs['Background Alpha'], baking_1.inputs['Fac'])
    group.links.new(baking_input.outputs['Footage Alpha'], baking_2.inputs['Fac'])
    group.links.new(baking_1.outputs['Shader'], baking_2.inputs[1])
    group.links.new(baking_2.outputs['Shader'], baking_3.inputs[1])
    group.links.new(baking_diffuse.outputs['BSDF'], baking_3.inputs[2])

    #----------------------
    # The remaining nodes.

    # Create the nodes.
    mix_input = group.nodes.new(type='NodeGroupInput')
    background_mask = group.nodes.new(type='ShaderNodeMixShader')
    backfacing1_mask = group.nodes.new(type='ShaderNodeMixShader')
    backfacing1_geo = group.nodes.new(type='ShaderNodeNewGeometry')
    hide_sockets(backfacing1_geo)
    backfacing1_shader = group.nodes.new(type='ShaderNodeBsdfTransparent')
    camera_switch = group.nodes.new(type='ShaderNodeMixShader')
    bake_switch = group.nodes.new(type='ShaderNodeMixShader')
    backfacing2_mask = group.nodes.new(type='ShaderNodeMixShader')
    backfacing2_geo = group.nodes.new(type='ShaderNodeNewGeometry')
    hide_sockets(backfacing2_geo)
    backfacing2_shader = group.nodes.new(type='ShaderNodeBsdfTransparent')
    output = group.nodes.new(type='NodeGroupOutput')

    # Label the nodes.
    mix_input.label = "Mix Input"
    background_mask.label = "Background Mask"
    backfacing1_mask.label = "Backfacing Mask"
    backfacing2_mask.label = "Backfacing Mask"
    camera_switch.label = "Camera Switch"
    bake_switch.label = "Bake Switch"

    # Position the nodes.
    hs = 200.0
    x = 1200.0
    y = 300.0

    mix_input.location = (x, y)

    x += hs
    background_mask.location = (x, y - 200.0)
    backfacing1_geo.location = (x, y - 450)
    backfacing1_shader.location = (x, y - 550)

    x += hs
    backfacing1_mask.location = (x, y - 450)

    x += hs
    camera_switch.location = (x, y - 200.0)

    x += 50.0
    y = 600.0
    backfacing2_geo.location = (x, y)
    backfacing2_shader.location = (x, y - 100)

    x += hs
    backfacing2_mask.location = (x, y)

    x += hs
    y = 300.0
    bake_switch.location = (x, y)

    x += hs
    output.location = (x, y)

    # Configure the nodes.
    for socket in mix_input.outputs:
        socket.hide = True
    mix_input.outputs["Footage Alpha"].hide = False
    mix_input.outputs["Do Bake"].hide = False

    # Hook up the nodes.
    group.links.new(mix_input.outputs['Footage Alpha'], background_mask.inputs['Fac'])
    group.links.new(mix_input.outputs['Do Bake'], bake_switch.inputs['Fac'])
    group.links.new(backfacing1_geo.outputs['Backfacing'], backfacing1_mask.inputs['Fac'])
    group.links.new(background_mask.outputs['Shader'], backfacing1_mask.inputs[1])
    group.links.new(backfacing1_shader.outputs[0], backfacing1_mask.inputs[2])
    group.links.new(backfacing1_mask.outputs['Shader'], camera_switch.inputs[1])
    group.links.new(camera_switch.outputs['Shader'], bake_switch.inputs[1])
    group.links.new(bake_switch.outputs['Shader'], output.inputs['Shader'])
    group.links.new(backfacing2_geo.outputs['Backfacing'], backfacing2_mask.inputs['Fac'])
    group.links.new(backfacing2_shader.outputs[0], backfacing2_mask.inputs[2])

    #-------------------------------------------------
    # Final hook up of all the groups of nodes above.

    group.links.new(camera_ray.outputs['Value'], baking_3.inputs['Fac'])
    group.links.new(camera_ray.outputs['Value'], camera_switch.inputs['Fac'])
    group.links.new(background_3.outputs['Shader'], background_mask.inputs[1])
    group.links.new(footage_2.outputs['Shader'], background_mask.inputs[2])
    group.links.new(footage_2.outputs['Shader'], camera_switch.inputs[2])
    group.links.new(baking_3.outputs['Shader'], backfacing2_mask.inputs[1])
    group.links.new(backfacing2_mask.outputs['Shader'], bake_switch.inputs[2])

    return group


# Ensures that the Feathered Square shader group exists.
#
# It will create it if it doesn't exist, and returns the group.
def ensure_feathered_square_group():
    NAME = "Feathered Square"
    
    # If it already exists, just return it.
    if NAME in bpy.data.node_groups:
        return bpy.data.node_groups[NAME]

    # Create the group.
    group = bpy.data.node_groups.new(NAME, type='ShaderNodeTree')
    for node in group.nodes:
        group.nodes.remove(node)
    
    # Create the group inputs and outputs.
    group.interface.new_socket(name="Vector", socket_type="NodeSocketVector", in_out='INPUT')
    
    socket = group.interface.new_socket(name="Feather", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 1.0
    
    socket = group.interface.new_socket(name="Dilate", socket_type="NodeSocketFloat", in_out='INPUT')
    socket.default_value = 0.0
    socket.min_value = 0.0
    socket.max_value = 0.1
    
    group.interface.new_socket(name="Value", socket_type="NodeSocketFloat", in_out='OUTPUT')

    #-------------------
    # Create the nodes.
    input = group.nodes.new(type='NodeGroupInput')
    output = group.nodes.new(type='NodeGroupOutput')
    
    xyz = group.nodes.new(type='ShaderNodeSeparateXYZ')
    feather_clamp = group.nodes.new(type='ShaderNodeMath')
    
    madd_x = group.nodes.new(type='ShaderNodeMath')
    madd_y = group.nodes.new(type='ShaderNodeMath')
    
    abs_x = group.nodes.new(type='ShaderNodeMath')
    abs_y = group.nodes.new(type='ShaderNodeMath')
    
    xy_max = group.nodes.new(type='ShaderNodeMath')
    xy_invert = group.nodes.new(type='ShaderNodeMath')
    xy_add = group.nodes.new(type='ShaderNodeMath')
    xy_divide = group.nodes.new(type='ShaderNodeMath')
    
    smoothstep1 = group.nodes.new(type='ShaderNodeMath')
    smoothstep2 = group.nodes.new(type='ShaderNodeMath')
    smoothstep3 = group.nodes.new(type='ShaderNodeMath')
    smoothstep4 = group.nodes.new(type='ShaderNodeMath')
    smoothstep5 = group.nodes.new(type='ShaderNodeMath')
    
    #------------------
    # Label the nodes.
    xyz.label = "XYZ"
    feather_clamp.label = "Feather Clamp"
    
    madd_x.label = "Multiply-Add X"
    madd_y.label = "Multiply-Add Y"
    
    abs_x.label = "Abs X"
    abs_y.label = "Abs Y"
    
    xy_max.label = "XY Max"
    xy_invert.label = "XY Invert"
    xy_add.label = "XY Add"
    xy_divide.label = "XY Divide"
    
    smoothstep1.label = "Smoothstep 1"
    smoothstep2.label = "Smoothstep 2"
    smoothstep3.label = "Smoothstep 3"
    smoothstep4.label = "Smoothstep 4"
    smoothstep5.label = "Smoothstep 5"

    #---------------------
    # Position the nodes.
    hs = 250.0
    x = 0.0
    
    input.location = (x, 0.0)
    
    x += hs
    xyz.location = (x, 0.0)
    feather_clamp.location = (x, -200.0)
    
    x += hs
    madd_x.location = (x, 0.0)
    madd_y.location = (x, -200.0)
    
    x += hs
    abs_x.location = (x, 0.0)
    abs_y.location = (x, -200.0)
    
    x += hs
    xy_max.location = (x, 0.0)
    
    x += hs
    xy_invert.location = (x, 0.0)
    
    x += hs
    xy_add.location = (x, 0.0)
    
    x += hs
    xy_divide.location = (x, 0.0)
    
    x += hs
    smoothstep1.location = (x, 0.0)
    
    x += hs
    smoothstep2.location = (x, -200.0)
    
    x += hs
    smoothstep3.location = (x, 0.0)
    smoothstep4.location = (x, -200.0)
    
    x += hs
    smoothstep5.location = (x, 0.0)
    
    x += hs
    output.location = (x, 0.0)

    #----------------------
    # Configure the nodes.
    feather_clamp.operation = 'MAXIMUM'
    feather_clamp.use_clamp = False
    feather_clamp.inputs[1].default_value = 0.000001

    madd_x.operation = 'MULTIPLY_ADD'
    madd_x.use_clamp = False
    madd_x.inputs[1].default_value = 2.0
    madd_x.inputs[2].default_value = -1.0
    madd_y.operation = 'MULTIPLY_ADD'
    madd_y.use_clamp = False
    madd_y.inputs[1].default_value = 2.0
    madd_y.inputs[2].default_value = -1.0
    
    abs_x.operation = 'ABSOLUTE'
    abs_x.use_clamp = False
    abs_y.operation = 'ABSOLUTE'
    abs_y.use_clamp = False
    
    xy_max.operation = 'MAXIMUM'
    xy_max.use_clamp = False
    xy_invert.operation = 'MULTIPLY_ADD'
    xy_invert.use_clamp = False
    xy_invert.inputs[1].default_value = -1.0
    xy_invert.inputs[2].default_value = 1.0
    xy_add.operation = 'ADD'
    xy_add.use_clamp = False
    xy_divide.operation = 'DIVIDE'
    xy_divide.use_clamp = True
    
    smoothstep1.operation = 'MULTIPLY'
    smoothstep1.use_clamp = False
    smoothstep2.operation = 'MULTIPLY'
    smoothstep2.use_clamp = False
    smoothstep3.operation = 'MULTIPLY'
    smoothstep3.use_clamp = False
    smoothstep3.inputs[1].default_value = 3.0
    smoothstep4.operation = 'MULTIPLY'
    smoothstep4.use_clamp = False
    smoothstep4.inputs[1].default_value = 2.0
    smoothstep5.operation = 'SUBTRACT'
    smoothstep5.use_clamp = True

    #--------------------
    # Hook up the nodes.
    group.links.new(input.outputs['Vector'], xyz.inputs[0])
    group.links.new(input.outputs['Feather'], feather_clamp.inputs[0])
    group.links.new(input.outputs['Dilate'], xy_add.inputs[1])
    
    group.links.new(xyz.outputs['X'], madd_x.inputs[0])
    group.links.new(xyz.outputs['Y'], madd_y.inputs[0])
    group.links.new(feather_clamp.outputs[0], xy_divide.inputs[1])
    
    group.links.new(madd_x.outputs[0], abs_x.inputs[0])
    group.links.new(madd_y.outputs[0], abs_y.inputs[0])
    
    group.links.new(abs_x.outputs[0], xy_max.inputs[0])
    group.links.new(abs_y.outputs[0], xy_max.inputs[1])
    
    group.links.new(xy_max.outputs[0], xy_invert.inputs['Value'])
    
    group.links.new(xy_invert.outputs[0], xy_add.inputs[0])
    
    group.links.new(xy_add.outputs[0], xy_divide.inputs[0])
    
    group.links.new(xy_divide.outputs[0], smoothstep1.inputs[0])
    group.links.new(xy_divide.outputs[0], smoothstep1.inputs[1])
    group.links.new(xy_divide.outputs[0], smoothstep2.inputs[1])
    group.links.new(smoothstep1.outputs[0], smoothstep2.inputs[0])
    
    group.links.new(smoothstep1.outputs[0], smoothstep3.inputs[0])
    group.links.new(smoothstep2.outputs[0], smoothstep4.inputs[0])
    
    group.links.new(smoothstep3.outputs[0], smoothstep5.inputs[0])
    group.links.new(smoothstep4.outputs[0], smoothstep5.inputs[1])
    
    group.links.new(smoothstep5.outputs[0], output.inputs['Value'])

    return group


# Takes a camera object, and ensures there is a node group for
# projecting textures from that camera.
#
# It will create it if it doesn't exist, and returns the group.
def ensure_camera_project_group(camera, default_aspect=1.0):
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

    # Create the group inputs.
    if not "Aspect Ratio" in group.interface.items_tree:
        socket = group.interface.new_socket(name="Aspect Ratio", socket_type='NodeSocketFloat', in_out='INPUT')
        socket.default_value = default_aspect
    if not "Rotation" in group.interface.items_tree:
        group.interface.new_socket(name="Rotation", socket_type='NodeSocketFloat', in_out='INPUT')
    if not "Loc X" in group.interface.items_tree:
        group.interface.new_socket(name="Loc X", socket_type='NodeSocketFloat', in_out='INPUT')
    if not "Loc Y" in group.interface.items_tree:
        group.interface.new_socket(name="Loc Y", socket_type='NodeSocketFloat', in_out='INPUT')

    # Create the group outputs.
    if not "Vector" in group.interface.items_tree:
        group.interface.new_socket(name="Vector", socket_type = 'NodeSocketVector', in_out='OUTPUT')

    #-------------------
    # Create the nodes.
    input = group.nodes.new(type='NodeGroupInput')
    output = group.nodes.new(type='NodeGroupOutput')

    camera_transform = group.nodes.new(type='ShaderNodeTexCoord')
    lens = group.nodes.new(type='ShaderNodeValue')
    sensor_width = group.nodes.new(type='ShaderNodeValue')
    lens_shift_x = group.nodes.new(type='ShaderNodeValue')
    lens_shift_y = group.nodes.new(type='ShaderNodeValue')

    zoom_1 = group.nodes.new(type='ShaderNodeMath')
    zoom_2 = group.nodes.new(type='ShaderNodeMath')
    lens_shift_1 = group.nodes.new(type='ShaderNodeCombineXYZ')
    to_radians = group.nodes.new(type='ShaderNodeMath')
    user_location = group.nodes.new(type='ShaderNodeCombineXYZ')

    perspective_1 = group.nodes.new(type='ShaderNodeSeparateXYZ')
    perspective_2 = group.nodes.new(type='ShaderNodeMath')
    perspective_3 = group.nodes.new(type='ShaderNodeMath')
    perspective_4 = group.nodes.new(type='ShaderNodeCombineXYZ')
    zoom_3 = group.nodes.new(type='ShaderNodeVectorMath')
    lens_shift_2 = group.nodes.new(type='ShaderNodeVectorMath')

    user_translate = group.nodes.new(type='ShaderNodeVectorMath')
    user_rotate = group.nodes.new(type='ShaderNodeVectorRotate')
    aspect_ratio_1 = group.nodes.new(type='ShaderNodeCombineXYZ')
    aspect_ratio_2 = group.nodes.new(type='ShaderNodeCombineXYZ')
    aspect_ratio_div = group.nodes.new(type='ShaderNodeMath')
    aspect_ratio_lt = group.nodes.new(type='ShaderNodeMath')
    aspect_ratio_switch = group.nodes.new(type='ShaderNodeMixRGB')
    user_transforms = group.nodes.new(type='ShaderNodeVectorMath')

    recenter = group.nodes.new(type='ShaderNodeVectorMath')
    
    #--------------------
    # Label the nodes.
    camera_transform.label = "Camera Transform"
    lens.label = "Lens"
    sensor_width.label = "Sensor Width"
    lens_shift_x.label = "Lens Shift X"
    lens_shift_y.label = "Lens Shift Y"

    zoom_1.label = "Zoom 1"
    zoom_2.label = "Zoom 2"
    lens_shift_1.label = "Lens Shift 1"
    to_radians.label = "Degrees to Radians"
    user_location.label = "User Location"

    perspective_1.label = "Perspective 1"
    perspective_2.label = "Perspective 2"
    perspective_3.label = "Perspective 3"
    perspective_4.label = "Perspective 4"
    zoom_3.label = "Zoom 3"
    lens_shift_2.label = "Lens Shift 2"

    user_translate.label = "User Translate"
    user_rotate.label = "User Rotate"

    aspect_ratio_1.label = "Aspect Ratio 1"
    aspect_ratio_2.label = "Aspect Ratio 2"
    aspect_ratio_div.label = "Divide"
    aspect_ratio_lt.label = "Less Than"
    aspect_ratio_switch.label = "Aspect Ratio Switch"

    user_transforms.label = "User Transforms"

    recenter.label = "Recenter"

    #---------------------
    # Position the nodes.
    hs = 250.0
    x = 0.0

    camera_transform.location = (x, 0.0)
    lens.location = (x, -700.0)
    sensor_width.location = (x, -900.0)
    lens_shift_x.location = (x, -1100.0)
    lens_shift_y.location = (x, -1300.0)
    input.location = (x, -1500.0)

    x += hs
    zoom_1.location = (x, -700.0)
    lens_shift_1.location = (x, -1100.0)
    to_radians.location = (x, -1500.0)
    user_location.location = (x, -1700.0)

    x += hs
    zoom_2.location = (x, -700.0)

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
    aspect_ratio_div.location = (x, -850.0)

    x += hs
    user_translate.location = (x, 0.0)
    aspect_ratio_lt.location = (x, -500.0)
    aspect_ratio_1.location = (x, -700.0)
    aspect_ratio_2.location = (x, -850.0)

    x += hs
    user_rotate.location = (x, 0.0)
    aspect_ratio_switch.location = (x, -600.0)

    x += hs
    user_transforms.location = (x, 0.0)

    x += hs
    recenter.location = (x, 0.0)

    x += hs
    output.location = (x, 0.0)

    #---------------------
    # Set up the drivers.

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
    camera_transform.object = camera

    zoom_1.operation = 'DIVIDE'
    zoom_1.use_clamp = False
    zoom_2.operation = 'MULTIPLY'
    zoom_2.use_clamp = False
    zoom_2.inputs[1].default_value = -1.0
    lens_shift_1.inputs[2].default_value = 0.0
    to_radians.operation = 'MULTIPLY'
    to_radians.use_clamp = False
    to_radians.inputs[1].default_value = math.pi / 180.0
    user_location.inputs[2].default_value = 0.0

    perspective_2.operation = 'DIVIDE'
    perspective_2.use_clamp = False
    perspective_3.operation = 'DIVIDE'
    perspective_3.use_clamp = False
    zoom_3.operation = 'MULTIPLY'
    lens_shift_2.operation = 'SUBTRACT'

    user_translate.operation = 'SUBTRACT'
    user_rotate.rotation_type = 'Z_AXIS'
    user_rotate.invert = False
    user_rotate.inputs['Center'].default_value = (0.0, 0.0, 0.0)
    aspect_ratio_1.inputs['X'].default_value = 1.0
    aspect_ratio_1.inputs['Z'].default_value = 0.0
    aspect_ratio_2.inputs['Y'].default_value = 1.0
    aspect_ratio_2.inputs['Z'].default_value = 0.0
    aspect_ratio_div.operation = 'DIVIDE'
    aspect_ratio_div.inputs[0].default_value = 1.0
    aspect_ratio_lt.operation = 'LESS_THAN'
    aspect_ratio_lt.inputs[1].default_value = 1.0
    aspect_ratio_switch.blend_type = 'MIX'
    aspect_ratio_switch.use_clamp = False

    user_transforms.operation = 'MULTIPLY'

    recenter.operation = 'ADD'
    recenter.inputs[1].default_value = (0.5, 0.5, 0.0)

    #--------------------
    # Hook up the nodes.
    group.links.new(camera_transform.outputs['Object'], perspective_1.inputs['Vector'])
    group.links.new(lens.outputs['Value'], zoom_1.inputs[0])
    group.links.new(sensor_width.outputs['Value'], zoom_1.inputs[1])
    group.links.new(zoom_1.outputs['Value'], zoom_2.inputs[0])
    group.links.new(zoom_2.outputs['Value'], zoom_3.inputs[1])
    group.links.new(lens_shift_x.outputs['Value'], lens_shift_1.inputs['X'])
    group.links.new(lens_shift_y.outputs['Value'], lens_shift_1.inputs['Y'])
    group.links.new(lens_shift_1.outputs['Vector'], lens_shift_2.inputs[1])

    group.links.new(input.outputs['Aspect Ratio'], aspect_ratio_1.inputs['Y'])
    group.links.new(input.outputs['Aspect Ratio'], aspect_ratio_div.inputs[1])
    group.links.new(input.outputs['Aspect Ratio'], aspect_ratio_lt.inputs[0])
    group.links.new(input.outputs['Rotation'], to_radians.inputs[0])
    group.links.new(to_radians.outputs['Value'], user_rotate.inputs['Angle'])
    group.links.new(input.outputs['Loc X'], user_location.inputs['X'])
    group.links.new(input.outputs['Loc Y'], user_location.inputs['Y'])
    group.links.new(user_location.outputs['Vector'], user_translate.inputs[1])

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

    group.links.new(aspect_ratio_div.outputs[0], aspect_ratio_2.inputs['X'])
    group.links.new(aspect_ratio_1.outputs[0], aspect_ratio_switch.inputs[1])
    group.links.new(aspect_ratio_2.outputs[0], aspect_ratio_switch.inputs[2])
    group.links.new(aspect_ratio_lt.outputs[0], aspect_ratio_switch.inputs[0])

    group.links.new(user_translate.outputs['Vector'], user_rotate.inputs['Vector'])
    group.links.new(user_rotate.outputs['Vector'], user_transforms.inputs[0])
    group.links.new(aspect_ratio_switch.outputs[0], user_transforms.inputs[1])
    group.links.new(user_transforms.outputs['Vector'], recenter.inputs[0])

    group.links.new(recenter.outputs['Vector'], output.inputs['Vector'])

    return group
