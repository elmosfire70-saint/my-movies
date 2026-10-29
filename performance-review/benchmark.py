# 현재 두 사진 영상 워크플로의 실행 시간과 GPU·RAM 사용을 기록한다.
import asyncio
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import aiohttp
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'past-present-comfy'))
from build_meeting_workflows import meeting_graph

BASE = 'http://127.0.0.1:8188'


async def main():
    client = str(uuid.uuid4())
    folder = ROOT / 'output' / 'performance-review' / client
    folder.mkdir(parents=True)
    graph = meeting_graph().api
    for node in graph.values():
        if node['class_type'] in ('SaveImage', 'SaveVideo'):
            node['inputs']['filename_prefix'] = 'performance-review/' + client
    (folder / 'request.json').write_text(json.dumps(graph, indent=2), encoding='utf-8')
    print('OUTPUT', folder, flush=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE + '/queue') as response:
            queue = await response.json()
        assert not queue['queue_running'] and not queue['queue_pending'], 'Queue must be idle'
        async with session.ws_connect(BASE + '/ws', params={'clientId': client}) as ws:
            async with session.post(BASE + '/prompt', json={'prompt': graph, 'client_id': client}) as response:
                job = await response.json()
                assert response.status == 200 and not job.get('node_errors'), job
            (folder / 'job.json').write_text(json.dumps(job), encoding='utf-8')
            prompt_id = job['prompt_id']
            print('JOB', prompt_id, flush=True)
            started = time.perf_counter()
            events, samples = [], []

            async def monitor():
                while True:
                    result = await asyncio.to_thread(subprocess.run, [
                        'nvidia-smi', '--query-gpu=memory.used,utilization.gpu',
                        '--format=csv,noheader,nounits'], capture_output=True, text=True)
                    ram = psutil.virtual_memory()
                    samples.append({'seconds': time.perf_counter() - started,
                                    'gpu_memory_utilization': result.stdout.strip(),
                                    'ram_available': ram.available})
                    await asyncio.sleep(5)

            task = asyncio.create_task(monitor())
            try:
                async for message in ws:
                    if message.type != aiohttp.WSMsgType.TEXT:
                        continue
                    event = json.loads(message.data)
                    if event.get('data', {}).get('prompt_id') != prompt_id:
                        continue
                    if event['type'] in ('executing', 'execution_start', 'execution_cached',
                                         'execution_success', 'execution_error', 'execution_interrupted'):
                        event['elapsed_seconds'] = time.perf_counter() - started
                        events.append(event)
                        print(json.dumps(event), flush=True)
                    if event['type'] in ('execution_success', 'execution_error', 'execution_interrupted'):
                        break
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                (folder / 'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
                (folder / 'memory.json').write_text(json.dumps(samples, indent=2), encoding='utf-8')
            async with session.get(BASE + '/history/' + prompt_id) as response:
                history = await response.json()
            (folder / 'history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
            assert history[prompt_id]['status']['status_str'] == 'success', 'Generation failed; inspect history'
            print('SUCCESS', folder, flush=True)


if __name__ == '__main__':
    asyncio.run(main())
