# 공식 Qwen 모델을 이어받고 SHA256을 검증해 ComfyUI 모델 폴더에 설치한다.
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

MODELS = [
    ('Comfy-Org/Qwen-Image-2.1', 'diffusion_models/qwen_image_2.1_int8_convrot.safetensors', 7256783064, 'cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d'),
    ('Comfy-Org/Qwen-Image-2.1', 'text_encoders/qwen3vl_8b_int8_convrot.safetensors', 9350798360, '8bfd0f6e12abf2d2d697ecc888e5e90b0d6741d6708f05799f53afa560452e8f'),
    ('Comfy-Org/Qwen-Image-2.1', 'vae/qwen_image_2.1_vae_bf16.safetensors', 675509688, 'bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9'),
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
    needed = sum(max(0, size - ((root / 'models' / rel).with_suffix('.safetensors.part').stat().st_size
                               if (root / 'models' / rel).with_suffix('.safetensors.part').exists() else 0))
                 for _, rel, size, _ in MODELS if not (root / 'models' / rel).exists())
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
                        f'https://huggingface.co/{repo}/resolve/main/{rel}'], check=True)
        verify(part, size, digest)
        part.rename(target)
        print(f'SHA256 verified: {target.name}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('comfy_root')
    install(parser.parse_args().comfy_root)
