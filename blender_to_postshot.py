bl_info = {
    "name": "PostShot Export",
    "author": "Mate Steinforth",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > PostShot Tab",
    "description": "Exports camera and point data for 3D reconstruction",
    "category": "3D View"
}

import bpy
from bpy.props import IntProperty, StringProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup
import os
import math
import mathutils
from math import pi, sin, cos
from mathutils import Vector

# Output directory
output_dir = "/Users/msteinforth/Desktop/temp/gs"
os.makedirs(output_dir, exist_ok=True)
cameras_file = os.path.join(output_dir, "cameras.txt")
images_file = os.path.join(output_dir, "images.txt")
points3D_file = os.path.join(output_dir, "points3D.txt")
images_dir = os.path.join(output_dir, "")
os.makedirs(images_dir, exist_ok=True)

def create_cameras_around_sphere(num_cameras):
    cameras = []
    radius = 10  # Distance from the center
    golden_angle = pi * (3 - math.sqrt(5))  # Fibonacci golden angle
    for i in range(num_cameras):
        theta = golden_angle * i
        phi = math.acos(1 - 2 * (i + 0.5) / num_cameras)
        x = radius * sin(phi) * cos(theta)
        y = radius * sin(phi) * sin(theta)
        z = radius * cos(phi)
        # Create camera
        bpy.ops.object.camera_add(location=(x, y, z))
        camera = bpy.context.object
        camera.name = f"Camera_{i+1}"
        # Set camera rotation mode
        camera.rotation_mode = 'XYZ'
        # Calculate direction vector from camera to target (origin)
        direction = Vector((0, 0, 0)) - Vector((x, y, z))
        rot_quat = direction.to_track_quat('Z', 'Y')
        # Set camera rotation
        camera.rotation_euler = rot_quat.to_euler()
        # Flip the camera to look at the center and then flip it upside down
        camera.rotation_euler.rotate_axis("X", math.pi)
        cameras.append(camera)
    return cameras

# Function to get camera intrinsics in COLMAP format
def get_camera_intrinsics(camera):
    scene = bpy.context.scene
    render = scene.render
    K = camera.data.lens
    width = render.resolution_x
    height = render.resolution_y
    fx = K * width / camera.data.sensor_width
    fy = fx  # Assuming square pixels
    cx = width / 2.0
    cy = height / 2.0
    return fx, fy, cx, cy

# Function to convert Blender Z-up to COLMAP Y-up coordinates
def convert_coordinates(cam):
    rotation_mode_bk = cam.rotation_mode
                
    cam.rotation_mode = "QUATERNION"
    cam_rot_orig = mathutils.Quaternion(cam.rotation_quaternion)
    cam_rot = mathutils.Quaternion((
        cam_rot_orig.x,
        cam_rot_orig.w,
        cam_rot_orig.z,
        -cam_rot_orig.y))
    qw = cam_rot.w
    qx = cam_rot.x
    qy = cam_rot.y
    qz = cam_rot.z
    cam.rotation_mode = rotation_mode_bk

    T = mathutils.Vector(cam.location)
    T1 = -(cam_rot.to_matrix() @ T)
    
    tx = T1[0]
    ty = T1[1]
    tz = T1[2]
                
    
    return tx, ty, tz # position.x, position.z, -position.y

# Function to convert Blender rotation to COLMAP format (Hamilton convention)
def convert_rotation(rotation):
    if isinstance(rotation, mathutils.Euler):
        rotation = rotation.to_quaternion()
    # Blender to COLMAP coordinate system transformation
    # Swap and invert z and y to match COLMAP's coordinate system
    quat = rotation
    return [quat.x, quat.w, quat.z, -quat.y]

# Function to export camera intrinsics in COLMAP format
def export_camera_intrinsics(cameras, file_path):
    with open(file_path, 'w') as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   Camera ID, MODEL, width, height, fx, fy, cx, cy\n")
        f.write(f"# Number of cameras: {len(cameras)}\n")
        
        for idx, camera in enumerate(cameras):
            fx, fy, cx, cy = get_camera_intrinsics(camera)
            width = bpy.context.scene.render.resolution_x
            height = bpy.context.scene.render.resolution_y
            f.write(f"{idx} PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")

# Function to export images metadata in COLMAP format
def export_images_metadata(cameras, file_path, images_dir):
    with open(file_path, 'w') as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("# IMAGE_ID, QVEC (w, x, y, z), TVEC (x, y, z), CAMERA_ID, NAME\n")
        f.write("# POINTS2D[] as (x, y, POINT3D_ID)\n")
        for cam_id, camera in enumerate(cameras):
            # Get camera pose
            location, rotation, scale = camera.matrix_world.decompose()
            print(cam_id , " " ,  location)
            qvec = convert_rotation(rotation)
            colmap_location = convert_coordinates(camera)
            
            # Image file name
            img_name = f"frame_{cam_id:05d}.png"
            img_path = os.path.join(images_dir, img_name)

            # Render image
            bpy.context.scene.camera = camera
            bpy.context.scene.render.filepath = img_path
            bpy.ops.render.render(write_still=True)

            f.write(f"{cam_id + 1} {qvec[0]} {qvec[1]} {qvec[2]} {qvec[3]} {colmap_location[0]} {colmap_location[1]} {colmap_location[2]} 0 {img_name}\n")
            f.write("\n")

            f.write(f"{cam_id + 1} {qvec[0]} {qvec[1]} {qvec[2]} {qvec[3]} {colmap_location[0]} {colmap_location[1]} {colmap_location[2]} 0 {img_name}\n")
            f.write("\n")

