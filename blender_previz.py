# 숏 명세를 저분할 기본 도형의 별도 Blender 파일과 프리비즈 프레임으로 변환한다.
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector


def primitive(kind, name, location, scale, color, parent=None):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, location=location)
    elif kind == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1, depth=2, location=location)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=8, location=location)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    obj = bpy.context.object
    obj.name, obj.scale, obj.parent = name, scale, parent
    mat = bpy.data.materials.get(name + '_mat') or bpy.data.materials.new(name + '_mat')
    mat.diffuse_color = (*color, 1)
    obj.data.materials.append(mat)
    return obj


def actor(item):
    root = bpy.data.objects.new(item['id'], None)
    bpy.context.collection.objects.link(root)
    color = item.get('color', [0.5, 0.5, 0.5])
    def part(kind, suffix, pos, scale):
        return primitive(kind, item['id'] + '_' + suffix, pos, scale, color, root)
    kind = item['kind']
    if kind == 'person':
        part('sphere', 'head', (0, 0, 1.55), (.14, .13, .19))
        part('cube', 'torso', (0, 0, 1.08), (.2, .12, .28))
        for side in (-1, 1):
            part('cylinder', f'leg{side}', (side * .11, 0, .43), (.08, .08, .39))
            part('cylinder', f'arm{side}', (side * .27, 0, 1.02), (.06, .06, .31))
    elif kind == 'car':
        part('cube', 'body', (0, 0, .65), (1, 2, .35))
        cabin = part('cube', 'cabin', (0, 0, 1.28), (1, 1, 1))
        for vertex in cabin.data.vertices:
            upper = vertex.co.z > 0
            vertex.co.x *= .78 if upper else .94
            vertex.co.y *= .85 if upper else 1.35
            vertex.co.z *= .28
        cabin.data.materials[0].diffuse_color = (.08, .12, .16, 1)
        part('cube', 'roof', (0, 0, 1.58), (.79, .86, .035))
        part('cube', 'seat', (-.45, -.3, .98), (.3, .4, .08))
        hinge = bpy.data.objects.new(item['id'] + '_door_hinge', None)
        bpy.context.collection.objects.link(hinge)
        hinge.parent, hinge.location = root, (-1, -1, .7)
        primitive('cube', item['id'] + '_door', (0, .5, .3), (.06, .5, .3), color, hinge)
        for key in item.get('door_keys', []):
            hinge.rotation_euler.z = key['angle']
            hinge.keyframe_insert(data_path='rotation_euler', frame=key['frame'])
        for x in (-1, 1):
            for y in (-1.3, 1.3):
                wheel = part('cylinder', f'wheel{x}_{y}', (x, y, .4), (.4, .4, .16))
                wheel.rotation_euler[1] = math.pi / 2
    elif kind == 'helicopter':
        part('sphere', 'body', (0, 0, 1.3), (.9, 1.5, .8))
        part('cube', 'tail', (0, 2.4, 1.3), (.16, 1.4, .16))
        part('cube', 'rotor', (0, 0, 2.25), (2.8, .1, .035))
        for x in (-.7, .7):
            part('cube', f'skid{x}', (x, 0, .35), (.06, 1.5, .06))
    elif kind in ('cube', 'sphere', 'cylinder', 'cone'):
        part(kind, 'body', (0, 0, .5), (.5, .5, .5))
    else:
        raise ValueError('Unsupported primitive actor: ' + kind)
    root.location = item.get('location', [0, 0, 0])
    root.scale = item.get('scale', [1, 1, 1])
    root.rotation_euler = item.get('rotation', [0, 0, 0])
    for key in item.get('keyframes', []):
        for prop in ('location', 'rotation_euler', 'scale'):
            if prop in key:
                setattr(root, prop, key[prop])
                root.keyframe_insert(data_path=prop, frame=key['frame'])
    return root


def build(spec, output, animation=False):
    if not bpy.app.background:
        raise RuntimeError('Run in a separate background Blender process')
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'previz.blend').exists():
        raise FileExistsError('Choose a new output directory to preserve the previous scene')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if hasattr(bpy.context.preferences.filepaths, 'save_preview_images'):
        bpy.context.preferences.filepaths.save_preview_images = False
    scene = bpy.context.scene
    scene.name = spec['id']
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new('NeutralWorld')
    scene.world.color = (.16, .16, .16)
    scene.render.resolution_x, scene.render.resolution_y = spec['width'], spec['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, round(spec['seconds'] * 24)
    for item in spec['objects']:
        actor(item)
    primitive('cube', 'Ground', (0, 0, -.1), (10, 10, .1), (.35, .35, .35))
    bpy.ops.object.camera_add(location=spec['camera']['location'])
    camera = bpy.context.object
    camera.name = 'ShotCamera'
    camera.rotation_euler = (Vector(spec['camera']['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = spec['camera'].get('lens', 50)
    scene.camera = camera
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output / 'frame_')
    scene.frame_set(scene.frame_start)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'previz.blend'))
    report = {'scene': scene.name, 'active_camera': camera.name,
              'frame_start': scene.frame_start, 'frame_end': scene.frame_end, 'fps': 24,
              'camera_location': list(camera.location), 'camera_rotation': list(camera.rotation_euler), 'lens_mm': camera.data.lens,
              'objects': [{'name': o.name, 'type': o.type, 'polygons': len(o.data.polygons) if o.type == 'MESH' else 0} for o in scene.objects]}
    report['motion_samples'] = {}
    for frame in (scene.frame_start, (scene.frame_end + 1) // 2, scene.frame_end):
        scene.frame_set(frame)
        report['motion_samples'][str(frame)] = {item['id']: list(bpy.data.objects[item['id']].location) for item in spec['objects']}
    (output / 'scene-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if animation:
        bpy.ops.render.render(animation=True)
    else:
        for frame in sorted(set([1, (scene.frame_end + 1) // 2, scene.frame_end])):
            scene.frame_set(frame)
            scene.render.filepath = str(output / f'frame_{frame:04}.png')
            bpy.ops.render.render(write_still=True)
    for view in spec.get('views', []):
        scene.frame_set(1)
        camera.location = view['location']
        camera.rotation_euler = (Vector(spec['camera']['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(output / ('view_' + view['name'] + '.png'))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('spec')
    parser.add_argument('output')
    parser.add_argument('--animation', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    build(json.loads(Path(args.spec).read_text(encoding='utf-8-sig')), Path(args.output).resolve(), args.animation)
