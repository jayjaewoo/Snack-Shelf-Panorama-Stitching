# Snack Shelf Panorama Stitching

마트 과자 매대를 수평으로 이동하면서 촬영한 5장의 이미지를 자동으로 정합하여 하나의 파노라마 이미지로 합성하는 프로그램입니다.

OpenCV의 **feature matching + homography + perspective warping**을 직접 구현하여 image stitching을 수행했습니다.
(`cv.Stitcher` 사용하지 않음)

---

## Result

아래는 최종 stitching 결과입니다.

![Panorama Result](output/panorama.jpg)

---

## Input Images

파노라마 생성을 위해 직접 촬영한 입력 이미지 5장은 다음과 같습니다.

| 1.jpg             | 2.jpg             | 3.jpg             | 4.jpg             | 5.jpg             |
| ----------------- | ----------------- | ----------------- | ----------------- | ----------------- |
| ![](images/1.jpg) | ![](images/2.jpg) | ![](images/3.jpg) | ![](images/4.jpg) | ![](images/5.jpg) |

이미지는 왼쪽에서 오른쪽 방향으로 수평 이동하며 촬영되었습니다.

중앙 이미지 **3.jpg**를 기준으로 다음과 같이 정합됩니다.
```
1.jpg → 2.jpg → 3.jpg ← 4.jpg ← 5.jpg
```
즉,

* 2.jpg → 3.jpg 기준 변환
* 1.jpg → 2.jpg → 3.jpg 기준 변환
* 4.jpg → 3.jpg 기준 변환
* 5.jpg → 4.jpg → 3.jpg 기준 변환

의 순서로 정합됩니다.

---

## Method

다음 순서로 panorama 이미지를 생성합니다.

1. SIFT를 이용한 특징점 검출
2. BFMatcher + Ratio test로 특징점 매칭
3. RANSAC 기반 homography 계산
4. 모든 이미지를 3.jpg 기준 좌표계로 변환
5. warpPerspective로 panorama canvas 생성
6. Feather blending으로 경계 자연스럽게 합성
7. 검은 영역 자동 제거

---

## Additional Feature

**Feather blending**

이미지 경계에서 발생하는 seam을 줄이기 위해 distance transform 기반 blending을 적용했습니다.

또한 안정적인 feature matching을 위해 입력 이미지를 일정 크기로 resize 후 stitching을 수행했습니다.

---

## Feature Matching Statistics

각 이미지 쌍에 대해 RANSAC 기반 homography 계산 결과는 다음과 같습니다.

| Image Pair | Matches | Inliers |
|-----------|--------|--------|
| 2 → 3 | 167 | 18 |
| 1 → 2 | 111 | 20 |
| 4 → 3 | 216 | 25 |
| 5 → 4 | 308 | 67 |

모든 이미지 쌍에서 충분한 inlier가 확보되어 안정적인 panorama 생성이 가능합니다.

---

## How to Run

```
pip install -r requirements.txt
python main.py
```

결과 이미지:

```
output/panorama.jpg
```

---

## Project Structure

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
