# 과거·현재 사진 두 장으로 만남 장면과 무음 H3 영상 워크플로를 만든다.
import json
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'character-sheet-comfy'))
from build_workflows import Graph, loaders, ui_workflow as base_ui_workflow

ROOT = Path(__file__).resolve().parent


def add_still(g):
    model, clip, vae = loaders(g)
    past = g.add('LoadImage', '01 과거 사진 · 한 사람', 0, 100, image='child-face.jpg')
    present = g.add('LoadImage', '02 현재 사진 · 같은 사람의 현재 모습', 0, 600,
                    image='adult-face-new.png')
    past = g.add('ImageScaleToMaxDimension', '과거 참조 · 비율 유지', 370, 100,
                 image=past, upscale_method='lanczos', largest_size=1024)
    present = g.add('ImageScaleToMaxDimension', '현재 참조 · 비율 유지', 370, 600,
                    image=present, upscale_method='lanczos', largest_size=1024)
    background = g.add('LoadImage', '03 선택 배경 사진 · enable을 켠 경우만 사용', 0, 1100,
                       image='meeting-background-neutral.png')
    background = g.add('ImageScaleToMaxDimension', '배경 참조 · 비율 유지', 370, 1100,
                       image=background, upscale_method='lanczos', largest_size=1024)
    enable = g.add('PrimitiveBoolean', 'enable · 배경 이미지 사용 ON / OFF', 750, 1100,
                   value=False)
    background = g.add('ComfySwitchNode', '배경 이미지 전달 · OFF는 제외', 750, 1450,
                       switch=enable, on_true=background)
    canvas = g.add('EmptyImage', '세로 9:16 캔버스', 750, 0,
                   width=576, height=1024, batch_size=1, color=0xC7C7C7)
    prompt = (
        'Replace the blank canvas in <image1> with ONE photorealistic vertical 9:16 photograph of '
        'a person meeting their younger self. <image2> is the PAST reference, placed on the LEFT. '
        '<image3> is the PRESENT reference, placed on the RIGHT. Render exactly two people, one '
        'version from each reference. Preserve each version independently: visible age, face shape, '
        'eyes and brows, nose, lips, skin tone, hairstyle, body proportions and expression. Do not '
        'average their faces, swap identities, turn both into children, or make both the same age. '
        'Each person retains their OWN clothing, headwear and accessories from their OWN reference. '
        'Do not transfer clothes or headwear between people or invent a uniform. Preserve headwear '
        'fit and direction. If a reference is a portrait, infer unseen body and clothing conservatively '
        'from its visible neckline, fabric and colors; do not invent elaborate unseen details. '
        'Create a warm reunion portrait with the two versions close together. If the younger version '
        'is a child, the present-day version kneels or sits at a comfortable height beside them. '
        'Otherwise both stand or sit naturally side by side. The present-day version rests one relaxed '
        'hand lightly on the younger version’s outer shoulder. Keep the hand away from faces. '
        'Both faces are initially near frontal and clearly visible, with soft natural smiles. '
        'Use a medium-wide composition showing both heads, shoulders, hands and at least their knees; '
        'leave clear space around the two heads and at both sides so a slight head turn stays in frame. '
        'Match a single camera perspective, plausible age-relative scale, light direction and contact '
        'shadows. If a FOURTH reference image is provided, use it ONLY as the selected environment: '
        'preserve its recognizable setting, architecture, landscape, colors, perspective and lighting. '
        'Place both people naturally into that setting with matching scale, light and ground shadows. '
        'The fourth image overrides the backgrounds of BOTH person photos; do not blend locations. '
        'Ignore any people, faces, clothing, text and watermarks in the background reference; it must '
        'never change either person’s identity or outfit. If there are only THREE reference images, '
        'use the setting visible in the PAST photo, excluding bystanders. If no setting is visible, '
        'use a simple softly blurred daylight outdoor background. '
        'Ignore cutout transparency, borders and studio backdrops in the PRESENT photo. The people '
        'must occupy the same physical space, not pasted panels. Natural skin texture and hands, '
        'nostalgic family-photo atmosphere. No additional people, split screen, collage, before/after '
        'divider, age labels, captions, speech bubbles, subtitles, watermark or extra limbs. '
        'Render one opaque RGB scene.'
    )
    enabled_prompt = prompt.replace(
        'If a FOURTH reference image is provided,',
        'BACKGROUND REPLACEMENT IS ENABLED. There are exactly FOUR references. <image4> is '
        'the mandatory background. Completely REPLACE the original backgrounds of <image2> '
        'and <image3> with <image4>. Never retain the original ocean, mountains, room or studio '
        'unless those appear in <image4>. A plain-color fourth image means a plain studio backdrop '
        'of that color; do not invent an outdoor setting. For this image,')
    enabled_prompt = enabled_prompt.replace(
        'If there are only THREE reference images, '
        'use the setting visible in the PAST photo, excluding bystanders. If no setting is visible, '
        'use a simple softly blurred daylight outdoor background. ', '')
    default_text = g.add('PrimitiveStringMultiline', '배경 OFF · 과거 사진의 장소 사용', 1100, 750,
                         value=prompt)
    background_text = g.add('PrimitiveStringMultiline', '배경 ON · 선택 배경으로 교체', 1100, 1100,
                            value=enabled_prompt)
    selected_prompt = g.add('ComfySwitchNode', '배경 상태에 맞는 합성 지시', 1100, 1450,
                            switch=enable, on_false=default_text, on_true=background_text)
    encoded = g.add('TextEncodeQwenImage21', '07 두 시점 합성 지시', 1500, 750,
                    clip=clip, vae=vae, prompt=selected_prompt, negative_prompt='', resolution=0,
                    **{'images.image_1': canvas, 'images.image_2': past,
                       'images.image_3': present, 'images.image_4': background})
    sampled = g.add('KSampler', '08 정지 장면 생성', 1450, 0,
                    model=model, positive=encoded, negative=[encoded[0], 1],
                    latent_image=[encoded[0], 2], seed=20261003, steps=25, cfg=1.0,
                    sampler_name='euler', scheduler='simple', denoise=1.0)
    decoded = g.add('VAEDecodeTiled', '09 디코딩', 1800, 0, samples=sampled,
                    vae=vae, tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    rgb = g.add('SplitImageWithAlpha', '10 RGB', 2150, 0, image=decoded)
    g.add('SaveImage', '11 시작 장면 PNG', 2500, 0, images=rgb,
          filename_prefix='past-present/two-photo-still')
    return rgb


def still_graph():
    g = Graph()
    add_still(g)
    return g


def add_video(g, front, offset=0):
    start = len(g.layout)
    settings = g.add('CodexShotSettings', '02 동작·길이·해상도', 0, 430,
                     prompt=('One continuous photorealistic shot. <Picture 1> is the exact opening '
                             'frame and defines BOTH versions of the same person and their shared setting. '
                             'The PAST version stays on the LEFT; the PRESENT version stays on the RIGHT. '
                             'Preserve each face, visible age, hairstyle, clothing, headwear, relative size '
                             'and seated or standing pose exactly as in the opening frame. '
                             'At the beginning, hold the reunion portrait with subtle breathing and blinking. '
                             'Through the middle of the shot, they slowly turn their eyes and heads slightly '
                             'toward each other, making warm eye contact without hiding either face. '
                             'Toward the end, the present-day version gives one tiny affectionate shoulder '
                             'pat with the hand already resting there; both settle into a gentle smile. '
                             'Keep the shoulder contact light and anatomically correct. No large reach, '
                             'hug, walking, lifting, head rubbing or abrupt body movement. '
                             'LOCKED WIDE CAMERA: fixed tripod, no zoom, no push-in, no pan, no '
                             'reframing. Both people stay completely visible in the frame from start '
                             'to finish with the original framing margins. Maintain their distinct ages, exact '
                             'identities, clothing, positions and anatomy. No other people, no face '
                             'morphing, no cuts, no text, no speaking mouth movements, no lip sync, '
                             'no dialogue, no singing, no narration, no audible laughter, no music and '
                             'no sound effects. Smiles and breathing only; this is a silent reunion.'),
                     width=576, height=1024, seconds=5.0, turbo=True,
                     project='past_present_two_photos', shot='silent_meeting')
    refs = g.add('CodexReferences', '시작 장면 외 추가 참조 없음', 350, 430,
                 roles='', enabled=False)
    model = g.add('UNETLoader', 'H3 ref2va INT8', 0, -500,
                  unet_name='minimax_h3_ref2va_pruned_int8_convrot.safetensors', weight_dtype='default')
    model = g.add('LoraLoaderModelOnly', 'H3 Turbo 4 step', 350, -500,
                  model=model, lora_name='minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors',
                  strength_model=1.0)
    clip = g.add('CLIPLoader', 'H3 Qwen3VL 32B', 0, -250,
                 clip_name='qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',
                 type='minimax', device='default')
    vae = g.add('VAELoader', 'H3 영상 VAE', 350, -250,
                vae_name='minimax_h3_video_vae_fp16.safetensors')
    audio_vae = g.add('VAELoader', 'H3 내부 조건용 VAE · 최종 음성 출력 없음', 700, -250,
                      vae_name='minimax_h3_audio_vae_fp32.safetensors')
    inputs = g.add('CodexH3Inputs', '03 첫 프레임 고정', 750, 0,
                   clip=clip, vae=vae, audio_vae=audio_vae, references=refs,
                   prompt=settings, width=[settings[0], 1], height=[settings[0], 2],
                   frames=[settings[0], 3], first_frame=front)
    noise = g.add('RandomNoise', '고정 시드', 750, 430, noise_seed=20261003)
    sampler = g.add('KSamplerSelect', 'H3 샘플러', 1100, 430, sampler_name='res_multistep')
    sigmas = g.add('BasicScheduler', '4단계 스케줄', 1100, 700,
                   model=model, scheduler='simple', steps=4, denoise=1.0)
    guider = g.add('BasicGuider', '영상 가이드', 1100, 0,
                   model=model, conditioning=inputs)
    sampled = g.add('SamplerCustomAdvanced', '04 영상 생성', 1450, 0,
                    noise=noise, guider=guider, sampler=sampler, sigmas=sigmas,
                    latent_image=[inputs[0], 1])
    decoded = g.add('VAEDecode', '05 영상 프레임', 1800, 0,
                    samples=sampled, vae=vae)
    video = g.add('CreateVideo', '07 무음 24fps MP4', 2150, 0,
                  images=decoded, fps=24.0, bit_depth=8, color_space='sRGB')
    g.add('SaveVideo', '08 최종 영상', 2500, 0, video=video,
          filename_prefix='past-present/two-photo-video-silent', format='auto', codec='auto')
    for key in list(g.layout)[start:]:
        g.layout[key][0] += offset


def video_graph():
    g = Graph()
    front = g.add('LoadImage', '01 선택한 두 인물 시작 장면', 0, 0,
                  image='past-present/two-photo-still_00001_.png [output]')
    add_video(g, front)
    return g


def meeting_graph():
    g = Graph()
    front = add_still(g)
    add_video(g, front, offset=3000)
    return g


def ui_workflow(g, info):
    workflow = base_ui_workflow(g, info)
    # 저장된 스위치의 동적 포트를 연결된 이미지·문자열 타입으로 명시한다.
    switches = {}
    for key, node in g.api.items():
        if node['class_type'] == 'ComfySwitchNode':
            source, slot = node['inputs']['on_true']
            switches[int(key)] = info[g.api[source]['class_type']]['output'][slot]
    for node in workflow['nodes']:
        if node['id'] in switches:
            for port in node['inputs'] + node['outputs']:
                if port['type'] == 'COMFY_MATCHTYPE_V3':
                    port['type'] = switches[node['id']]
    for link in workflow['links']:
        if link[1] in switches:
            link[5] = switches[link[1]]
        elif link[3] in switches and link[5] == 'COMFY_MATCHTYPE_V3':
            link[5] = switches[link[3]]
    return workflow


def build():
    with urlopen('http://127.0.0.1:8188/object_info') as response:
        info = json.load(response)
    output = ROOT / 'workflows'
    output.mkdir(exist_ok=True)
    for name, graph in [('00_Past_Present_Two_Photos', meeting_graph()),
                        ('01_Past_Present_Still', still_graph()),
                        ('02_Past_Present_Video', video_graph())]:
        (output / (name + '.api.json')).write_text(
            json.dumps(graph.api, ensure_ascii=False, indent=2), encoding='utf-8')
        (output / (name + '.json')).write_text(
            json.dumps(ui_workflow(graph, info), ensure_ascii=False, indent=2), encoding='utf-8')
        print(name, len(graph.api), 'nodes')


if __name__ == '__main__':
    build()
