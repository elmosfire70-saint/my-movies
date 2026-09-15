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
                'optional': {**{f'image_{i}': ('IMAGE', {'lazy': True}) for i in range(1, 10)},
                             'enabled': ('BOOLEAN', {'default': True})}}

    def check_lazy_status(self, roles, enabled=True, **images):
        return [name for name, value in images.items() if value is None] if enabled else []

    def run(self, roles, enabled=True, **images):
        if not enabled:
            return ({'images': [], 'roles': []},)
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


class PrevizVideo:
    CATEGORY = 'Codex Video'
    RETURN_TYPES = ('CODEX_VIDEO_REF', 'IMAGE', 'STRING')
    RETURN_NAMES = ('video_reference', 'preview_frames', 'info')
    FUNCTION = 'run'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'enabled': ('BOOLEAN', {'default': False}),
            'video_path': ('STRING', {'default': ''}),
            'role': ('STRING', {'multiline': True, 'default': 'Use camera movement, timing and blocking only. Replace primitive geometry with the subjects and appearance from the image references.'}),
            'max_frames': ('INT', {'default': 124, 'min': 5, 'max': 362, 'forceInput': True}),
            'max_edge': ('INT', {'default': 864, 'min': 32, 'max': 1344, 'step': 32})}}

    @classmethod
    def IS_CHANGED(cls, enabled, video_path, **kwargs):
        return LastFrame.IS_CHANGED(enabled, video_path)

    def run(self, enabled, video_path, role, max_frames, max_edge):
        if not enabled:
            return None, None, 'Video reference disabled.'
        import av
        import numpy as np
        import torch
        path = Path(video_path)
        if not path.is_absolute() or not path.is_file():
            raise ValueError('Choose an existing absolute local previz video path.')
        if not 5 <= max_frames <= 362 or not 32 <= max_edge <= 1344 or not role.strip():
            raise ValueError('Use 5-362 frames, 32-1344 maximum edge, and describe the video role.')
        frames = []
        previous = None
        previous_time = None
        origin = None
        size = None
        with av.open(str(path)) as source:
            stream = source.streams.video[0]
            rate = float(stream.average_rate or 24)
            for index, frame in enumerate(source.decode(video=0)):
                timestamp = float(frame.time) if frame.time is not None else index / rate
                if origin is None:
                    origin = timestamp
                timestamp -= origin
                if previous_time is not None and timestamp < previous_time:
                    raise ValueError('Video timestamps are not ordered.')
                if size is None:
                    scale = min(1., max_edge / max(frame.width, frame.height))
                    size = (max(32, int(frame.width * scale) // 32 * 32),
                            max(32, int(frame.height * scale) // 32 * 32))
                if previous is not None:
                    while len(frames) / 24 < timestamp - 1e-7 and len(frames) < max_frames:
                        frames.append(previous)
                if len(frames) >= max_frames:
                    break
                previous = frame.reformat(width=size[0], height=size[1], format='rgb24').to_ndarray()
                previous_time = timestamp
                end_time = timestamp + (float(frame.duration * frame.time_base) if frame.duration else 1 / rate)
            else:
                if previous is not None:
                    while len(frames) / 24 < end_time - 1e-7 and len(frames) < max_frames:
                        frames.append(previous)
        count = len(frames) - (len(frames) - 5) % 17
        if count < 5:
            raise ValueError('Video must contain at least 5 frames at 24fps.')
        batch = torch.from_numpy(np.stack(frames[:count])).float().div_(255)
        info = f'{count} frames, 24fps, {count / 24:.3f}s, {size[0]}x{size[1]}; audio ignored.'
        return {'frames': batch, 'role': role}, batch, info


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
                'optional': {'first_frame': ('IMAGE',), 'video_reference': ('CODEX_VIDEO_REF',)}}

    def run(self, clip, vae, audio_vae, references, prompt, width, height, frames, first_frame=None, video_reference=None):
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo, MiniMaxH3AddGuide
        images, roles = list(references['images']), list(references['roles'])
        if first_frame is not None:
            images.append(first_frame)
            roles.append('Previous ending. Continue the same subjects, objects, setting and camera from this frame.')
        if len(images) > 9 or (not images and video_reference is None):
            raise ValueError('Use up to 9 images and at least one image or video reference.')
        tags = re.findall(r'<(Picture|Video|Audio)\s+(\d+)>', prompt)
        limits = {'Picture': len(images), 'Video': int(video_reference is not None), 'Audio': 0}
        if any(not 1 <= int(n) <= limits[kind] for kind, n in tags):
            raise ValueError('Prompt references a missing image, video or audio input.')
        resolved = prompt + '\n' + '\n'.join(f'<Picture {i}>: {role}' for i, role in enumerate(roles, 1))
        videos = None
        if video_reference is not None:
            videos = {'ref_video_0': video_reference['frames']}
            resolved += '\n<Video 1>: ' + video_reference['role']
        result = MiniMaxH3ReferenceToVideo.execute(clip=clip, vae=vae, audio_vae=audio_vae,
            prompt=resolved, width=width, height=height, length=frames,
            ref_images={f'ref_image_{i}': image for i, image in enumerate(images)}, ref_videos=videos)
        conditioning, latent = result[0], result[1]
        if first_frame is not None:
            conditioning = MiniMaxH3AddGuide.execute(positive=conditioning, latent=latent,
                frame_idx=0, vae=vae, image=first_frame)[0]
        return conditioning, latent, resolved


NODE_CLASS_MAPPINGS = {'CodexShotSettings': ShotSettings, 'CodexReferences': References,
                       'CodexLastFrame': LastFrame, 'CodexH3Inputs': H3Inputs, 'CodexPrevizVideo': PrevizVideo}
NODE_DISPLAY_NAME_MAPPINGS = {'CodexShotSettings': 'Codex · Shot Settings',
    'CodexReferences': 'Codex · Reference Images & Roles', 'CodexLastFrame': 'Codex · Previous Video Last Frame',
    'CodexH3Inputs': 'Codex · H3 Shot Inputs', 'CodexPrevizVideo': 'Codex · Previz Video Reference'}


def skip_disabled_image_inputs(data):
    # 화면의 연결은 유지하고 실행 요청의 꺼진 이미지 참조 연결만 제외한다.
    from copy import deepcopy
    prompt = data.get('prompt', {})
    disabled = [key for key, node in prompt.items() if node.get('class_type') == 'CodexReferences'
                and node.get('inputs', {}).get('enabled') is False]
    if not disabled:
        return data
    result = dict(data)
    result['prompt'] = deepcopy(prompt)
    for key in disabled:
        inputs = result['prompt'][key]['inputs']
        for index in range(1, 10):
            inputs.pop(f'image_{index}', None)
    return result


try:
    from server import PromptServer
except ImportError:
    pass  # ComfyUI 밖의 단위 테스트에서는 서버 훅을 등록하지 않는다.
else:
    PromptServer.instance.add_on_prompt_handler(skip_disabled_image_inputs)
