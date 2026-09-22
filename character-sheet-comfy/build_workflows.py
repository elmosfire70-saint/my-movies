# 얼굴·의상 참조로 정면과 턴어라운드를 만드는 표준 ComfyUI 워크플로를 생성한다.
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
NEGATIVE = 'multiple people, duplicate person, collage, text, watermark, cropped feet, cropped head, extra limbs, deformed hands, different clothes, different identity, fisheye'
STUDIO = ('Photorealistic studio character reference. Exactly one person, plain neutral light gray background, '
          'soft even light, realistic skin and fabric. No text, no panels, no props unless part of the outfit. ')
BODY = ('Entire body including head and both shoes, centered, 6 percent margin above and below, '
        'relaxed upright neutral stance, arms slightly away from torso, hands empty. '
        'Eye-level camera, natural long-lens perspective, no foreshortening. ')


class Graph:
    def __init__(self):
        self.api, self.layout = {}, {}

    def add(self, kind, title, x, y, **inputs):
        key = str(len(self.api) + 1)
        self.api[key] = {'class_type': kind, 'inputs': inputs, '_meta': {'title': title}}
        self.layout[key] = [x, y]
        return [key, 0]


def loaders(g):
    model = g.add('UNETLoader', 'Qwen Edit 2511 · FP8 mixed', 0, -450,
                  unet_name='qwen_image_edit_2511_fp8mixed.safetensors', weight_dtype='default')
    model = g.add('ModelSamplingAuraFlow', 'Flow shift 3.1', 370, -450, model=model, shift=3.1)
    model = g.add('CFGNorm', 'CFG normalization', 740, -450, model=model, strength=1.0, pre_cfg=False)
    clip = g.add('CLIPLoader', 'Qwen vision-language encoder', 0, -200,
                 clip_name='qwen_2.5_vl_7b_fp8_scaled.safetensors', type='qwen_image', device='default')
    vae = g.add('VAELoader', 'Qwen VAE', 370, -200, vae_name='qwen_image_vae.safetensors')
    return model, clip, vae


