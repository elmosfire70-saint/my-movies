# 저장된 H3 실행 이력에서 동일 입력 비교 시간과 출력 검증 정보를 추출한다.
import pipeline as p

base = p.ROOT / 'projects/h3_baseline/shots'
results = {}
specs = {}
for mode in ('single_turbo', 'single_full'):
    job = p.read(base / mode / 'job.json')
    timestamps = {item[0]: item[1]['timestamp'] for item in job['server_status']['messages'] if 'timestamp' in item[1]}
    results[mode] = {'seconds': (timestamps['execution_success'] - timestamps['execution_start']) / 1000,
                     'prompt_id': job['prompt_id'], 'output': job['outputs'][0]}
    specs[mode] = p.read(base / mode / 'shot.json')
results['controlled_inputs_equal'] = all(specs['single_turbo'][key] == specs['single_full'][key]
    for key in ('images', 'prompt', 'width', 'height', 'seconds', 'seed'))
results['speed_ratio'] = results['single_full']['seconds'] / results['single_turbo']['seconds']
results['note'] = 'One run per configuration, cached nodes present. Not a universal performance guarantee.'
p.save(base.parent / 'comparison.json', results)
print(p.json.dumps(results, ensure_ascii=False, indent=2))
