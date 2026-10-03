# 어린 시절과 성인의 해변 만남 정지 장면과 H3 영상 워크플로를 만든다.
import json
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'character-sheet-comfy'))
from build_workflows import Graph, loaders, ui_workflow

ROOT = Path(__file__).resolve().parent


def still_graph():
    g = Graph()
    model, clip, vae = loaders(g)
    sheet = g.add('LoadImage', '01 성인 캐릭터 시트', 0, 0, image='adult-sheet.png')
    adult = g.add('ImageCrop', '02 성인 정면만', 350, 0, image=sheet,
                  x=0, y=0, width=512, height=1152)
    adult_face = g.add('LoadImage', '03 새 성인 얼굴 원본', 350, 350,
                       image='adult-face-new.png')
    child1 = g.add('LoadImage', '04 어린 시절 해변 사진', 0, 550, image='child-seaside.jpg')
    child2 = g.add('LoadImage', '05 어린 시절 얼굴 확대', 0, 1000, image='child-face.jpg')
    child3 = g.add('LoadImage', '06 어린 시절 다른 표정', 0, 1450, image='child-smile.jpg')
    canvas = g.add('EmptyImage', '세로 9:16 캔버스', 750, 0,
                   width=576, height=1024, batch_size=1, color=0xC7C7C7)
    prompt = (
        'Replace the blank canvas in <image1> with ONE realistic vertical cinematic photograph. '
        'Images <image2> and <image3> are the SAME young adult man: <image2> defines his full olive '
        'military flight suit, bright red-orange scarf and black shoes; '
        '<image3> is the authoritative reference for his facial identity and low black beret: preserve '
        'the eye shape and spacing, brows, nose, lips, jawline, skin tone, clean-shaven face and the '
        'beret sitting naturally close to his eyebrows. Ignore the face in <image2> if it differs. '
        'Images <image4>, <image5>, <image6> are the SAME Korean boy aged about '
        'six in 2005; preserve his smiling face, short black hair, white sleeveless shirt with green trim '
        'and little blue car print. Create exactly TWO distinct people together in one coherent seaside '
        'photograph: the boy on the left and his older self on the right. The adult crouches to the boy’s '
        'height and gently places his right hand on the boy’s shoulder. The boy laughs naturally and '
        'looks toward the adult; the adult gives him a warm small smile. Medium three-quarter portrait '
        'showing both from head to at least knees, no overlapping or duplicated faces. They share the '
        'same physical ground, camera perspective, soft daylight and believable contact shadows. '
        'Behind them: calm gray-blue sea, distant hazy hills and one subtle fishing boat, like the child '
        'photographs. Candid family-photo realism, natural skin and hands, quiet nostalgic mood. '
        'Do not copy the source photo as a panel or paste an existing cutout. No third person, '
        'split screen, collage, title, subtitles, watermark or extra limbs. Render an opaque image.'
    )
    encoded = g.add('TextEncodeQwenImage21', '07 두 시점 합성 지시', 1100, 0,
                    clip=clip, vae=vae, prompt=prompt, negative_prompt='', resolution=0,
                    **{'images.image_1': canvas, 'images.image_2': adult,
                       'images.image_3': adult_face, 'images.image_4': child1,
                       'images.image_5': child2, 'images.image_6': child3})
    sampled = g.add('KSampler', '08 정지 장면 생성', 1450, 0,
                    model=model, positive=encoded, negative=[encoded[0], 1],
                    latent_image=[encoded[0], 2], seed=20261003, steps=25, cfg=1.0,
                    sampler_name='euler', scheduler='simple', denoise=1.0)
    decoded = g.add('VAEDecodeTiled', '09 디코딩', 1800, 0, samples=sampled,
                    vae=vae, tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    rgb = g.add('SplitImageWithAlpha', '10 RGB', 2150, 0, image=decoded)
    g.add('SaveImage', '11 시작 장면 PNG', 2500, 0, images=rgb,
          filename_prefix='past-present/meeting-still')
    return g


def video_graph():
    g = Graph()
    front = g.add('LoadImage', '01 선택한 두 인물 시작 장면', 0, 0,
                  image='past-present/meeting-still_00002_.png [output]')
    settings = g.add('CodexShotSettings', '02 동작·길이·해상도', 0, 430,
                     prompt=('One continuous photorealistic shot. <Picture 1> is the exact opening '
                             'frame and defines both people and the seaside. Keep the young Korean boy '
                             'on the left in the white green-trim sleeveless car shirt and his adult '
                             'self on the right in the olive flight suit, bright red scarf and low '
                             'black beret. The adult keeps one hand gently on the boy’s shoulder. '
                             'They look at each other and exchange small natural smiles without talking. '
                             'Very subtle breathing, blinking, sea breeze moving hair and scarf. '
                             'LOCKED WIDE CAMERA: fixed tripod, no zoom, no push-in, no pan, no '
                             'reframing. Both people stay completely visible in the frame from start '
                             'to finish with empty space around them. Maintain their distinct ages, exact '
                             'identities, clothing, positions and anatomy. No other people, no face '
                             'morphing, no cuts, no text, no speaking mouth movements, no lip sync, '
                             'no dialogue.'),
                     width=576, height=1024, seconds=5.0, turbo=True,
                     project='past_present_2005_2026', shot='meeting')
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
    audio_vae = g.add('VAELoader', 'H3 오디오 VAE', 700, -250,
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
          filename_prefix='past-present/meeting-video-silent', format='auto', codec='auto')
    return g


def build():
    with urlopen('http://127.0.0.1:8188/object_info') as response:
        info = json.load(response)
    output = ROOT / 'workflows'
    output.mkdir(exist_ok=True)
    for name, graph in [('01_Past_Present_Still', still_graph()),
                        ('02_Past_Present_Video', video_graph())]:
        (output / (name + '.api.json')).write_text(
            json.dumps(graph.api, ensure_ascii=False, indent=2), encoding='utf-8')
        (output / (name + '.json')).write_text(
            json.dumps(ui_workflow(graph, info), ensure_ascii=False, indent=2), encoding='utf-8')
        print(name, len(graph.api), 'nodes')


if __name__ == '__main__':
    build()
