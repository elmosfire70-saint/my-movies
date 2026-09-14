# 작업 맥락

2026-09-14 추가 검증. 로컬 Git 저장소를 초기화하고 실행기를 0cc1896으로 커밋했다. 기존 LTX 설치 스크립트·보고서는 별도 미추적 상태로 보존했다. 인물 단일 정면의 기본 20-step은 611.257초, Turbo는 229.088초였다. 이미지·프롬프트·seed·해상도·길이는 같고 ID와 Turbo 설정만 다름을 확인했다. 각 1회 캐시 포함 측정이며 comparison.json에 저장했다.

자동차 이야기의 세 R2V Turbo 숏과 15.5초 검증용 편집본을 생성했다. 접근 243.533초, 문 열기 335.213초, 탑승 244.889초였다. 차량 지붕 구조 오류가 있고, 두 번째 숏은 운전석 지시 대신 뒷문을 열었다. 사용자 원래 요청은 좌석을 지정하지 않아 세 번째는 뒷좌석으로 연결했지만 시작 시 닫힌 문으로 되돌아가는 오류가 있었다. 결과를 최종 승인하지 않고 preview로 편집했다. 설치된 MiniMaxH3AddGuide의 frame_idx=0을 이용해 anchor_first 옵션을 구현하고 세 번째 숏만 별도 shot03_anchor에서 재실행 중이다. 라이브 브리지는 재확인 시에도 미연결이다.

2026-09-14 구현 진행. pipeline.py는 실제 성공 API 그래프에서 H3 실행 그래프를 만들고 /prompt 제출, WebSocket 진행 수신, history 회수와 PyAV 전체 디코드를 처리한다. 참조 입력 키는 ref_images.ref_image_0 형태다. 첫 변환 시 남은 139 링크로 HTTP 400을 받아 수정했으며 원래 거부된 제출 기록은 rejected-initial-job.json으로 보관했다.

project.py는 자산 등록·해시·시점 분리, 숏 검증, Blender 대표 프레임 결합, 순차 실행, 검수 기록, 영상·오디오 이어 붙이기를 제공한다. Blender 5.2.1은 E:\Blender Foundation\Blender 5.2\blender.exe를 사용한다. 별도 프로세스 렌더가 성공했으며 사용자 확장 환경과 분리하기 위해 BLENDER_USER_RESOURCES를 작업 폴더로 지정했다. 사용자 썸네일 캐시 쓰기 경고가 있으나 blend와 PNG 저장은 성공했다. Higgsfield get_host_status는 Blender 미연결을 반환했다.

사용자가 첫 이야기를 '여성이 자동차에 다가가 탑승하는 장면'으로 선택했다. projects/car_entry에 접근·문 열기·탑승 3개 숏과 인물·자동차 자산을 준비했다. 자동차 시트는 저분할 Blender 구조 자료이며 최종 사실적 자동차 외형 시트는 아니다. 인물 시트는 제공된 800×533 이미지에서 확인한 좌표를 이용해 얼굴·정면·측면·후면으로 분리했다.

인물 기준 기본 20-step 실행 9465b21b-e116-4333-84ff-773b68c1f930은 659.930초에 성공했으나 합성 시트의 두 인물이 영상에 남아 시각 검증에서 거부했다. 정면 한 사람만 사용하는 Turbo 실행 8c1f68fd-5b34-46c8-93b9-4a1db9d498ba는 229.088초에 성공했다. 실제 출력은 864×480, 24fps, 124프레임, 5.167초, 오디오 1개이며 시작·중간·끝 프레임에서 인물 중복이 사라졌다. 두 실행은 입력이 달라 동일 조건 속도 비교로 보고하지 않는다. 음향 청취와 사용자 예술적 승인은 미완료다.

2026-09-14. 사용자가 LTX-2.5에서 H3로 변경한 전체 제작 계획 재작성을 요청했다. 기존 plan.md는 LTX 설치만 다루어 Codex 중심 제작 계획으로 확장했다. 기존 설치 기록은 아래에 유지한다. 현재 폴더는 Git 저장소가 아니므로 문서 변경을 커밋하지 않았다.

현재 ComfyUI history에서 fd139f53-0542-44be-a3bd-1ff50b983e7f의 success와 completed=true를 재확인했다. 실행 시간은 764.766초이며 일부 노드 캐시가 있었다. 실제 프롬프트에는 소년·괴수 예제와 미연결 Audio 1 지시가 남아 있어 인물 재현 품질의 증거로 사용하지 않는다. 다음 구현은 기준 숏 입력 정리와 결과 메타데이터·품질 검증부터 시작한다.

J:\LTX2.5 경로 존재와 추가 모델 경로 설정은 재확인했다. 이번 문서 개정에서 전체 LTX 파일 무결성·E 원본 제거 여부는 재검증하지 않았다. Blender의 RGB 참조를 H3에 전달하는 최소 경로부터 구현하며, 정확한 동작 제어가 필요할 때만 별도 H3 제어 모델을 검증한다. 시트 신규 생성은 독립 정지 이미지 경로가 필요하고 초기에는 제공 이미지 등록을 우선한다.

2026-09-13. 설치만 요청됨. Blender 장면과 ComfyUI 소스는 변경하지 않음.

공식 저장소 Lightricks/LTX-2.5 revision 5e6e71018ee1756ed329b697a7b4aedc934dfce9. 로컬 huggingface_hub get_token() 결과 False. 외부 네트워크 권한으로 재시도했으나 모델 HEAD 요청이 GatedRepoError / 401 Unauthorized. 약관 및 연락처 공유 동의를 대신 제출하지 않음. 사용자 인증 필요.

설치 대상 E:\Comfy-Desktop\ComfyUI-Shared\models. 실행 로그에서 diffusion_models, text_encoders, vae, latent_upscale_models 공유 경로를 확인한 후 설치할 것.

선택 파일과 바이트 용량.
- diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors 21504034224
- text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors 15372969374
- vae/ltx-2.5-video-vae-conv-bf16.safetensors 1452269922
- vae/ltx-2.5-audio-vae-bf16.safetensors 364866540
- latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors 995778752

Conv VAE는 공식 카드에서 더 가볍고 빠른 대안으로 설명됨. 기본 템플릿의 영상 VAE 선택을 해당 Conv 파일로 바꿔야 함. NVFP4보다 현재 공식 Comfy 템플릿의 INT8 경로를 우선함.

2026-09-14. 사용자가 Hugging Face 로그인을 완료함. 선택한 5개 파일 다운로드 완료. install_ltx25.py가 저장소 revision 메타데이터의 LFS SHA256과 실제 파일 SHA256을 대조했고 모두 통과하여 ltx25-install-report.json을 생성함. ComfyUI folder_paths를 통해 diffusion model, text encoder, 두 VAE, latent spatial upscaler가 각각 검색되는 것을 확인함. 다운로드 중 생성된 parts.json 및 중복 incomplete/lock 파일은 검증 후 정리함. ComfyUI 서버는 검증 시 실행 중이 아니어서 실제 영상 생성은 수행하지 않음.

2026-09-14. 첫 프레임 고정 탑승 재생성 성공(256.590초). 0·60·123프레임에서 열린 문 상태로 시작해 뒷좌석으로 들어가는 흐름 확인. 차량 지붕과 문 왜곡은 남아 있어 승인하지 않았다. 기존 결과를 보존하고 project-anchored.json의 세 번째 숏만 교체했다. car_entry_preview_v2.mp4는 전체 372프레임·15.5초·864×480·24fps 및 스테레오 48kHz 디코드 통과.
