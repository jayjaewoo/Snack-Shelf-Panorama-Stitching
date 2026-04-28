# Snack Shelf Panorama Stitching

마트 과자 매대를 수평으로 이동하면서 촬영한 5장의 이미지를 자동으로 정합하여 하나의 파노라마 이미지로 합성하는 프로그램입니다.

본 프로젝트는 OpenCV의 feature matching과 homography estimation을 직접 구현하여 image stitching을 수행합니다.

---

# Result

아래는 입력 이미지 5장을 이용해 생성한 최종 파노라마 결과입니다.

![Panorama Result](output/panorama.jpg)

---

# Input Images

입력 이미지는 `images` 폴더에 다음과 같이 저장합니다.

```
images/
├── 1.jpg
├── 2.jpg
├── 3.jpg
├── 4.jpg
└── 5.jpg
```

이미지는 아래 순서로 배치됩니다.

```
1.jpg - 2.jpg - 3.jpg - 4.jpg - 5.jpg
```

가운데 이미지인 `3.jpg`를 기준 좌표계로 사용하여 stitching을 수행합니다.

즉,

* 2.jpg → 3.jpg 기준 변환
* 1.jpg → 2.jpg → 3.jpg 기준 변환
* 4.jpg → 3.jpg 기준 변환
* 5.jpg → 4.jpg → 3.jpg 기준 변환

의 순서로 정합됩니다.

---

# Method

본 프로그램은 다음과 같은 단계로 panorama 이미지를 생성합니다.

### 1. Feature Detection

각 이미지에서 SIFT를 이용하여 특징점을 검출합니다.

```
SIFT (Scale-Invariant Feature Transform)
```

조명 변화에 강인한 특징점을 얻기 위해 histogram equalization을 함께 적용합니다.

---

### 2. Feature Matching

BFMatcher와 Lowe's ratio test를 이용하여 신뢰도가 높은 특징점만 선택합니다.

```
BFMatcher + Ratio Test
```

이를 통해 잘못된 매칭(outlier)을 줄입니다.

---

### 3. Homography Estimation

RANSAC 알고리즘을 사용하여 두 이미지 사이의 homography 행렬을 계산합니다.

```
cv.findHomography(..., RANSAC)
```

이 과정에서 잘못된 대응점은 자동으로 제거됩니다.

---

### 4. Coordinate Alignment

모든 이미지를 기준 이미지인 `3.jpg` 좌표계로 변환합니다.

```
1 → 2 → 3
2 → 3
4 → 3
5 → 4 → 3
```

---

### 5. Image Warping

각 이미지를 하나의 panorama canvas 위로 투영합니다.

```
cv.warpPerspective()
```

---

### 6. Feather Blending (Additional Feature)

이미지 경계에서 발생하는 부자연스러운 seam을 줄이기 위해 feather blending을 적용합니다.

distance transform을 이용하여 중심부에는 높은 가중치,
경계에는 낮은 가중치를 부여합니다.

이를 통해 겹치는 영역이 자연스럽게 연결됩니다.

---

### 7. Automatic Cropping

최종 panorama 주변의 검은 영역을 자동으로 제거합니다.

---

# Additional Features

기본 stitching 기능 외에 다음과 같은 기능을 추가 구현했습니다.

### Feather Blending

이미지 경계에서 발생하는 seam artifact를 줄이기 위해 distance transform 기반 blending을 적용했습니다.

### Image Resizing for Stability

특징점 매칭의 안정성과 계산 속도를 개선하기 위해 입력 이미지를 일정 크기로 조정한 뒤 stitching을 수행합니다.

---

# How to Run

다음 명령어로 실행할 수 있습니다.

```
pip install -r requirements.txt
python main.py
```

실행 후 결과 이미지는 다음 경로에 저장됩니다.

```
output/panorama.jpg
```

---

# Project Structure

프로젝트 폴더 구조는 다음과 같습니다.

```
project/
├── main.py
├── README.md
├── requirements.txt
├── images/
│   ├── 1.jpg
│   ├── 2.jpg
│   ├── 3.jpg
│   ├── 4.jpg
│   └── 5.jpg
└── output/
    └── panorama.jpg
```

---

# Requirements

다음 라이브러리가 필요합니다.

```
opencv-python
numpy
```

설치는 아래 명령어로 수행합니다.

```
pip install -r requirements.txt
```

---

# Implementation Summary

본 프로젝트는 다음과 같은 classical computer vision pipeline을 기반으로 구현되었습니다.

```
Feature Detection → Feature Matching → Homography Estimation
→ Perspective Warping → Feather Blending → Cropping
```

OpenCV의 high-level stitching API (`cv.Stitcher`)는 사용하지 않았습니다.
