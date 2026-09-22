# 공식 Qwen 모델을 이어받고 SHA256을 검증해 ComfyUI 모델 폴더에 설치한다.
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

MODELS = [
    ('Comfy-Org/Qwen-Image-Edit_ComfyUI', 'diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors', 20533762817, 'c9fdc158e46d3b61ef75f21ae866ca2fe808bf4a53643120d1c1e87c19280a4e'),
    ('Comfy-Org/Qwen-Image_ComfyUI', 'text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors', 9384670680, 'cb5636d852a0ea6a9075ab1bef496c0db7aef13c02350571e388aea959c5c0b4'),
    ('Comfy-Org/Qwen-Image_ComfyUI', 'vae/qwen_image_vae.safetensors', 253806246, 'a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f'),
]


def verify(path, size, digest):
    if path.stat().st_size != size:
        raise ValueError(f'Unexpected size: {path}')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != digest:
        raise ValueError(f'SHA256 mismatch: {path}; retained for inspection')


def install(root):
    root = Path(root).resolve()
    if not (root / 'main.py').is_file():
        raise ValueError('Select the ComfyUI root containing main.py')
    needed = sum(size for _, rel, size, _ in MODELS if not (root / 'models' / rel).exists())
    if shutil.disk_usage(root).free < needed + 2_000_000_000:
        raise ValueError('Insufficient disk space')
    for repo, rel, size, digest in MODELS:
        target = root / 'models' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            verify(target, size, digest)
            print(f'Already verified: {target.name}', flush=True)
            continue
        part = target.with_suffix('.safetensors.part')
        print(f'Downloading {target.name} ({size} bytes)', flush=True)
        subprocess.run(['curl.exe', '--fail', '--location', '--retry', '4', '--connect-timeout', '30',
                        '--speed-time', '120', '--speed-limit', '1024', '--continue-at', '-',
                        '--output', str(part), '--silent', '--show-error',
                        f'https://huggingface.co/{repo}/resolve/main/split_files/{rel}'], check=True)
        verify(part, size, digest)
        part.rename(target)
        print(f'SHA256 verified: {target.name}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('comfy_root')
    install(parser.parse_args().comfy_root)
