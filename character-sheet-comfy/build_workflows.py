# 얼굴·의상 참조로 정면과 턴어라운드를 만드는 표준 ComfyUI 워크플로를 생성한다.
import json
import re
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

    def add(self, kind, title, pos_x, pos_y, **inputs):
        key = str(len(self.api) + 1)
        self.api[key] = {'class_type': kind, 'inputs': inputs, '_meta': {'title': title}}
        self.layout[key] = [pos_x, pos_y]
        return [key, 0]


def loaders(g):
    model = g.add('UNETLoader', 'Qwen Image 2.1 · INT8 ConvRot', 0, -450,
                  unet_name='qwen_image_2.1_int8_convrot.safetensors', weight_dtype='default')
    model = g.add('QwenImage21Cache', '2.1 참조 캐시 · 자동 메모리 배치', 370, -450,
                  model=model, device='auto', dtype='default')
    clip = g.add('CLIPLoader', 'Qwen vision-language encoder', 0, -200,
                 clip_name='qwen3vl_8b_int8_convrot.safetensors', type='qwen_image', device='default')
    vae = g.add('VAELoader', 'Qwen 2.1 RGBA VAE', 370, -200, vae_name='qwen_image_2.1_vae_bf16.safetensors')
    return model, clip, vae


def generate(g, resources, refs, prompt, label, y, width, seed):
    model, clip, vae = resources
    canvas = g.add('EmptyImage', label + ' · 출력 캔버스', 750, y + 400,
                   width=width, height=1152, batch_size=1, color=0xC0C0C0)
    images = {'images.image_1': canvas}
    for i, ref in enumerate(refs, 2):
        images[f'images.image_{i}'] = ref
    prompt = re.sub(r'Picture (\d+)', lambda m: f'<image{int(m[1])+1}>', prompt)
    prompt = ('Replace the blank gray canvas in <image1> with the following complete character image. '
              'Use the other images only as references, not as a collage. Render an opaque image. ' + prompt +
              ' Avoid: ' + NEGATIVE + '.')
    encoded = g.add('TextEncodeQwenImage21', label + ' · 2.1 지시문과 참조', 1130, y,
                    clip=clip, vae=vae, prompt=prompt, negative_prompt='', resolution=0, **images)
    sampled = g.add('KSampler', label + ' · 생성', 1500, y, model=model, positive=encoded,
                    negative=[encoded[0], 1], latent_image=[encoded[0], 2], seed=seed, steps=25, cfg=1.0,
                    sampler_name='euler', scheduler='simple', denoise=1.0)
    decoded = g.add('VAEDecodeTiled', label + ' · 타일 디코딩', 1870, y, samples=sampled, vae=vae,
                    tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    decoded = g.add('SplitImageWithAlpha', label + ' · 불투명 RGB 시트용', 1870, y + 330, image=decoded)
    g.add('SaveImage', label + ' · 개별 PNG 저장', 2240, y, images=decoded,
          filename_prefix=f'character-sheets/%date:yyyy-MM-dd%/{label}')
    return decoded


def reference(g, title, x, y, filename):
    image = g.add('LoadImage', title, x, y, image=filename)
    return g.add('ImageScaleToMaxDimension', title + ' · 참조 크기 제한', x, y + 410,
                 image=image, upscale_method='lanczos', largest_size=1024)


def turnaround_views(g, resources, front, face, outfit, y, crop_closeup=False):
    lock = ('Picture 1 is the approved full-body character: preserve its identity, hairstyle, body proportions, '
            'complete clothing, colors, accessories and shoes. Picture 2 provides fine facial identity only. '
            'Picture 3 provides garment detail only; ignore the face of its wearer. Keep every garment piece on '
            'the same part of the body and do not mirror or duplicate patches. If the approved character wears '
            'a beret, keep the same fitted size, crown shape, tilt, side drape and low band position while '
            'rotating the head; show the beret in TRUE PROFILE without exposing a front-facing face. Keep the '
            'front insignia on the front part of the beret. If it wears a structured cap or other non-beret hat, '
            'preserve its brim, crown and low fit. Keep the eyes clear in either case. '
            'Do not redesign, add accessories, change age or change expression. ')
    side = generate(g, resources, [front, face, outfit], STUDIO + BODY + lock +
                    'Strict 90-degree left profile, nose pointing to the LEFT of the image, both shoulders '
                    'aligned in profile. No three-quarter view. Match the head-to-foot size of Picture 1.',
                    'side', y, 512, 20260923)
    rear_lock = ('Picture 1 shows the approved character from the FRONT. Use it to match the same body proportions, '
                 'hair and headwear, garment type, fabric color, sleeve details and footwear. Rotate the character '
                 '180 degrees in three-dimensional space rather than copying the front garment surface onto the back. '
                 'If the character wears a beret, keep its crown size, soft fold and fitted band at the same '
                 'anatomical height as the approved front; from behind the band passes just above the ears and '
                 'the short hair remains visible below it. The insignia is on the hidden front of the beret, '
                 'not on its back. For any other hat, retain the approved crown and rear band height without '
                 'moving a front brim or emblem to the back. If the approved front has no hat, leave the head bare. '
                 'Front chest badges, front zipper and other front-only details remain on the hidden front. '
                 'If a scarf has a knot and long tails on the chest, those tails and any emblem remain on the hidden '
                 'front; from behind show only the scarf wrap at the back of the neck. The rear garment shows '
                 'continuous fabric and plausible rear seams. ')
    back = generate(g, resources, [front], STUDIO + BODY + rear_lock +
                    'Strict 180-degree rear view, looking directly away, back of head visible, no face visible. '
                    'Infer unseen rear garment construction conservatively; do not duplicate front decorations. '
                    'Match the head-to-foot size of Picture 1.', 'back', y + 800, 512, 20260924)
    if crop_closeup:
        cropped = g.add('ImageCrop', '얼굴 확대 · 생성 정면에서 자르기', 2240, y + 1600,
                        image=front, width=240, height=360, x=136, y=65)
        close = g.add('ImageScale', '얼굴 확대 · 비율 유지', 2620, y + 1600, image=cropped,
                      upscale_method='lanczos', width=0, height=1152, crop='disabled')
        g.add('SaveImage', 'closeup · 개별 PNG 저장', 2990, y + 1600, images=close,
              filename_prefix='character-sheets/%date:yyyy-MM-dd%/closeup')
    else:
        close = generate(g, resources, [front, face, outfit], STUDIO + lock +
                         'Front-facing head-and-shoulders close-up of the SAME character, whole head and hair or '
                         'headwear within frame. Match collar and hairstyle to Picture 1. Eyes visible, natural '
                         'neutral expression. No beautification, no face reshaping.',
                         'closeup', y + 1600, 768, 20260925)
    return side, back, close


def graphs():
    front_prompt = (STUDIO + BODY +
                    'Picture 1 is the only source for this person\'s facial identity. Preserve the head shape, '
                    'forehead, eyebrows, eye shape and spacing, nose, mouth, skin tone, apparent age and visible '
                    'hairline; ignore the clothing and background in Picture 1. Picture 2 is the clothing source. '
                    'If several people appear in Picture 2, use only the central wearer. Study the complete outfit '
                    'carefully: headwear, scarf and knot, collar, garment cut and fabric, fastenings, chest and sleeve '
                    'patch positions, pockets, trouser shape and footwear. Transfer each visible item to the same '
                    'anatomical location on the person from Picture 1, with realistic fabric fit and no mirrored '
                    'or duplicated badges. Ignore the outfit wearer\'s face, sunglasses, pose and background. '
                    'Identify the headwear type in Picture 2 before dressing the person. If it is a soft beret, '
                    'reproduce its color, crown, asymmetrical tilt, side drape, fitted band and front insignia. '
                    'Seat the beret visibly LOW on the head from Picture 1. On the lowered, draped side, the '
                    'band edge touches or slightly overlaps the OUTER TOP of ONE eyebrow; leave no exposed '
                    'forehead strip between that edge and those eyebrow hairs. Keep the rest of that eyebrow '
                    'visible. On the raised side leave a small natural gap above the other visible eyebrow. '
                    'Do not cover either eye or pull the whole beret evenly across both eyebrows. If Picture 2 '
                    'instead shows a structured cap or another non-beret hat, preserve '
                    'that hat type and brim shape; wear its brim close above BOTH eyebrows without touching or '
                    'hiding either eyebrow. If Picture 2 has no hat, do not add one. Arrange the original hair '
                    'naturally beneath the chosen headwear. Straight front view facing the camera. '
                    'The scarf knot and hanging tails stay on the chest, with front patches only on the front. '
                    'If footwear is unseen use simple matching shoes. Preserve natural facial detail.')
    anchor = Graph()
    resources = loaders(anchor)
    face = reference(anchor, '01 얼굴 클로즈업 · 정체성만 사용', 0, 150, 'FACE_REFERENCE.png')
    outfit = reference(anchor, '02 의상 참조 · 얼굴은 무시', 370, 150, 'OUTFIT_REFERENCE.png')
    generate(anchor, resources, [face, outfit], front_prompt, 'front', 150, 512, 20260922)
    sheet = Graph()
    resources = loaders(sheet)
    front = sheet.add('LoadImage', '01 선택한 정면 PNG · 1단계 결과', 0, 150, image='APPROVED_FRONT.png')
    face = reference(sheet, '02 같은 얼굴 원본', 0, 600, 'FACE_REFERENCE.png')
    outfit = reference(sheet, '03 같은 의상 원본', 370, 600, 'OUTFIT_REFERENCE.png')
    side, back, close = turnaround_views(sheet, resources, front, face, outfit, 150)
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
    one_click = Graph()
    resources = loaders(one_click)
    face = reference(one_click, '01 얼굴 원본 · 인물 특징', 0, 150, 'FACE_REFERENCE.png')
    outfit = reference(one_click, '02 의상 원본 · 복장 특징', 370, 150, 'OUTFIT_REFERENCE.png')
    front = generate(one_click, resources, [face, outfit], front_prompt, 'front', 150, 512, 20260922)
    side, back, close = turnaround_views(one_click, resources, front, face, outfit, 950, crop_closeup=True)
    combined = front
    for index, part in enumerate((side, back, close)):
        combined = one_click.add('ImageStitch', '정면 → 측면 → 후면 → 얼굴', 3000 + index * 370, 950,
                                 image1=combined, image2=part, direction='right', match_image_size=False,
                                 spacing_width=0, spacing_color='white')
    one_click.add('SaveImage', '완성된 캐릭터 시트', 4110, 950, images=combined,
                  filename_prefix='character-sheets/%date:yyyy-MM-dd%/character-sheet')
    return {'01_Face_Outfit_Anchor': anchor, '02_Character_Turnaround': sheet,
            '03_Assemble_Selected_Views': compose, '04_Character_Sheet_One_Click': one_click}


def expanded_inputs(meta, node):
    result = {}
    for section in ('required', 'optional'):
        fields = {}
        for name, definition in meta['input'].get(section, {}).items():
            if definition[0] == 'COMFY_AUTOGROW_V3':
                for field in node['inputs']:
                    if field.startswith(name + '.'):
                        fields[field] = ['IMAGE', {}]
            else:
                fields[name] = definition
        result[section] = fields
    return result


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
            for name, definition in expanded_inputs(meta, node).get(section, {}).items():
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
