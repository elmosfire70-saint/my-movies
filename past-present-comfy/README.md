# 과거와 현재의 만남 영상 사용법

ComfyUI 워크플로 목록의 `Past_Present_Meeting` 폴더에서 `01_Past_Present_Still`을 먼저 실행한다. 입력은 성인 군복 시트, 새 성인 얼굴 사진, 2005년 아이 사진 세 장으로 설정돼 있다. 정지 장면을 확인한 다음 `02_Past_Present_Video`의 첫 이미지에 선택한 정지 장면 PNG를 넣고 실행한다.

첫 워크플로는 성인 시트의 첫 칸에서 전신 군복을 잘라 사용하고, 별도의 성인 얼굴 사진을 얼굴 기준으로 사용한다. 다른 레이아웃의 시트로 바꾸면 전신 ImageCrop 좌표를 맞춰야 한다. 두 번째 워크플로는 시작 이미지를 첫 프레임으로 고정하고 MiniMax H3 Turbo 4단계로 약 5초 영상을 만든다. 영상 출력의 오디오 입력을 비워 대사가 없는 무음 MP4로 저장한다.

두 번째 워크플로의 첫 이미지 기본값은 이번에 생성한 `past-present/meeting-still_00002_.png [output]`이다. 새 시작 장면을 생성했다면 LoadImage를 그 결과로 변경한다. ComfyUI 기본 출력 폴더에서 `past-present/meeting-still_*.png`와 `past-present/meeting-video-silent_*.mp4`를 찾을 수 있다. 선택된 결과는 `E:\Codex\movies\output\past-present-20261003\v003\meeting-video.mp4`다. 이전 버전은 비교용으로 보존했다.

실행 검사는 `python past-present-comfy/build_meeting_workflows.py`와 `python -m unittest discover -s past-present-comfy -p 'test_*.py' -v`다. 사진 속 아이와 생성 성인이 실제 동일인임을 검증하는 기능은 없다. 영상의 얼굴·손·의상 연속성을 육안으로 확인한다.
