# 범용 숏 설정과 참조 이미지 및 연속 프레임을 H3 표준 노드에 연결한다.
import re
from pathlib import Path


class ShotSettings:
    CATEGORY = 'Codex Video'
    RETURN_TYPES = ('STRING', 'INT', 'INT', 'INT', 'INT', 'STRING', 'FLOAT')
    RETURN_NAMES = ('prompt', 'width', 'height', 'frames', 'steps', 'filename_prefix', 'turbo_strength')
    FUNCTION = 'run'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'prompt': ('STRING', {'multiline': True, 'default': 'Describe the action, setting, camera and sound here.'}),
            'width': ('INT', {'default': 864, 'min': 32, 'max': 1344, 'step': 32}),
            'height': ('INT', {'default': 480, 'min': 32, 'max': 1344, 'step': 32}),
            'seconds': ('FLOAT', {'default': 5.0, 'min': 2, 'max': 15}),
            'turbo': ('BOOLEAN', {'default': True}),
            'project': ('STRING', {'default': 'my_video'}),
            'shot': ('STRING', {'default': 'shot01'})}}

    def run(self, prompt, width, height, seconds, turbo, project, shot):
        if width % 32 or height % 32 or min(width, height) < 32 or width * height > 1344 * 768:
            raise ValueError('Use multiples of 32 within 1344 x 768 pixels.')
        if not 2 <= seconds <= 15 or not prompt.strip():
            raise ValueError('Provide a prompt and 2-15 seconds.')
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in (project, shot)):
            raise ValueError('Project and shot names accept letters, digits, underscores and hyphens.')
        frames = round(seconds * 24)
        frames += (5 - frames % 17) % 17
        return prompt, width, height, frames, 4 if turbo else 20, f'codex/{project}/{shot}', 1.0 if turbo else 0.0


class References:
    CATEGORY = 'Codex Video'
    RETURN_TYPES = ('CODEX_REFS',)
    RETURN_NAMES = ('references',)
    FUNCTION = 'run'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'roles': ('STRING', {'multiline': True, 'default': 'Subject identity and appearance.\nObject appearance.\nComposition only; replace primitive surfaces.'})},
                'optional': {f'image_{i}': ('IMAGE',) for i in range(1, 10)}}

    def run(self, roles, **images):
        connected = [(i, images[f'image_{i}']) for i in range(1, 10) if images.get(f'image_{i}') is not None]
        if [i for i, _ in connected] != list(range(1, len(connected) + 1)):
            raise ValueError('Connect images consecutively starting at image_1.')
        lines = roles.splitlines()
        if any(i > len(lines) or not lines[i - 1].strip() for i, _ in connected):
            raise ValueError('Write one role per connected image, in input order.')
        for _, image in connected:
            if image.ndim != 4 or image.shape[0] != 1:
                raise ValueError('Each reference must be one image, not a batch.')
        return ({'images': [image for _, image in connected], 'roles': lines[:len(connected)]},)


class LastFrame:
    CATEGORY = 'Codex Video'
    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('last_frame',)
    FUNCTION = 'run'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'enabled': ('BOOLEAN', {'default': False}),
                             'video_path': ('STRING', {'default': ''})}}

    @classmethod
    def IS_CHANGED(cls, enabled, video_path):
        if not enabled:
            return False
        path = Path(video_path)
        info = path.stat()
        return str(path.resolve()), info.st_size, info.st_mtime_ns

    def run(self, enabled, video_path):
        if not enabled:
            return (None,)
        import av
        import numpy as np
        import torch
        path = Path(video_path)
        if not path.is_absolute() or not path.is_file():
            raise ValueError('Choose an existing absolute local video path.')
        last = None
        with av.open(str(path)) as source:
            for frame in source.decode(video=0):
                last = frame
        if last is None:
            raise ValueError('Video has no decodable frames.')
        return (torch.from_numpy(last.to_ndarray(format='rgb24').astype(np.float32) / 255).unsqueeze(0),)


class H3Inputs:
    CATEGORY = 'Codex Video'
    RETURN_TYPES = ('CONDITIONING', 'LATENT', 'STRING')
    RETURN_NAMES = ('conditioning', 'latent', 'resolved_prompt')
    FUNCTION = 'run'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'clip': ('CLIP',), 'vae': ('VAE',), 'audio_vae': ('VAE',),
                             'references': ('CODEX_REFS',), 'prompt': ('STRING', {'forceInput': True}),
                             'width': ('INT', {'forceInput': True}), 'height': ('INT', {'forceInput': True}),
                             'frames': ('INT', {'forceInput': True})},
                'optional': {'first_frame': ('IMAGE',)}}

    def run(self, clip, vae, audio_vae, references, prompt, width, height, frames, first_frame=None):
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo, MiniMaxH3AddGuide
        images, roles = list(references['images']), list(references['roles'])
        if first_frame is not None:
            images.append(first_frame)
            roles.append('Previous ending. Continue the same subjects, objects, setting and camera from this frame.')
        if not 1 <= len(images) <= 9:
            raise ValueError('Use 1-9 references total, including the continuity frame.')
        tags = re.findall(r'<(Picture|Video|Audio)\s+(\d+)>', prompt)
        if any(kind != 'Picture' or not 1 <= int(n) <= len(images) for kind, n in tags):
            raise ValueError('Prompt references a missing image, video or audio input.')
        resolved = prompt + '\n' + '\n'.join(f'<Picture {i}>: {role}' for i, role in enumerate(roles, 1))
        result = MiniMaxH3ReferenceToVideo.execute(clip=clip, vae=vae, audio_vae=audio_vae,
            prompt=resolved, width=width, height=height, length=frames,
            ref_images={f'ref_image_{i}': image for i, image in enumerate(images)})
        conditioning, latent = result[0], result[1]
        if first_frame is not None:
            conditioning = MiniMaxH3AddGuide.execute(positive=conditioning, latent=latent,
                frame_idx=0, vae=vae, image=first_frame)[0]
        return conditioning, latent, resolved


NODE_CLASS_MAPPINGS = {'CodexShotSettings': ShotSettings, 'CodexReferences': References,
                       'CodexLastFrame': LastFrame, 'CodexH3Inputs': H3Inputs}
NODE_DISPLAY_NAME_MAPPINGS = {'CodexShotSettings': 'Codex · Shot Settings',
    'CodexReferences': 'Codex · Reference Images & Roles', 'CodexLastFrame': 'Codex · Previous Video Last Frame',
    'CodexH3Inputs': 'Codex · H3 Shot Inputs'}
