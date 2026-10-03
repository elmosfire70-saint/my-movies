# 과거와 현재의 만남 영상 사용법

ComfyUI 워크플로 목록의 `Past_Present_Meeting` 폴더에서 `01_Past_Present_Still`을 먼저 실행한다. 입력 네 장은 이번 작업에서 사용한 성인 시트 한 장과 2005년 사진 세 장으로 설정돼 있다. 정지 장면을 확인한 다음 `02_Past_Present_Video`의 첫 이미지에 선택한 정지 장면 PNG를 넣고 실행한다.

첫 워크플로는 성인 시트의 첫 칸과 얼굴 확대 칸을 잘라 사용한다. 다른 레이아웃의 시트로 바꾸면 두 ImageCrop 좌표도 맞춰야 한다. 두 번째 워크플로는 시작 이미지를 첫 프레임으로 고정하고 MiniMax H3 Turbo 4단계로 약 5초 영상을 만든다. 배경은 2005년 사진과 맞춘 해변이며 조용한 바닷가 환경음만 지시했다.

첫 이미지 기본값은 이번 생성의 `past-present/meeting-still_00001_.png [output]`이다. 새 시작 장면을 생성했다면 두 번째 워크플로의 LoadImage도 새 결과로 변경한다. ComfyUI 기본 출력 폴더에서 `past-present/meeting-still_*.png`와 `past-present/meeting-video_*.mp4`를 찾을 수 있다. 선택된 최종 결과는 `E:\Codex\movies\output\past-present-20261003\v002\meeting-video.mp4`다. v001 영상은 카메라가 다가가며 아이가 잘린 비교용 결과로 보존했다.

실행 검사는 `python past-present-comfy/build_meeting_workflows.py`와 `python -m unittest discover -s past-present-comfy -p 'test_*.py' -v`다. 사진 속 아이와 생성 성인이 실제 동일인임을 검증하는 기능은 없다. 영상의 얼굴·손·의상 연속성을 육안으로 확인한다.
