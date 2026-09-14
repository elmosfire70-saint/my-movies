# 프로젝트 자산과 H3 작업의 검증, 제출, 복구, 결과 수집을 관리한다.
import argparse
import hashlib
import json
import re
import time
import uuid
import asyncio
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent
SERVER = 'http://127.0.0.1:8188'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.' + uuid.uuid4().hex + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def api(route, data=None):
    body = None if data is None else json.dumps(data).encode()
    with urlopen(Request(SERVER + route, data=body, headers={'Content-Type': 'application/json'}), timeout=30) as response:
        return json.load(response)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def upload(path):
    path = Path(path)
    boundary = uuid.uuid4().hex
    name = digest(path)[:16] + path.suffix.lower()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n').encode() + path.read_bytes()
    body += f'\r\n--{boundary}--\r\n'.encode()
    request = Request(SERVER + '/upload/image', data=body,
                      headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urlopen(request, timeout=60) as response:
        result = json.load(response)
    return '/'.join(filter(None, [result.get('subfolder'), result['name']]))


def validate(spec):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', spec['id']):
        raise ValueError('Invalid shot ID')
    refs = spec['images']
    if not 1 <= len(refs) <= 9:
        raise ValueError('R2V requires 1-9 images in this implementation')
    hashes = [digest(p) for p in refs]
    if len(set(hashes)) != len(hashes):
        raise ValueError('Duplicate reference images')
    tags = re.findall(r'<(Picture|Video|Audio)\s+(\d+)>', spec['prompt'])
    if any(kind != 'Picture' or not 1 <= int(n) <= len(refs) for kind, n in tags):
        raise ValueError('Prompt references a missing input')
    if {int(n) for _, n in tags} != set(range(1, len(refs) + 1)):
        raise ValueError('Describe the role of every reference image')
    if any(spec[k] <= 0 or spec[k] % 32 for k in ('width', 'height')):
        raise ValueError('Resolution must be positive multiples of 32')
    if spec['width'] * spec['height'] > 1344 * 768:
        raise ValueError('Canvas exceeds the verified H3 limit')
    if not 2 <= spec['seconds'] <= 15:
        raise ValueError('Duration must be 2-15 seconds')
    if 'anchor_first' in spec and (type(spec['anchor_first']) is not int or not 0 <= spec['anchor_first'] < len(refs)):
        raise ValueError('anchor_first must be a zero-based reference image index')
    return hashes


def graph(spec, names):
    g = read(ROOT / 'h3-reference-api.json')
    # 실행에 성공한 그래프에서 불필요한 스위치와 참조를 제거한다.
    for key in ['137', '139', '141', '142', '143', '144', '145', '146']:
        g.pop(key, None)
    model = ['127', 0]
    if spec.get('turbo', False):
        g['145'] = {'class_type': 'LoraLoaderModelOnly', 'inputs': {
            'model': model, 'lora_name': 'minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors', 'strength_model': 1.0}}
        model = ['145', 0]
    g['126']['inputs']['model'] = model
    g['124']['inputs']['steps'] = 4 if spec.get('turbo') else 20
    g['129']['inputs']['noise_seed'] = spec['seed']
    g['132']['inputs']['value'] = spec['seconds']
    g['138']['inputs']['value'] = spec['prompt']
    g['92']['inputs']['filename_prefix'] = 'codex/' + spec['id']
    cond = g['136']['inputs']
    for key in list(cond):
        if key.startswith('ref_images.') or (key.startswith('ref_image_') and key != 'ref_image_size'):
            del cond[key]
    cond['width'], cond['height'] = spec['width'], spec['height']
    for i, name in enumerate(names):
        key = str(200 + i)
        g[key] = {'class_type': 'LoadImage', 'inputs': {'image': name}}
        cond[f'ref_images.ref_image_{i}'] = [key, 0]
    if 'anchor_first' in spec:
        g['300'] = {'class_type': 'MiniMaxH3AddGuide', 'inputs': {
            'positive': ['136', 0], 'latent': ['136', 1], 'vae': ['119', 0],
            'image': [str(200 + spec['anchor_first']), 0], 'frame_idx': 0}}
        g['126']['inputs']['conditioning'] = ['300', 0]
    return g


def inspect_video(path):
    import av
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        result = {'width': video.width, 'height': video.height,
                  'fps': float(video.average_rate), 'audio_streams': len(container.streams.audio),
                  'duration': container.duration / av.time_base if container.duration else None}
        if container.streams.audio:
            stream = container.streams.audio[0]
            result.update(audio_channels=stream.codec_context.channels, audio_sample_rate=stream.codec_context.sample_rate)
        result['decoded_frames'] = sum(1 for _ in container.decode(video=0))
    if result['decoded_frames'] == 0:
        raise ValueError('No decodable video frames')
    with av.open(str(path)) as container:
        result['audio_frames'] = sum(1 for _ in container.decode(audio=0)) if result['audio_streams'] else 0
    return result


def refresh(directory):
    directory = Path(directory)
    job = read(directory / 'job.json')
    if job.get('shot_hash') and digest(directory / 'shot.json') != job['shot_hash']:
        raise ValueError('Shot changed after submission; create a new shot revision')
    if job['status'] in ('approved', 'rejected', 'cancelled'):
        return job
    if not job.get('prompt_id'):
        candidates = [v for v in api('/history').values() if v['prompt'][3].get('codex_job_id') == job['job_id']]
        queue = api('/queue')
        queued = [v for v in queue['queue_running'] + queue['queue_pending'] if v[3].get('codex_job_id') == job['job_id']]
        if candidates:
            job['prompt_id'] = candidates[0]['prompt'][1]
        elif queued:
            job['prompt_id'] = queued[0][1]
        else:
            raise RuntimeError('Submission outcome unknown; do not resubmit automatically')
    history = api('/history/' + job['prompt_id']).get(job['prompt_id'])
    if history:
        save(directory / 'history.json', history)
        job['status'] = 'failed' if history['status']['status_str'] != 'success' else 'review_required'
        if any(message[0] == 'execution_interrupted' for message in history['status']['messages']):
            job['status'] = 'cancelled'
        job['server_status'] = history['status']
        if job['status'] == 'review_required':
            from urllib.parse import urlencode
            outputs = []
            for node in history['outputs'].values():
                for item in node.get('images', []):
                    if not item['filename'].lower().endswith('.mp4'):
                        continue
                    target = directory / Path(item['filename']).name
                    if not target.exists():
                        with urlopen(SERVER + '/view?' + urlencode(item), timeout=60) as response:
                            partial = target.with_suffix('.partial')
                            partial.write_bytes(response.read())
                            partial.replace(target)
                    metadata = inspect_video(target)
                    spec = read(directory / 'shot.json')
                    expected_frames = round(spec['seconds'] * 24)
                    expected_frames += (5 - expected_frames % 17) % 17
                    if (metadata['width'], metadata['height']) != (spec['width'], spec['height']) or metadata['fps'] != 24 or not metadata['audio_frames'] or metadata['decoded_frames'] != expected_frames:
                        raise ValueError('Output metadata does not match shot')
                    outputs.append({'path': str(target.resolve()), 'sha256': digest(target), **metadata})
            if not outputs:
                raise ValueError('Successful job has no MP4 output')
            job['outputs'] = outputs
    elif job['status'] == 'cancel_requested':
        queue = api('/queue')
        if job['prompt_id'] not in [item[1] for item in queue['queue_running'] + queue['queue_pending']]:
            job['status'] = 'cancelled'
    else:
        job['status'] = 'running'
    save(directory / 'job.json', job)
    return job


@contextmanager
def submission_lock():
    import msvcrt
    with (ROOT / '.submit.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def submit(spec_path):
    with submission_lock():
        return _submit(spec_path)


def _submit(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = read(spec_path)
    hashes = validate(spec)
    directory = spec_path.parent
    if (directory / 'job.json').exists():
        return refresh(directory)
    queue = api('/queue')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('ComfyUI is busy; wait before submitting')
    g = graph(spec, [upload(p) for p in spec['images']])
    nodes = api('/object_info')
    for node in g.values():
        if node['class_type'] not in nodes:
            raise ValueError('Missing node: ' + node['class_type'])
        for key in ('unet_name', 'clip_name', 'vae_name', 'lora_name'):
            if key in node['inputs']:
                definition = nodes[node['class_type']]['input']['required'][key]
                choices = definition[0] if isinstance(definition[0], list) else definition[1].get('options', [])
                if node['inputs'][key] not in choices:
                    raise ValueError('Missing model: ' + node['inputs'][key])
    save(directory / 'workflow-api.json', g)
    job = {'job_id': uuid.uuid4().hex, 'status': 'submitting', 'created': time.time(),
           'input_hashes': hashes, 'seed': spec['seed'], 'shot_hash': digest(spec_path),
           'workflow_hash': digest(directory / 'workflow-api.json')}
    # 제출 전에 상태를 저장해 응답 유실 시 중복 생성을 막는다.
    save(directory / 'job.json', job)
    try:
        response = api('/prompt', {'prompt': g, 'client_id': job['job_id'], 'extra_data': {'codex_job_id': job['job_id']}})
    except HTTPError as error:
        job['status'] = 'rejected' if error.code == 400 else 'submission_unknown'
        job['error'] = error.read().decode()
        save(directory / 'job.json', job)
        raise RuntimeError(job['error']) from error
    job.update(prompt_id=response['prompt_id'], status='submitted')
    save(directory / 'job.json', job)
    return job


async def watch(directory, seconds=45):
    import aiohttp
    job = refresh(directory)
    if job['status'] in ('failed', 'review_required', 'approved', 'cancelled', 'rejected'):
        return job
    deadline = time.monotonic() + seconds
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(SERVER.replace('http:', 'ws:') + '/ws?clientId=' + job['job_id']) as ws:
            while time.monotonic() < deadline:
                try:
                    event = await ws.receive(timeout=min(10, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    if api('/history/' + job['prompt_id']):
                        break
                    continue
                if event.type == aiohttp.WSMsgType.TEXT:
                    message = json.loads(event.data)
                    if message.get('data', {}).get('prompt_id', job['prompt_id']) != job['prompt_id']:
                        continue
                    if message['type'] in ('progress', 'executing', 'execution_error', 'execution_success'):
                        print(json.dumps(message, ensure_ascii=False), flush=True)
                    if message['type'] in ('execution_error', 'execution_success'):
                        break
                elif event.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
    return refresh(directory)


def cancel(directory):
    directory = Path(directory)
    job = read(directory / 'job.json')
    queue = api('/queue')
    pending_ids = [item[1] for item in queue['queue_pending']]
    running_ids = [item[1] for item in queue['queue_running']]
    if job.get('prompt_id') in pending_ids:
        api('/queue', {'delete': [job['prompt_id']]})
    elif running_ids == [job.get('prompt_id')]:
        api('/interrupt', {})
    else:
        raise ValueError('This job is not queued or is not the sole running job')
    job['status'] = 'cancel_requested'
    save(directory / 'job.json', job)
    return job


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['validate', 'submit', 'status', 'inspect', 'watch', 'cancel'])
    parser.add_argument('path')
    parser.add_argument('--seconds', type=int, default=45)
    args = parser.parse_args()
    if args.command == 'validate':
        result = {'valid': True, 'hashes': validate(read(args.path))}
    elif args.command == 'submit':
        result = submit(args.path)
    elif args.command == 'status':
        result = refresh(args.path)
    elif args.command == 'watch':
        if not 1 <= args.seconds <= 3600:
            parser.error('--seconds must be between 1 and 3600')
        result = asyncio.run(watch(args.path, args.seconds))
    elif args.command == 'cancel':
        result = cancel(args.path)
    else:
        result = inspect_video(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
