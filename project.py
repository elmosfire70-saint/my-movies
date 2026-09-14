# 자산 시트 등록, 프로젝트 검증, 프리비즈 실행과 검수된 숏의 편집을 제공한다.
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
import pipeline as p

BLENDER = Path('E:/Blender Foundation/Blender 5.2/blender.exe')


def initialize(path, title, story):
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError(path)
    p.save(path, {'id': path.parent.name, 'title': title, 'story': story, 'shots': [], 'assets': {}})
    return p.read(path)


def register(project_path, asset_id, kind, sheet, version, description):
    root = Path(project_path).resolve().parent
    project = p.read(project_path)
    if not re.fullmatch(r'(CHAR|PROP)_\d+', asset_id) or kind not in ('character', 'prop'):
        raise ValueError('Use CHAR_001 or PROP_001 and character or prop')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', version):
        raise ValueError('Invalid version')
    sheet = Path(sheet).resolve()
    target = root / 'assets' / asset_id / version / ('sheet' + sheet.suffix.lower())
    if target.exists():
        raise FileExistsError('Use a new asset version')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sheet, target)
    project.setdefault('assets', {}).setdefault(asset_id, {})[version] = {
        'kind': kind, 'sheet': target.relative_to(root).as_posix(),
        'sha256': p.digest(target), 'description': description, 'approved': False, 'views': {}}
    p.save(project_path, project)
    return project['assets'][asset_id][version]


def register_view(project_path, asset_id, version, view, source):
    if view not in ('front', 'side', 'rear', 'threequarter', 'face'):
        raise ValueError('Unsupported view name')
    root = Path(project_path).resolve().parent
    project = p.read(project_path)
    asset = project['assets'][asset_id][version]
    if asset['approved'] or view in asset['views']:
        raise ValueError('Create a new version to change approved or existing views')
    source = Path(source)
    target = root / 'assets' / asset_id / version / (view + source.suffix)
    shutil.copy2(source, target)
    asset['views'][view] = {'path': target.relative_to(root).as_posix(), 'sha256': p.digest(target)}
    p.save(project_path, project)
    return asset


def split_sheet(project_path, asset_id, version, boxes_path):
    from PIL import Image
    root = Path(project_path).resolve().parent
    manifest = p.read(project_path)
    asset = manifest['assets'][asset_id][version]
    boxes = p.read(boxes_path)
    with Image.open(root / asset['sheet']) as sheet:
        for name, box in boxes.items():
            if name not in ('front', 'side', 'rear', 'face', 'threequarter') or name in asset['views']:
                raise ValueError('Invalid or existing view: ' + name)
            if asset['approved'] or not (0 <= box[0] < box[2] <= sheet.width and 0 <= box[1] < box[3] <= sheet.height):
                raise ValueError('Invalid crop bounds or approved asset')
        for name, box in boxes.items():
            target = root / 'assets' / asset_id / version / (name + '.png')
            sheet.crop(box).save(target)
            asset['views'][name] = {'path': target.relative_to(root).as_posix(), 'sha256': p.digest(target), 'box': box}
    p.save(project_path, manifest)
    return asset


def validate_project(project_path):
    root = Path(project_path).resolve().parent
    project = p.read(project_path)
    errors = []
    ids = set()
    for shot_file in project['shots']:
        path = (root / shot_file).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Shot path escapes project')
        shot = p.read(path)
        if shot['id'] in ids:
            errors.append('Duplicate shot ID: ' + shot['id'])
        ids.add(shot['id'])
        for ref in shot.get('assets', []):
            asset = project.get('assets', {}).get(ref['id'], {}).get(ref['version'])
            if not asset:
                errors.append('Missing asset: ' + ref['id'])
            elif not (root / asset['sheet']).exists() or p.digest(root / asset['sheet']) != asset['sha256']:
                errors.append('Missing or modified sheet: ' + ref['id'])
            else:
                for view in asset.get('views', {}).values():
                    if not (root / view['path']).exists() or p.digest(root / view['path']) != view['sha256']:
                        errors.append('Missing or modified view: ' + ref['id'])
        try:
            p.validate(shot)
        except (ValueError, OSError) as error:
            errors.append(shot['id'] + ': ' + str(error))
    if errors:
        raise ValueError('\n'.join(errors))
    return {'valid': True, 'shots': len(ids), 'assets': len(project.get('assets', {}))}


