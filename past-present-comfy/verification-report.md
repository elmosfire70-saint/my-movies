# 실제 생성 검증

## 2026-10-04 두 사진 통합 워크플로

- `python past-present-comfy/build_meeting_workflows.py` 성공. 통합 30노드, 합성 14노드, 영상 17노드 워크플로 생성.
- `python -m unittest discover -s past-present-comfy -p 'test_*.py' -v` 2개 통과. 통합 LoadImage 두 개, 과거·현재 참조 순서, 합성 PNG와 H3 첫 프레임의 동일 연결, 오디오 디코드 및 최종 오디오 입력 부재를 확인.
- ComfyUI `Past_Present_Meeting/00_Past_Present_Two_Photos`, `01_Past_Present_Still`, `02_Past_Present_Video` 저장 후 GET 바이트 일치 확인. 기존 두 워크플로는 출력 버전 폴더에 백업.
- 통합 작업 `a19d4551-f9bc-4e31-b80c-228a41357002` 성공. 두 사진으로 Qwen 합성과 H3 생성이 자동 연결되어 PNG와 MP4를 저장.
- ComfyUI 가상환경 Python으로 `output/past-present-20261004/v004/verify_video.py` 실행. PyAV 전체 디코드 576×1024·24fps·124프레임·오디오 스트림 0개 검사 통과.
- 합성 PNG와 영상 첫·중간·끝 프레임 육안 검토. 두 얼굴과 배경이 유지되고 시선 교환 후 미소 짓는 구도를 확인. 입력에 없는 옷 부분은 추정되며 영상에서 표정과 얼굴 세부는 조금 변한다. 무음은 확인했지만 입의 움직임 자체가 완전히 멈추지는 않는다.

- `python past-present-comfy/build_meeting_workflows.py` 성공. 16노드 정지 장면과 18노드 영상 워크플로 생성.
- `python -m unittest discover -s past-present-comfy -p 'test_*.py' -v` 1개 통과. 설치된 노드 스키마, 참조 연결, 첫 프레임 입력과 저장 노드를 검사.
- ComfyUI 사용자 워크플로 `Past_Present_Meeting/01_Past_Present_Still` 및 `02_Past_Present_Video` 저장 후 GET 바이트 일치 확인.
- Qwen 정지 장면 작업 `d501c012-3a11-4b26-9422-d44d94cba3a5` 성공. 576×1024 PNG 육안 검토에서 두 사람, 해변, 손의 접촉, 복장을 확인.
- H3 첫 영상 작업 `4efede3a-77cd-4acf-9719-23c90a760634` 성공. PyAV로 576×1024·24fps·124프레임·5.167초 전체 디코드. 첫·중간·끝 프레임 육안 검토에서 끝부분 아이가 화면 밖으로 밀려나 선택하지 않음.
- 카메라 이동을 제거한 H3 수정 작업 `96627a77-6ed9-4dfc-b3f9-24947e6fa5b4` 성공. v002 MP4 576×1024·24fps·124프레임·5.167초, 오디오 32kHz 스테레오 165888 샘플을 전부 디코드. 첫·중간·마지막 프레임 육안 검토에서 두 인물이 계속 화면 안에 있고 시선·손 접촉이 자연스러워 선택.
- v002에 참조 4장, 정지 장면, 영상, 실행 요청·이력, 크기·SHA256 기록을 보존. 성인 시트는 생성 이미지여서 얼굴·군복 문양의 완전 일치는 보장하지 않는다.

## v003 성인 얼굴 교체·대사 제거

- `python past-present-comfy/build_meeting_workflows.py` 성공. 16노드 정지 장면과 17노드 무음 영상 워크플로 생성.
- `python -m unittest discover -s past-present-comfy -p 'test_*.py' -v` 1개 통과. 새 얼굴 입력 및 `CreateVideo` 오디오 미연결을 검사.
- ComfyUI 사용자 워크플로 두 개를 갱신한 뒤 GET 바이트 일치 확인.
- Qwen 정지 장면 작업 `66d8d833-c026-4bbe-b07a-52a23756de69` 성공. 새 성인 얼굴·베레모, 아이, 해변, 의상과 손 접촉을 PNG에서 육안 확인.
- H3 영상 작업 `7b4c412a-cbdd-49e7-9ecf-53b95fb9eb03` 성공. PyAV로 576×1024·24fps·124프레임 전체 디코드. 오디오 스트림 0개를 확인했고, 첫·중간·끝 프레임에서 두 사람이 모두 화면 안에 있음을 육안 확인.
- 생성형 영상의 신원·군복 문양·표정은 프레임마다 조금 달라질 수 있다. 무음 파일이므로 대사와 환경음도 없다.
