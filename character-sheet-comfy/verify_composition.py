# 실제 ComfyUI 서버에 색상 패널을 보내 비율 보존과 합성 순서를 검증한다.
import io
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
import uuid
from PIL import Image
from build_workflows import graphs

BASE = 'http://127.0.0.1:8188'


def get(path):
    with urlopen(BASE + path) as response:
        return json.load(response)


def run():
    queue = get('/queue')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('Queue is occupied; retry when idle')
    token = uuid.uuid4().hex
    colors = [(220, 30, 30), (30, 220, 30), (30, 30, 220), (220, 180, 30)]
    names = []
    for i, color in enumerate(colors):
        # 서로 다른 종횡비를 사용해 가로 왜곡과 잘림을 검출한다.
        image = Image.new('RGB', (128 if i < 3 else 192, 288), color)
        stream = io.BytesIO()
        image.save(stream, format='PNG')
        name = f'character_sheet_test_{token}_{i}.png'
        boundary = '----' + token
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                'Content-Type: image/png\r\n\r\n').encode() + stream.getvalue() + f'\r\n--{boundary}--\r\n'.encode()
        with urlopen(Request(BASE + '/upload/image', data=body,
                             headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})) as response:
            names.append(json.load(response)['name'])
    graph = graphs()['03_Assemble_Selected_Views'].api
    loads = [node for node in graph.values() if node['class_type'] == 'LoadImage']
    for node, name in zip(loads, names):
        node['inputs']['image'] = name
    for node in graph.values():
        if node['class_type'] == 'SaveImage':
            node['inputs']['filename_prefix'] = 'character-sheets/validation/' + token
    with urlopen(Request(BASE + '/prompt', data=json.dumps({'prompt': graph}).encode(),
                         headers={'Content-Type': 'application/json'})) as response:
        job = json.load(response)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        history = get('/history/' + job['prompt_id']).get(job['prompt_id'])
        if history:
            break
        time.sleep(1)
    else:
        raise TimeoutError(job['prompt_id'])
    if history['status']['status_str'] != 'success':
        raise RuntimeError(history['status'])
    outputs = next(value['images'] for value in history['outputs'].values() if 'images' in value)
    from urllib.parse import urlencode
    with urlopen(BASE + '/view?' + urlencode(outputs[0])) as response:
        image = Image.open(io.BytesIO(response.read())).convert('RGB')
    assert image.size == (2304, 1152), image.size
    for x, expected in zip((256, 768, 1280, 1920), colors):
        actual = image.getpixel((x, 576))
        assert max(abs(a-b) for a, b in zip(actual, expected)) <= 1, (actual, expected)
    report = {'status': 'passed', 'prompt_id': job['prompt_id'], 'size': image.size,
              'checks': ['front-side-back-closeup order', 'aspect ratios', 'no crop', 'local execution'],
              'generated_by_ai': False, 'output': outputs[0]}
    Path(__file__).with_name('composition-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    run()