def bind(project_path, asset_ids, previz_path, shot_id, prompt, output):
    root = Path(project_path).resolve().parent
    project = p.read(project_path)
    output = Path(output).resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Use a new shot JSON path inside the project')
    images, assets = [], []
    for entry in asset_ids:
        asset_id, version = entry.split('@', 1)
        asset = project['assets'][asset_id][version]
        preferred = asset['views'].get('front') if asset['kind'] == 'character' else asset['views'].get('threequarter')
        sheet = root / (preferred['path'] if preferred else asset['sheet'])
        if p.digest(sheet) != (preferred['sha256'] if preferred else asset['sha256']):
            raise ValueError('Asset sheet changed')
        images.append(str(sheet))
        assets.append({'id': asset_id, 'version': version})
    previz_path = Path(previz_path).resolve()
    report = p.read(previz_path / 'scene-report.json')
    frame = sorted(previz_path.glob('frame_*.png'))[0]
    images.append(str(frame))
    spec = {'id': shot_id, 'assets': assets, 'images': images, 'prompt': prompt,
            'width': 864, 'height': 480, 'seconds': (report['frame_end'] - report['frame_start'] + 1) / report['fps'],
            'seed': 42, 'turbo': False, 'previz': str(previz_path)}
    p.validate(spec)
    p.save(output, spec)
    project['shots'].append(output.relative_to(root).as_posix())
    p.save(project_path, project)
    return spec


def advance(project_path):
    validate_project(project_path)
    root = Path(project_path).resolve().parent
    results = []
    for shot in p.read(project_path)['shots']:
        path = root / shot
        if (path.parent / 'job.json').exists():
            job = p.refresh(path.parent)
            results.append({'shot': shot, 'status': job['status']})
            if job['status'] != 'approved':
                break
        else:
            results.append(p.submit(path))
            break
    return results


def link_previous(previous, next_shot):
    import av
    previous = Path(previous).resolve()
    next_shot = Path(next_shot).resolve()
    if (next_shot.parent / 'job.json').exists():
        raise ValueError('Do not change a submitted shot')
    job = p.refresh(previous)
    if job['status'] not in ('review_required', 'approved'):
        raise ValueError('Previous shot has not completed successfully')
    output = job['outputs'][0]
    if p.digest(output['path']) != output['sha256']:
        raise ValueError('Previous output changed')
    reference = previous / 'continuity-last.png'
    with av.open(output['path']) as container:
        last = None
        for frame in container.decode(video=0):
            last = frame
        last.to_image().save(reference)
    spec = p.read(next_shot)
    if spec.get('previous_shot'):
        raise ValueError('Continuity reference already linked')
    spec['images'].append(str(reference))
    spec['prompt'] += (f" Use <Picture {len(spec['images'])}> as the previous shot's ending. "
                       'Keep the same woman, the same car, parking place and camera direction. Continue the action from this situation.')
    spec['previous_shot'] = str(previous)
    p.validate(spec)
    p.save(next_shot, spec)
    return spec


def previz(spec, output, animation=False):
    output = Path(output).resolve()
    env = os.environ.copy()
    resources = p.ROOT / '.blender-runtime'
    resources.mkdir(exist_ok=True)
    env['BLENDER_USER_RESOURCES'] = str(resources)
    command = [str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
               '--python', str(p.ROOT / 'blender_previz.py'), '--', str(Path(spec).resolve()), str(output)]
    if animation:
        command.append('--animation')
    subprocess.run(command, env=env, check=True)
    report = p.read(output / 'scene-report.json')
    source = p.read(spec)
    if report['fps'] != 24 or report['frame_end'] != round(source['seconds'] * 24):
        raise ValueError('Blender output does not match shot timing')
    if not report['active_camera'] or not list(output.glob('frame_*.png')):
        raise ValueError('Missing camera or render')
    return report


def approve(directory, note):
    directory = Path(directory)
    job = p.refresh(directory)
    if job['status'] != 'review_required':
        raise ValueError('Review a successfully decoded output first')
    if not note.strip():
        raise ValueError('Record the reviewer and review result')
    job.update(status='approved', review=note)
    p.save(directory / 'job.json', job)
    return job