def generate(g, resources, refs, prompt, label, y, width, seed):
    model, clip, vae = resources
    images = {f'image{i+1}': ref for i, ref in enumerate(refs)}
    conditioning = []
    for index, text in enumerate((prompt, NEGATIVE)):
        c = g.add('TextEncodeQwenImageEditPlus', label + (' · 지시문' if index == 0 else ' · 제외'),
                  750, y + index * 310, clip=clip, vae=vae, prompt=text, **images)
        c = g.add('FluxKontextMultiReferenceLatentMethod', label + ' · 참조 정렬',
                  1130, y + index * 220, conditioning=c, reference_latents_method='index_timestep_zero')
        conditioning.append(c)
    latent = g.add('EmptySD3LatentImage', label + ' · 출력 크기', 1130, y + 450,
                   width=width, height=1152, batch_size=1)
    sampled = g.add('KSampler', label + ' · 생성', 1500, y, model=model, positive=conditioning[0],
                    negative=conditioning[1], latent_image=latent, seed=seed, steps=20, cfg=4.0,
                    sampler_name='euler', scheduler='simple', denoise=1.0)
    decoded = g.add('VAEDecodeTiled', label + ' · 타일 디코딩', 1870, y, samples=sampled, vae=vae,
                    tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    g.add('SaveImage', label + ' · 개별 PNG 저장', 2240, y, images=decoded,
          filename_prefix=f'character-sheets/%date:yyyy-MM-dd%/{label}')
    return decoded


def graphs():
    anchor = Graph()
    resources = loaders(anchor)
    face = anchor.add('LoadImage', '01 얼굴 클로즈업 · 정체성만 사용', 0, 150, image='FACE_REFERENCE.png')
    outfit = anchor.add('LoadImage', '02 의상 참조 · 얼굴은 무시', 370, 150, image='OUTFIT_REFERENCE.png')
    generate(anchor, resources, [face, outfit], STUDIO + BODY +
             'Picture 1 is the sole facial identity reference: preserve facial proportions, eyes, nose, mouth, '
             'age appearance and skin tone. Picture 2 supplies clothing, footwear, accessories and hairstyle '
             'only when explicitly part of its headwear; ignore the identity of its wearer. Dress the person '
             'from Picture 1 in the complete outfit from Picture 2. Straight front view facing the camera. '
             'Keep garment colors, cut, fastenings and details. If footwear is unseen use simple matching shoes. '
             'If multiple people are in Picture 2 use the central person only. Preserve natural facial detail.',
             'front', 150, 512, 20260922)
    sheet = Graph()
    resources = loaders(sheet)
    front = sheet.add('LoadImage', '01 선택한 정면 PNG · 1단계 결과', 0, 150, image='APPROVED_FRONT.png')
    face = sheet.add('LoadImage', '02 같은 얼굴 원본', 0, 600, image='FACE_REFERENCE.png')
    outfit = sheet.add('LoadImage', '03 같은 의상 원본', 370, 600, image='OUTFIT_REFERENCE.png')
    lock = ('Picture 1 is the approved full-body character: preserve its identity, hairstyle, body proportions, '
            'complete clothing, colors, accessories and shoes exactly. Picture 2 provides fine facial identity '
            'only. Picture 3 provides garment detail only; ignore the face of its wearer. '
            'Do not redesign, add accessories, change age or change expression. ')
    side = generate(sheet, resources, [front, face, outfit], STUDIO + BODY + lock +
                    'Strict 90-degree left profile, nose pointing to the LEFT of the image, both shoulders '
                    'aligned in profile. No three-quarter view. Match the head-to-foot size of Picture 1.',
                    'side', 150, 512, 20260923)
    back = generate(sheet, resources, [front, face, outfit], STUDIO + BODY + lock +
                    'Strict 180-degree rear view, looking directly away, back of head visible, no face visible. '
                    'Infer unseen rear garment construction conservatively; add no new emblems or pockets. '
                    'Match the head-to-foot size of Picture 1.', 'back', 950, 512, 20260924)
    close = generate(sheet, resources, [front, face, outfit], STUDIO + lock +
                     'Front-facing head-and-shoulders close-up of the SAME character, whole head and hair or '
                     'headwear within frame. Match collar and hairstyle to Picture 1. Eyes visible, natural '
                     'neutral expression. No beautification, no face reshaping.', 'closeup', 1750, 768, 20260925)
    front_scaled = sheet.add('ImageScale', '정면 높이 정렬 · 비율 유지', 2240, -250,
                             image=front, upscale_method='lanczos', width=0, height=1152, crop='disabled')
    combined = front_scaled
    for index, part in enumerate((side, back, close)):
        combined = sheet.add('ImageStitch', '정면 → 측면 → 후면 → 얼굴', 2630 + index * 370, 400,
                             image1=combined, image2=part, direction='right', match_image_size=False,
                             spacing_width=0, spacing_color='white')
    sheet.add('SaveImage', '최종 턴어라운드 시트', 3740, 400, images=combined,
              filename_prefix='character-sheets/%date:yyyy-MM-dd%/turnaround')
    compose = Graph()
    combined = None
    for index, name in enumerate(('FRONT', 'SIDE', 'BACK', 'CLOSEUP')):
        part = compose.add('LoadImage', name + ' · 선택한 결과', index * 380, 0, image=name + '.png')
        part = compose.add('ImageScale', name + ' · 비율 유지', index * 380, 420,
                           image=part, upscale_method='lanczos', width=0, height=1152, crop='disabled')
        if combined is None:
            combined = part
        else:
            combined = compose.add('ImageStitch', '선택된 칸 연결', index * 380, 760,
                                    image1=combined, image2=part, direction='right', match_image_size=False,
                                    spacing_width=0, spacing_color='white')
    compose.add('SaveImage', '재생성 없이 최종 합성', 1600, 760, images=combined,
                 filename_prefix='character-sheets/%date:yyyy-MM-dd%/selected_turnaround')
    return {'01_Face_Outfit_Anchor': anchor, '02_Character_Turnaround': sheet,
            '03_Assemble_Selected_Views': compose}


def ui_workflow(g, info):
    nodes, by_id, links = [], {}, []
    for key, node in g.api.items():
        meta = info[node['class_type']]
        entry = {'id': int(key), 'type': node['class_type'], 'title': node['_meta']['title'],
                 'pos': g.layout[key], 'size': [345, 290], 'flags': {}, 'order': len(nodes), 'mode': 0,
                 'properties': {'Node name for S&R': node['class_type'], 'cnr_id': 'comfy-core'},
                 'inputs': [], 'outputs': [], 'widgets_values': []}
        for i, kind in enumerate(meta['output']):
            entry['outputs'].append({'name': meta.get('output_name', meta['output'])[i],
                                     'type': kind, 'links': [], 'slot_index': i})
        for section in ('required', 'optional'):
            for name, definition in meta['input'].get(section, {}).items():
                kind = definition[0]
                opts = definition[1] if len(definition) > 1 else {}
                value = node['inputs'].get(name)
                linked = isinstance(value, list) and len(value) == 2 and value[0] in g.api
                widget = isinstance(kind, list) or kind in ('STRING', 'INT', 'FLOAT', 'BOOLEAN', 'COMBO')
                if not widget or linked:
                    slot = {'name': name, 'type': 'COMBO' if isinstance(kind, list) else kind, 'link': None}
                    if widget:
                        slot['widget'] = {'name': name}
                    entry['inputs'].append(slot)
                if widget:
                    choices = kind if isinstance(kind, list) else opts.get('options', [])
                    default = opts.get('default', choices[0] if choices else 0)
                    entry['widgets_values'].append(default if linked or value is None else value)
                    if opts.get('control_after_generate'):
                        entry['widgets_values'].append('fixed')
        if node['class_type'] == 'LoadImage':
            entry['widgets_values'].append('image')
            entry['size'][1] = 380
        if node['class_type'] == 'KSampler':
            entry['size'][1] = 340
        nodes.append(entry)
        by_id[key] = entry
    for key, node in g.api.items():
        for slot, inp in enumerate(by_id[key]['inputs']):
            value = node['inputs'].get(inp['name'])
            if isinstance(value, list) and len(value) == 2 and value[0] in by_id:
                link = len(links) + 1
                inp['link'] = link
                by_id[value[0]]['outputs'][value[1]]['links'].append(link)
                links.append([link, int(value[0]), value[1], int(key), slot, inp['type']])
    return {'last_node_id': len(nodes), 'last_link_id': len(links), 'nodes': nodes,
            'links': links, 'groups': [], 'config': {}, 'extra': {'ds': {'scale': .55, 'offset': [70, 500]}}, 'version': .4}


def build():
    with urlopen('http://127.0.0.1:8188/object_info') as response:
        info = json.load(response)
    output = ROOT / 'workflows'
    output.mkdir(exist_ok=True)
    for name, graph in graphs().items():
        for suffix, value in (('.json', ui_workflow(graph, info)), ('.api.json', graph.api)):
            (output / (name + suffix)).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
        print(name, len(graph.api), 'nodes')


if __name__ == '__main__':
    build()
