"""Blender scene initialization and anatomy mesh creation for MEDI."""

try:
    import bpy
    import bmesh
except ImportError:
    bpy = None
    bmesh = None


def create_anatomical_scene() -> None:
    """
    Create a full-body anatomical scene in Blender for MEDI visualization.
    """
    if bpy is None:
        print("Blender not available")
        return

    # Clear existing mesh data
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Create main body structure
    anatomical_parts = {
        "Head": {"location": (0, 0, 2.5),"scale": (0.35, 0.35, 0.4)},
        "Neck": {"location": (0, 0, 2.0),"scale": (0.15, 0.15, 0.25)},
        "Chest": {"location": (0, 0, 1.2),"scale": (0.5, 0.3, 0.6)},
        "Abdomen": {"location": (0, 0, 0.6),"scale": (0.45, 0.28, 0.5)},
        "Left Arm": {"location": (-0.6, 0, 1.3),"scale": (0.15, 0.15, 0.65)},
        "Right Arm": {"location": (0.6, 0, 1.3),"scale": (0.15, 0.15, 0.65)},
        "Left Leg": {"location": (-0.25, 0, -0.5),"scale": (0.18, 0.18, 1.0)},
        "Right Leg": {"location": (0.25, 0, -0.5),"scale": (0.18, 0.18, 1.0)},
        "Lower Back": {"location": (0, -0.2, 0.8),"scale": (0.4, 0.12, 0.4)},
        "Left Knee": {"location": (-0.25, 0, 0.0),"scale": (0.2, 0.2, 0.15)},
        "Right Knee": {"location": (0.25, 0, 0.0),"scale": (0.2, 0.2, 0.15)},
        "Left Ankle": {"location": (-0.25, 0, -1.3),"scale": (0.15, 0.15, 0.12)},
        "Right Ankle": {"location": (0.25, 0, -1.3),"scale": (0.15, 0.15, 0.12)},
        "Left Shoulder": {"location": (-0.52, 0, 1.5),"scale": (0.2, 0.12, 0.2)},
        "Right Shoulder": {"location": (0.52, 0, 1.5),"scale": (0.2, 0.12, 0.2)},
        "Hip": {"location": (0, 0, 0.4),"scale": (0.5, 0.25, 0.35)},
    }

    for part_name, props in anatomical_parts.items():
        # Create UV sphere for each body part
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=props["location"])
        obj = bpy.context.active_object
        obj.name = part_name
        obj.scale = props["scale"]

        # Create material
        mat = bpy.data.materials.new(name=f"{part_name}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.9, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.1
        obj.data.materials.append(mat)

    print("Anatomical scene created with", len(anatomical_parts), "body parts.")


def highlight_anatomical_region(region_name: str, color: tuple = (1.0, 0.2, 0.2)) -> None:
    """
    Highlight a specific anatomical region by changing its material color.
    """
    if bpy is None:
        return

    for obj in bpy.data.objects:
        if region_name.lower() in obj.name.lower():
            if obj.data.materials:
                mat = obj.data.materials[0]
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
                    bsdf.inputs["Emission"].default_value = (*color, 1.0)
                    bsdf.inputs["Emission Strength"].default_value = 0.8
            return


def reset_anatomical_colors() -> None:
    """
    Reset all anatomical region colors to default.
    """
    if bpy is None:
        return

    for obj in bpy.data.objects:
        if obj.data.materials:
            mat = obj.data.materials[0]
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.9, 1.0)
                bsdf.inputs["Emission"].default_value = (0.0, 0.0, 0.0, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.0