def assemble(project_path, output, preview=False):
    import av
    from fractions import Fraction
    root = Path(project_path).resolve().parent
    project = p.read(project_path)
    files = []
    for shot in project['shots']:
        job = p.read((root / shot).parent / 'job.json')
        allowed = ('approved', 'review_required') if preview else ('approved',)
        if job['status'] not in allowed:
            raise ValueError('All shots require a recorded review before final assembly')
        file = Path(job['outputs'][0]['path'])
        if job['outputs'][0].get('sha256') and p.digest(file) != job['outputs'][0]['sha256']:
            raise ValueError('Approved output changed')
        files.append(file)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = [p.inspect_video(f) for f in files]
    first = metadata[0]
    if any((m['width'], m['height'], m['fps']) != (first['width'], first['height'], first['fps']) for m in metadata):
        raise ValueError('Normalize shot resolution and fps before assembly')
    partial = output.with_suffix('.partial.mp4')
    with av.open(str(partial), 'w') as target:
        video = target.add_stream('libx264', rate=24)
        video.width, video.height, video.pix_fmt = first['width'], first['height'], 'yuv420p'
        audio = target.add_stream('aac', rate=48000)
        audio.layout = 'stereo'
        video_index = audio_index = 0
        for file, info in zip(files, metadata):
            with av.open(str(file)) as source:
                for frame in source.decode(video=0):
                    frame.pts, frame.time_base = video_index, Fraction(1, 24)
                    video_index += 1
                    for packet in video.encode(frame):
                        target.mux(packet)
            resampler = av.AudioResampler(format='fltp', layout='stereo', rate=48000)
            audio_end = audio_index + info['decoded_frames'] * 2000
            def encode_audio(converted):
                nonlocal audio_index
                remaining = audio_end - audio_index
                if remaining <= 0:
                    return
                if converted.samples > remaining:
                    converted = av.AudioFrame.from_ndarray(converted.to_ndarray()[:, :remaining].copy(), format='fltp', layout='stereo')
                converted.sample_rate = 48000
                converted.pts, converted.time_base = audio_index, Fraction(1, 48000)
                audio_index += converted.samples
                for packet in audio.encode(converted):
                    target.mux(packet)
            with av.open(str(file)) as source:
                for frame in source.decode(audio=0):
                    for converted in resampler.resample(frame):
                        encode_audio(converted)
                for converted in resampler.resample(None):
                    encode_audio(converted)
            if audio_index < audio_end:
                import numpy as np
                encode_audio(av.AudioFrame.from_ndarray(np.zeros((2, audio_end - audio_index), dtype=np.float32), format='fltp', layout='stereo'))
        for stream in (video, audio):
            for packet in stream.encode(None):
                target.mux(packet)
    result = p.inspect_video(partial)
    if result['decoded_frames'] != sum(m['decoded_frames'] for m in metadata):
        raise ValueError('Assembly lost frames')
    partial.replace(output)
    p.save(output.with_suffix('.json'), {'mode': 'preview' if preview else 'approved_assembly', 'inputs': [str(f) for f in files], **result})
    return result


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    for field in ('path', 'title', 'story'):
        init.add_argument(field)
    reg = commands.add_parser('register')
    for field in ('project', 'id', 'kind', 'sheet', 'version', 'description'):
        reg.add_argument(field)
    view = commands.add_parser('register-view')
    for field in ('project', 'id', 'version', 'view', 'source'):
        view.add_argument(field)
    split = commands.add_parser('split-sheet')
    for field in ('project', 'id', 'version', 'boxes'):
        split.add_argument(field)
    check = commands.add_parser('validate')
    check.add_argument('project')
    step = commands.add_parser('advance')
    step.add_argument('project')
    continuity = commands.add_parser('link-previous')
    continuity.add_argument('previous')
    continuity.add_argument('next_shot')
    binding = commands.add_parser('bind')
    for field in ('project', 'previz', 'id', 'prompt', 'output'):
        binding.add_argument(field)
    binding.add_argument('--asset', action='append', required=True)
    render = commands.add_parser('previz')
    render.add_argument('spec')
    render.add_argument('output')
    render.add_argument('--animation', action='store_true')
    review = commands.add_parser('approve')
    review.add_argument('directory')
    review.add_argument('note')
    edit = commands.add_parser('assemble')
    edit.add_argument('project')
    edit.add_argument('output')
    edit.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if args.command == 'init':
        result = initialize(args.path, args.title, args.story)
    elif args.command == 'register':
        result = register(args.project, args.id, args.kind, args.sheet, args.version, args.description)
    elif args.command == 'register-view':
        result = register_view(args.project, args.id, args.version, args.view, args.source)
    elif args.command == 'split-sheet':
        result = split_sheet(args.project, args.id, args.version, args.boxes)
    elif args.command == 'validate':
        result = validate_project(args.project)
    elif args.command == 'advance':
        result = advance(args.project)
    elif args.command == 'link-previous':
        result = link_previous(args.previous, args.next_shot)
    elif args.command == 'bind':
        result = bind(args.project, args.asset, args.previz, args.id, args.prompt, args.output)
    elif args.command == 'previz':
        result = previz(args.spec, args.output, args.animation)
    elif args.command == 'approve':
        result = approve(args.directory, args.note)
    else:
        result = assemble(args.project, args.output, args.preview)
    print(p.json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
