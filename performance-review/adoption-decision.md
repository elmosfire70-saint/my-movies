# 공개 비교 자료에 따른 모델 적용 판단

2026-10-29 확인. 결론은 **Qwen Turbo는 초안용 선택 모드의 시험 적용을 권장하되 기본 모델 교체는 보류하고, H3 경량판·새 Turbo·Wan으로 운영 모델을 교체하는 것은 보류**한다. 이번 요청은 판단이므로 설치·워크플로 변경은 수행하지 않았다.

## 근거를 평가한 기준

설치 가능성, 파일 크기, 제작자 예시, 같은 입력의 속도 측정, 반복 품질 평가는 서로 다른 증거다. RTX 3060이라는 이름이 같아도 RAM·해상도·프레임·스텝·샘플러·attention·캐시가 다르면 속도 배율을 이전할 수 없다. 한 제작자의 소수 사례를 독립적인 대규모 품질 벤치마크로 부르지 않는다.

## Qwen 2.1 Turbo

[Loop Forge의 직접 실행 기록](https://loopforge.cc/projects/qwen-image-2-1-turbo/)은 RTX 3060 12GB, INT8 ConvRot, ComfyUI 0.37.0, PyTorch 2.11+cu130, SageAttention 조건을 공개한다. 1024² 텍스트 생성 한 번은 기본 25단계 34.9초, Turbo 8단계 15.0초였다. 이는 단일 사례이며 평균·분산이 아니다.

이 프로젝트에 더 가까운 [인물 참조 한 장으로 6개 장면 편집](https://loopforge.cc/projects/qwen-image-2-1-turbo/same-face-six-scenes/)은 832×1216, seed 21에서 기본 **40단계** 약 63.2초, Turbo 8단계 약 23.5초였다. 약 2.69배 속도 차이이나 현재 **25단계**와 비교한 결과가 아니다. 저자는 여섯 장면에서 두 모델 모두 동일 인물을 유지했다고 평가한다. 블라인드 평가·얼굴 임베딩 점수·독립 평가자 수·통계 신뢰구간은 제공하지 않아 얼굴 품질 동등성의 증거는 약하다.

공개된 [기본 API JSON](https://loopforge.cc/assets/workflows/qwen-image-2-1-turbo/same-face-six-scenes-base-1.json)과 [Turbo API JSON](https://loopforge.cc/assets/workflows/qwen-image-2-1-turbo/same-face-six-scenes-turbo-1.json)을 열어 같은 참조 파일, 프롬프트, seed, 인코더·VAE, CFG 1, 캐시 설정 및 40단계/고정 8단계 차이를 대조했다. 실행 원본 로그를 독립 재현한 것은 아니다. 현재 프로젝트는 두 사람과 배경을 합성하고, 다른 PyTorch·attention·출력 크기를 사용한다.

[Qwen 공식 모델 카드](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo)는 8단계·동일 7B 구조와 사례를 제공하지만 현재 기본형 대비 얼굴 보존의 정량 동등성 표는 확인하지 못했다. [Comfy 공식 문서](https://github.com/Comfy-Org/docs/blob/main/tutorials/image/qwen/qwen-image-2-1.mdx)는 독립 Turbo 체크포인트와 베이스용 LoRA 경로를 구분한다. 위 개인 실측은 독립 Turbo 체크포인트 기준이므로 LoRA에도 같은 속도·품질 수치를 적용하지 않는다.

**판단.** 속도 개선 가능성에는 실증 근거가 있어 초안용 별도 모드의 로컬 시험을 권장한다. 최종 얼굴 합성 기본값을 즉시 교체할 근거는 부족하다. 이전 답변의 LoRA 추천은 다운로드·변경 부담 기준이었고, 이번 속도 비교 자료가 직접 지지하는 대상은 독립 Turbo 체크포인트다.

## H3 경량판과 새 Turbo

[Comfy 배포 목록](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/diffusion_models)에서 Ref2VA pruned INT8 약 21GB, W6A8 약 16GB는 확인했다. 약 24% 파일 감소를 24% 속도 증가 또는 VRAM 감소로 해석하지 않는다.

[WAS Singularity v2 양자화 비교](https://huggingface.co/WAS/Minimax-h3_Singularity_v2_pruned)는 같은 4개 seed에서 BF16 기준 평균 PSNR을 INT8 r2 26.1dB, W6A8 r2 24.4dB로 공개한다. 조건은 1344×768·124프레임·6단계·DMAD LoRA 0.7이다. 이는 **다른 파생 모델**의 픽셀 근접도이며 얼굴 보존 점수도, 현재 Comfy 원본의 성능 비교도 아니다. 다만 비트를 낮춰도 결과가 완전히 같다는 가정은 뒷받침하지 않는다.

[LightX2V 새 Ref2V 4-step v1.0 파일](https://huggingface.co/lightx2v/Minimax-h3-Turbo/tree/main)은 존재한다. 확인한 자료에서는 현재 v0.1과 같은 조건의 3060 속도·얼굴 품질 비교를 찾지 못했다. 최신 버전이라는 이유만으로 교체하지 않는다. FL2V와 Ref2V LoRA도 서로 대체하지 않는다.

**판단.** 현재 작업은 OOM 없이 성공했다. W6A8는 메모리 부족이 실제 실패로 이어지거나 동일 입력 로컬 비교에서 이득을 확인할 때 채택한다. 새 Ref2V Turbo는 품질 비교 후 채택한다. 현재 운영 기본값은 유지한다.

## Wan2.2 5B

[Comfy 공식 안내](https://docs.comfy.org/tutorials/video/wan/wan2_2)의 8GB 오프로딩 실행 조건은 설치 가능성 근거다. H3 Turbo4보다 빠르거나 두 사람의 얼굴을 더 잘 유지한다는 직접 비교는 확인하지 못했다. 따라서 현재 프로젝트의 교체 근거로는 부족하다. 더 상세한 영상 자료 비교는 [영상 비교 근거](video-comparison-evidence.md)에 기록했다.

## 현재 실측에 연결한 효과 판단

이 PC의 전체 437.511초 중 Qwen 샘플링 노드는 45.241초, 약 10.3%였다. 그 구간 전체가 8/25로 줄고 다른 시간이 동일하다는 **단순 가정**이면 절감은 약 30.8초, 전체 약 7%다. 노드 시간에는 모델 전송 등 고정 비용이 있어 이 계산은 실측 예측치가 아니다. 이미지 Turbo만으로 전체 영상 제작이 2~3배 빨라진다고 약속할 수 없다.

반면 합성 사진을 확정하고 영상 워크플로만 재실행하면 합성을 다시 계산하는 경우 약 94초 구간을 건너뛴다. 캐시가 이미 유지되는 경우 이 이득은 작아진다. 현재로서는 이 방법과 Turbo 스위치 연결 보강이 모델 전면 교체보다 근거가 명확하다.

최종 권고는 **기본 Qwen+H3 유지, Qwen Turbo 초안 모드만 시험 도입 후보, H3/Wan 교체 보류**다. 실제 채택 시에는 사용자 사진 3쌍 이상·각 3개 seed, 배경 OFF/ON을 같은 조건으로 비교하고, 얼굴·나이 구분·의상 실패율과 반복 생성까지 포함한 총 시간을 기록하는 기준을 제안한다. 이 비교는 아직 수행하지 않았다.

## 이번에 확인한 것

공개 모델 카드·제작자 실험·API 워크플로를 열어 버전, 스텝, 입력, seed, 하드웨어, 평가 척도를 대조했다. 기존 로컬 metrics/events JSON을 다시 읽었다. 이번에는 코드 수정·모델 생성·새 벤치마크를 실행하지 않았다. 링크와 근거를 정리하고 `git diff --check`로 문서 변경을 확인한다.
