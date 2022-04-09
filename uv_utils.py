from math import inf


def leftmost_u(mesh_objects, uv_layer_name):
    leftmost = inf
    for obj in mesh_objects:
        uvs = obj.data.uv_layers[uv_layer_name].data
        for uv in uvs:
            leftmost = min(leftmost, uv.uv[0])
    return leftmost