def distribute_points(mesh_obj, number_of_points):
    if not mesh_obj:
        print("No mesh object provided.")
        return []
    # Create a new particle system for the mesh object
    mesh_obj.modifiers.new(name="Particles", type='PARTICLE_SYSTEM')
    particle_system = mesh_obj.particle_systems[-1]
    particle_system.settings.count = number_of_points
    particle_system.settings.emit_from = 'FACE'
    particle_system.settings.use_even_distribution = True
    particle_system.settings.physics_type = 'NO'
    particle_system.settings.particle_size = 0.1
    particle_system.settings.show_unborn = True
    particle_system.settings.use_dead = False
    # Update the scene and dependencies
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()  # Force dependency graph update
    # Ensure the particle system is evaluated
    evaluated_obj = mesh_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    particles = evaluated_obj.particle_systems[0].particles
    # Collect points
    points = [(particle.location.x, particle.location.y, particle.location.z) for particle in particles]
    return points, particle_system

def delete_points(mesh_obj, particle_system):
    # Remove the particle system modifier
    for modifier in mesh_obj.modifiers:
        if modifier.type == 'PARTICLE_SYSTEM' and modifier.particle_system == particle_system:
            mesh_obj.modifiers.remove(modifier)
            break
    # Remove the particle system from the object
    bpy.ops.object.select_all(action='DESELECT')  # Deselect all objects
    mesh_obj.select_set(True)  # Select the target object
    bpy.context.view_layer.objects.active = mesh_obj  # Make it the active object
    bpy.ops.object.particle_system_remove()  # Remove the active particle system
    
def export_points(mesh_obj, points, file_path):
    if not mesh_obj:
        print("Mesh object not provided.")
        return
    with open(file_path, 'w') as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        
        for idx, point in enumerate(points):
            # Convert tuple point to Vector
            point_vector = Vector(point)
            # Convert point to world coordinates
            world_point = mesh_obj.matrix_world @ point_vector
            x, y, z = world_point.x, world_point.y, world_point.z
            r, g, b = 255, 255, 255  # Example color (white)
            error = 1.0  # Example reconstruction error
            track = [(0, idx), (1, idx)]  # Adjust as per your dataset
            track_str = ' '.join([f"{img_id} {point2d_idx}" for img_id, point2d_idx in track])
            f.write(f"{idx} {x} {y} {z} {r} {g} {b} {error} {track_str}\n")


class EXPORT_OT_scene_data(Operator):
    bl_idname = "export.scene_data"
    bl_label = "Export Scene Data"
    bl_description = "Export cameras and points data for 3D reconstruction"
    def execute(self, context):
        settings = context.scene.export_settings
        output_dir = settings.export_path
        os.makedirs(output_dir, exist_ok=True)
        cameras_file = os.path.join(output_dir, "cameras.txt")
        images_file = os.path.join(output_dir, "images.txt")
        points3D_file = os.path.join(output_dir, "points3D.txt")
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        selected_obj = settings.object_to_export  # Retrieve the selected object from settings
        num_points = settings.num_points
        num_cameras = settings.num_cameras
        # Check if a valid mesh object is selected
        if selected_obj is None or selected_obj.type != 'MESH':
            self.report({'ERROR'}, "No valid mesh object is selected.")
            return {'CANCELLED'}
        # Distribute points on the selected mesh object
        points, particle_system = distribute_points(selected_obj, num_points)
        if not points:
            self.report({'ERROR'}, "Failed to distribute points on the mesh.")
            return {'CANCELLED'}
        # Export points
        export_points(selected_obj, points, points3D_file)
        # Delete the particle system after exporting points
        delete_points(selected_obj, particle_system)
        # Create cameras and get the list
        cameras = create_cameras_around_sphere(num_cameras)
        # Export camera intrinsics to cameras.txt
        export_camera_intrinsics(cameras, cameras_file)
        # Export images metadata to images.txt
        export_images_metadata(cameras, images_file, images_dir)
        # Delete cameras after exporting data
        for camera in cameras:
            bpy.data.objects.remove(camera)
        self.report({'INFO'}, "Export completed successfully.")
        return {'FINISHED'}
        

class EXPORT_PT_main_panel(Panel):
    bl_label = "PostShot Export Settings"
    bl_idname = "EXPORT_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PostShot'
    def draw(self, context):
        layout = self.layout
        settings = context.scene.export_settings
        layout.prop(settings, "object_to_export")
        layout.prop(settings, "export_path")
        layout.prop(settings, "num_cameras")
        layout.prop(settings, "num_points")
        layout.operator(EXPORT_OT_scene_data.bl_idname)
        
class ExportSettings(PropertyGroup):
    object_to_export: PointerProperty(
        name="Object to Export",
        type=bpy.types.Object,
        description="Select the object to export"
    )
    export_path: StringProperty(
        name="Export Path",
        default="//export_data",
        subtype='DIR_PATH',
        description="Directory path to export data"
    )
    num_cameras: IntProperty(
        name="Number of Cameras",
        default=10,
        min=1,
        max=100,
        description="Set the number of cameras"
    )
    num_points: IntProperty(
        name="Number of Points",
        default=1000,
        min=1,
        max=10000,
        description="Set the number of points to distribute"
    )

def register():
    bpy.utils.register_class(ExportSettings)
    bpy.utils.register_class(EXPORT_OT_scene_data)
    bpy.utils.register_class(EXPORT_PT_main_panel)
    bpy.types.Scene.export_settings = PointerProperty(type=ExportSettings)
def unregister():
    bpy.utils.unregister_class(ExportSettings)
    bpy.utils.unregister_class(EXPORT_OT_scene_data)
    bpy.utils.unregister_class(EXPORT_PT_main_panel)
    del bpy.types.Scene.export_settings
if __name__ == "__main__":
    register()
