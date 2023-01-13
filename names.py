MAIN_NODE_NAME = "Compify Footage"
BAKE_IMAGE_NODE_NAME = "Baked Lighting"
UV_LAYER_NAME = 'Compify Baked Lighting'

# Gets the Compify Material name for the active scene.
def compify_mat_name(context):
    return "Compify Footage | " + context.scene.name


# Gets the Compify baked lighting image name for the active scene.
def compify_baked_texture_name(context):
    return "Compify Bake | " + context.scene.name
