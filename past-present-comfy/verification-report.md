# 실제 생성 검증

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
