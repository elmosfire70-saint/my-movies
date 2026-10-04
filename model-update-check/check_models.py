# 설치 모델을 배포 저장소 최신 SHA256과 비교한다.
import json, urllib.request, hashlib
from pathlib import Path
root=Path(r'E:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/models')
report=[]
for repo in ['Comfy-Org/Qwen-Image-2.1','Comfy-Org/MiniMax-H3']:
    data=json.load(urllib.request.urlopen('https://huggingface.co/api/models/'+repo+'?blobs=true',timeout=45))
    print('REPO',repo,data['sha'],flush=True)
    for item in data['siblings']:
        rel=item['rfilename']; p=root/rel
        expected=item.get('lfs',{}).get('sha256')
        if not p.is_file() or not expected or not rel.endswith('.safetensors'): continue
        print('HASHING',rel,flush=True)
        with p.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
        row=dict(repo=repo,revision=data['sha'],file=rel,size=p.stat().st_size,expected=expected,actual=actual,matches=actual==expected)
        report.append(row); print('MATCH',row['matches'],flush=True)
    Path('model-update-check/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert len(report)>=8, 'Expected at least eight active model components'
assert all(r['matches'] for r in report), 'Updated or mismatched files found'
print('ALL_MATCH',len(report),flush=True)
