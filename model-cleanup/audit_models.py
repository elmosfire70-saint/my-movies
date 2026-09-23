# 저장된 ComfyUI 워크플로와 설치 모델 파일의 참조 관계를 조사한다.
import json
from pathlib import Path

project = Path(__file__).resolve().parents[1]
comfy = Path(r'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI')
workflow_dir = comfy / 'user' / 'default' / 'workflows'
model_roots = [comfy / 'models', Path(r'J:\LTX2.5')]
workflows = sorted(workflow_dir.rglob('*.json'))
workflow_text = {str(path): path.read_text(encoding='utf-8').casefold() for path in workflows}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for part in value.values():
            yield from strings(part)
    elif isinstance(value, list):
        for part in value:
            yield from strings(part)


model_suffixes = ('.safetensors', '.gguf', '.ckpt', '.pt', '.pth', '.bin')
references = {
    str(path): sorted({Path(value).name for value in strings(json.loads(path.read_text(encoding='utf-8')))
                       if value.casefold().endswith(model_suffixes)})
    for path in workflows
}
model_files = sorted(
    path for root in model_roots if root.exists()
    for path in root.rglob('*') if path.is_file() and path.stat().st_size > 1024 * 1024
)
rows = []
for path in model_files:
    users = [name for name, content in workflow_text.items() if path.name.casefold() in content]
    rows.append({'path': str(path), 'bytes': path.stat().st_size, 'saved_workflows': users})
available = {path.name.casefold() for path in model_files}
unresolved = {name: [model for model in names if model.casefold() not in available]
              for name, names in references.items()}
report = {'workflow_count': len(workflows), 'workflows': references, 'models': rows,
          'unresolved_models': {name: names for name, names in unresolved.items() if names}}
(project / 'model-cleanup' / 'inventory.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for row in rows:
    print(f"{row['bytes'] / 1e9:.2f} GB | {len(row['saved_workflows'])} saved | {row['path']}")
print('unresolved model names:', report['unresolved_models'])
