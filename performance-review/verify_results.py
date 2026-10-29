# 저장된 실측 기록과 생성 영상의 크기·프레임·무음 여부를 검증한다.
import json
from pathlib import Path

import av

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'output/performance-review/90bf391c-6aaf-482e-8425-ae889b7ffe95'
history = next(iter(json.loads((RUN / 'history.json').read_text()).values()))
assert history['status']['completed'] and history['status']['status_str'] == 'success'
output = history['outputs']['37']['images'][0]
video = Path('E:/Comfy-Desktop/ComfyUI-Shared/output') / output['subfolder'] / output['filename']
with av.open(str(video)) as container:
    stream = container.streams.video[0]
    assert (stream.width, stream.height) == (576, 1024)
    assert stream.average_rate == 24 and len(container.streams.audio) == 0
    count = 0
    for count, frame in enumerate(container.decode(video=0), 1):
        if count in (1, 62, 124):
            frame.to_image().save(RUN / f'frame-{count:03}.png')
    assert count == 124, count
times = {name: data.get('timestamp') for name, data in history['status']['messages']}
memory = json.loads((RUN / 'memory.json').read_text())
system = json.loads((RUN.parent / 'system_stats.json').read_text())['system']
metrics = {
    'total_seconds': (times['execution_success'] - times['execution_start']) / 1000,
    'frames': count, 'fps': 24, 'duration_seconds': count / 24, 'audio_streams': 0,
    'gpu_peak_sampled_mib': max(float(x['gpu_memory_utilization'].split(',')[0]) for x in memory),
    'system_ram_peak_sampled_gib': (system['ram_total'] - min(x['ram_available'] for x in memory)) / 1024**3,
    'memory_samples': len(memory), 'video': str(video),
}
(RUN / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
print(json.dumps(metrics, indent=2))
