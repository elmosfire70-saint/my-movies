# 범용 사용자 노드와 표준 H3 노드를 연결한 UI 및 API 워크플로를 생성한다.
import json
from pathlib import Path
import pipeline as p
from custom_nodes.codex_video_tools import NODE_CLASS_MAPPINGS


def build():
    g = p.graph({'id': 'generic', 'turbo': True, 'seed': 42, 'seconds': 5,
                 'prompt': 'Describe your scene.', 'width': 864, 'height': 480}, [])
    for key in ('115', '131', '132', '136', '138'):
        g.pop(key)
    g['1'] = {'class_type': 'CodexShotSettings', 'inputs': {'prompt': 'A single continuous shot. Describe the action, setting, camera and sound.',
        'width': 864, 'height': 480, 'seconds': 5.0, 'turbo': True, 'project': 'my_video', 'shot': 'shot01'}}
    g['2'] = {'class_type': 'LoadImage', 'inputs': {'image': ''}}
    g['3'] = {'class_type': 'CodexReferences', 'inputs': {'roles': 'Subject identity and appearance.\nObject appearance.\nComposition only; replace primitive surfaces.', 'image_1': ['2', 0]}}
    g['4'] = {'class_type': 'CodexLastFrame', 'inputs': {'enabled': False, 'video_path': ''}}
    g['6'] = {'class_type': 'CodexPrevizVideo', 'inputs': {'enabled': False, 'video_path': '',
        'role': 'Use camera movement, timing and blocking only. Replace primitive surfaces with realistic appearance.',
        'max_frames': ['1', 3], 'max_edge': 864}}
    g['5'] = {'class_type': 'CodexH3Inputs', 'inputs': {'clip': ['128', 0], 'vae': ['119', 0], 'audio_vae': ['120', 0],
        'references': ['3', 0], 'prompt': ['1', 0], 'width': ['1', 1], 'height': ['1', 2], 'frames': ['1', 3], 'first_frame': ['4', 0], 'video_reference': ['6', 0]}}
    g['126']['inputs']['conditioning'] = ['5', 0]
    g['125']['inputs']['latent_image'] = ['5', 1]
    g['124']['inputs'].update(steps=['1', 4], model=['145', 0])
    g['145']['inputs']['strength_model'] = ['1', 6]
    g['92']['inputs']['filename_prefix'] = ['1', 5]
    g['92']['inputs'].pop('format.codec', None)
    info = p.api('/object_info')
    for name, cls in NODE_CLASS_MAPPINGS.items():
        info[name] = {'input': cls.INPUT_TYPES(), 'output': cls.RETURN_TYPES,
                      'output_name': cls.RETURN_NAMES}
    positions = {'1': [0, 0], '2': [0, 460], '3': [400, 450], '4': [400, 800], '5': [850, 350], '6': [850, 800],
        '127': [0, -600], '128': [400, -600], '119': [800, -600], '120': [1200, -600],
        '145': [400, -300], '129': [850, 0], '123': [850, 150], '124': [1250, 0],
        '126': [1250, 350], '125': [1650, 250], '121': [2050, 450], '122': [2050, 200],
        '130': [2450, 250], '92': [2850, 250]}
    ui_nodes, by_id, links = [], {}, []
    for order, (key, node) in enumerate(g.items()):
        meta = info[node['class_type']]
        height = {'1': 410, '2': 300, '3': 320, '4': 160, '5': 280, '6': 300, '129': 100, '123': 100, '92': 330}.get(key, 180)
        entry = {'id': int(key), 'type': node['class_type'], 'pos': positions[key], 'size': [350, height],
                 'flags': {}, 'order': order, 'mode': 0, 'properties': {'Node name for S&R': node['class_type']},
                 'inputs': [], 'outputs': [], 'widgets_values': []}
        for i, kind in enumerate(meta['output']):
            entry['outputs'].append({'name': meta.get('output_name', meta['output'])[i], 'type': kind, 'links': [], 'slot_index': i})
        for section in ('required', 'optional'):
            for name, definition in meta['input'].get(section, {}).items():
                kind = definition[0]
                opts = definition[1] if len(definition) > 1 else {}
                value = node['inputs'].get(name)
                linked = isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in g
                widget = isinstance(kind, list) or kind in ('STRING', 'INT', 'FLOAT', 'BOOLEAN', 'COMBO')
                if linked or not widget or opts.get('forceInput'):
                    inp = {'name': name, 'type': 'COMBO' if isinstance(kind, list) else kind, 'link': None}
                    if widget and not opts.get('forceInput'):
                        inp['widget'] = {'name': name}
                    entry['inputs'].append(inp)
                if widget and not opts.get('forceInput'):
                    default = opts.get('default', kind[0] if isinstance(kind, list) and kind else 0)
                    entry['widgets_values'].append(default if linked or value is None else value)
                    if opts.get('control_after_generate'):
                        entry['widgets_values'].append('fixed')
        ui_nodes.append(entry)
        by_id[key] = entry
    for key, node in g.items():
        for slot, inp in enumerate(by_id[key]['inputs']):
            value = node['inputs'].get(inp['name'])
            if isinstance(value, list) and len(value) == 2 and str(value[0]) in by_id:
                link_id = len(links) + 1
                inp['link'] = link_id
                by_id[value[0]]['outputs'][value[1]]['links'].append(link_id)
                links.append([link_id, int(value[0]), value[1], int(key), slot, inp['type']])
    workflow = {'last_node_id': max(map(int, g)), 'last_link_id': len(links), 'nodes': ui_nodes,
                'links': links, 'groups': [], 'config': {}, 'extra': {'ds': {'scale': .3, 'offset': [120, 650]}}, 'version': .4}
    output = Path('workflows')
    output.mkdir(exist_ok=True)
    p.save(output / 'Codex_Generic_H3.json', workflow)
    p.save(output / 'Codex_Generic_H3.api.json', g)
    return len(ui_nodes), len(links)


if __name__ == '__main__':
    print(build())
