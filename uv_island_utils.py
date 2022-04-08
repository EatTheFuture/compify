from math import inf
from bpy_extras.mesh_utils import mesh_linked_uv_islands


def uv_island_bbox_area_sum_multi_object(mesh_objects, uv_layer_name):
    area_sum = 0.0
    for obj in mesh_objects:
        area_sum += uv_island_bbox_area_sum(obj.data, uv_layer_name)
    return area_sum


def uv_island_bbox_area_sum(mesh, uv_layer_name):
    """ Returns the sum of the area of the bounding boxes of all the UV
        islands in the given mesh for the given uv layer.
    """
    uvs = mesh.uv_layers[uv_layer_name].data
    islands = mesh_linked_uv_islands(mesh)

    bbox_area_sum = 0.0
    for island in islands:
        # Calculate the island's bounding box.
        min_u = inf
        max_u = -inf
        min_v = inf
        max_v = -inf
        for face_idx in island:
            for loop_idx in mesh.polygons[face_idx].loop_indices:
                uv = uvs[mesh.loops[loop_idx].vertex_index].uv
                min_u = min(min_u, uv[0])
                max_u = max(max_u, uv[0])
                min_v = min(min_v, uv[1])
                max_v = max(max_v, uv[1])

        # Add it's area to the sum.
        bbox_area_sum += ((max_u - min_u) * (max_v - min_v))**0.5

    return bbox_area_sum
