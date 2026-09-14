# 자동차 시점 자료와 세 숏의 Blender 대표 프레임을 H3 입력으로 연결한다.
import pipeline as p
import project

root = p.ROOT / 'projects/car_entry'
prop_spec = p.read(root / 'prop-sheet-spec.json')
prop_spec['views'] = [
    {'name': 'front', 'location': [0, -8, 2]},
    {'name': 'side', 'location': [-8, 0, 2]},
    {'name': 'rear', 'location': [0, 8, 2]},
    {'name': 'threequarter', 'location': [-6, -7, 3.5]}]
p.save(root / 'prop-sheet-views.json', prop_spec)
project.previz(root / 'prop-sheet-views.json', root / 'renders/prop-views')
project.register(root / 'project.json', 'PROP_001', 'prop', root / 'renders/prop-views/view_threequarter.png',
                 'v1', '짙은 파란색 세단 프리비즈. 최종 외형 확정 전 구조 참조용.')
for name in ('front', 'side', 'rear', 'threequarter'):
    project.register_view(root / 'project.json', 'PROP_001', 'v1', name, root / f'renders/prop-views/view_{name}.png')
actions = [
    'The woman walks slowly toward the driver side of the parked car and stops beside the closed door.',
    'The woman stands by the driver door, reaches for the handle and slowly opens the door outward.',
    'The driver door is already open. The woman bends naturally and slowly sits in the driver seat. The door stays open.']
for index, action in enumerate(actions, 1):
    directory = root / f'shots/shot{index:02}'
    project.previz(directory / 'previz.json', directory / 'previz')
    prompt = ('Photorealistic continuous shot. <Picture 1> shows the single adult woman; '
              'preserve her black bob, beige sweater, brown trousers and dark shoes. Show exactly one woman. '
              '<Picture 2> defines the proportions and dark blue color of one sedan, rendered as a realistic finished car. '
              '<Picture 3> is a rough blocking reference for camera and object placement ONLY; replace its block person and primitive surfaces with realistic appearance. '
              'A quiet parking area, soft daylight, locked camera, no text, no speech, natural ambient sound. ' + action)
    project.bind(root / 'project.json', ['CHAR_001@v1', 'PROP_001@v1'], directory / 'previz',
                 f'car_entry_{index:02}', prompt, directory / 'shot.json')
print(project.validate_project(root / 'project.json'))
