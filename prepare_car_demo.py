# 선택한 자동차 탑승 이야기를 세 숏의 명세와 단순 프리비즈 입력으로 준비한다.
import copy
import pipeline as p
import project


def prepare():
    root = p.ROOT / 'projects' / 'car_entry'
    if (root / 'project.json').exists():
        raise FileExistsError('Demo already exists; preserve its revisions')
    p.save(root / 'project.json', {'id': 'car_entry', 'title': '자동차 탑승',
           'story': '여성이 주차된 자동차에 다가가 운전석 문을 열고 탑승한다.', 'shots': [], 'assets': {}})
    project.register(root / 'project.json', 'CHAR_001', 'character',
                     p.ROOT / 'projects/h3_baseline/assets/CHAR_001/v1/sheet.png', 'v1',
                     '제공된 여성. 검은 단발, 베이지 상의, 갈색 바지와 어두운 신발.')
    project.split_sheet(root / 'project.json', 'CHAR_001', 'v1', p.ROOT / 'character-sheet-boxes.json')
    positions = [([-3.5, -.6, 0], [-1.5, -.6, 0]),
                 ([-1.5, -.6, 0], [-1.5, -.6, 0]),
                 ([-1.5, -.6, 0], [-.45, -.3, -.45])]
    for index, (start, end) in enumerate(positions, 1):
        spec = {'id': f'car_entry_{index:02}', 'width': 864, 'height': 480, 'seconds': 5,
                'camera': {'location': [-7, -7, 4], 'target': [-.5, 0, .8], 'lens': 42},
                'objects': [
                    {'id': 'CHAR_001', 'kind': 'person', 'color': [.6, .52, .42],
                     'location': start, 'keyframes': [{'frame': 1, 'location': start}, {'frame': 120, 'location': end}]},
                    {'id': 'PROP_001', 'kind': 'car', 'color': [.08, .18, .3],
                     'location': [0, 0, 0], 'door_keys': [
                         {'frame': 1, 'angle': -1.1 if index == 3 else 0},
                         {'frame': 120, 'angle': -1.1 if index >= 2 else 0}]}]}
        p.save(root / f'shots/shot{index:02}/previz.json', spec)
    sheet_spec = copy.deepcopy(spec)
    sheet_spec['id'] = 'PROP_001_sheet'
    sheet_spec['objects'] = [sheet_spec['objects'][1]]
    sheet_spec['objects'][0]['door_keys'] = []
    sheet_spec['camera'] = {'location': [-6, -7, 3.5], 'target': [0, 0, .8], 'lens': 50}
    p.save(root / 'prop-sheet-spec.json', sheet_spec)
    return root


if __name__ == '__main__':
    print(prepare())
