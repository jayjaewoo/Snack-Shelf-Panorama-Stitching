from pathlib import Path

import cv2 as cv
import numpy as np


IMAGE_ORDER = [1, 2, 3, 4, 5]
CENTER_ID = 3
MAX_WIDTH = 1600
PREVIEW_MAX_WIDTH = 1400
PREVIEW_MAX_HEIGHT = 800


def load_images(image_dir="images"):
    """Load 1.jpg ~ 5.jpg from the image folder."""
    images = {}

    for idx in IMAGE_ORDER:
        path = Path(image_dir) / f"{idx}.jpg"
        img = cv.imread(str(path), cv.IMREAD_COLOR)

        if img is None:
            raise FileNotFoundError(f"Cannot load image: {path}")

        images[idx] = img

    return images


def resize_images(images, max_width=MAX_WIDTH):
    """
    Resize large images while keeping the original aspect ratio.
    This makes feature matching faster and more stable.
    """
    resized = {}

    for idx, img in images.items():
        h, w = img.shape[:2]

        if w > max_width:
            scale = max_width / w
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized[idx] = cv.resize(img, (new_w, new_h), interpolation=cv.INTER_AREA)
        else:
            resized[idx] = img.copy()

    return resized


def detect_features(img):
    """Detect SIFT keypoints and descriptors."""
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    gray = cv.equalizeHist(gray)

    sift = cv.SIFT_create(nfeatures=8000)
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 8:
        raise RuntimeError("Not enough feature points were found.")

    return keypoints, descriptors


def match_features(desc_src, desc_dst):
    """Match feature descriptors using BFMatcher and Lowe's ratio test."""
    matcher = cv.BFMatcher(cv.NORM_L2, crossCheck=False)
    knn_matches = matcher.knnMatch(desc_src, desc_dst, k=2)

    good_matches = []

    for pair in knn_matches:
        if len(pair) < 2:
            continue

        m, n = pair

        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    return good_matches


def estimate_homography(src_img, dst_img, pair_name):
    """
    Estimate a homography that maps src_img to the coordinate system of dst_img.
    """
    kp_src, desc_src = detect_features(src_img)
    kp_dst, desc_dst = detect_features(dst_img)

    matches = match_features(desc_src, desc_dst)

    if len(matches) < 8:
        raise RuntimeError(f"{pair_name}: not enough matches.")

    src_pts = np.float32(
        [kp_src[m.queryIdx].pt for m in matches]
    ).reshape(-1, 1, 2)

    dst_pts = np.float32(
        [kp_dst[m.trainIdx].pt for m in matches]
    ).reshape(-1, 1, 2)

    H, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 4.0)

    if H is None:
        raise RuntimeError(f"{pair_name}: homography estimation failed.")

    inliers = int(mask.sum())
    print(f"{pair_name}: matches={len(matches)}, inliers={inliers}")

    return H


def compute_homographies_to_center(images):
    """
    Compute homographies using 3.jpg as the reference image.

    Image layout:
        1.jpg - 2.jpg - 3.jpg - 4.jpg - 5.jpg
    """
    H_to_center = {
        CENTER_ID: np.eye(3, dtype=np.float64)
    }

    H_2_to_3 = estimate_homography(images[2], images[3], "2_to_3")
    H_1_to_2 = estimate_homography(images[1], images[2], "1_to_2")

    H_4_to_3 = estimate_homography(images[4], images[3], "4_to_3")
    H_5_to_4 = estimate_homography(images[5], images[4], "5_to_4")

    H_to_center[2] = H_2_to_3
    H_to_center[1] = H_2_to_3 @ H_1_to_2

    H_to_center[4] = H_4_to_3
    H_to_center[5] = H_4_to_3 @ H_5_to_4

    return H_to_center


def get_image_corners(img):
    """Return the four corner points of an image."""
    h, w = img.shape[:2]

    corners = np.float32([
        [0, 0],
        [w, 0],
        [w, h],
        [0, h]
    ]).reshape(-1, 1, 2)

    return corners


def compute_canvas(images, H_to_center):
    """Compute the canvas size that can contain all warped images."""
    all_corners = []

    for idx in IMAGE_ORDER:
        img = images[idx]
        corners = get_image_corners(img)
        warped_corners = cv.perspectiveTransform(corners, H_to_center[idx])
        all_corners.append(warped_corners)

    all_corners = np.concatenate(all_corners, axis=0)

    x_min, y_min = np.floor(all_corners.min(axis=0).ravel()).astype(int)
    x_max, y_max = np.ceil(all_corners.max(axis=0).ravel()).astype(int)

    canvas_w = int(x_max - x_min)
    canvas_h = int(y_max - y_min)

    translation = np.array([
        [1, 0, -x_min],
        [0, 1, -y_min],
        [0, 0, 1]
    ], dtype=np.float64)

    return translation, canvas_w, canvas_h


def make_feather_weight(mask):
    """
    Create a feather weight map.
    Pixels near image boundaries get lower weights than pixels near the center.
    """
    mask = (mask > 0).astype(np.uint8) * 255
    weight = cv.distanceTransform(mask, cv.DIST_L2, 5)

    if weight.max() > 0:
        weight = weight / weight.max()

    return weight.astype(np.float32) + 1e-6


def warp_and_blend(images, H_to_center, translation, canvas_w, canvas_h):
    """Warp all images to the panorama canvas and blend them."""
    result = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
    weight_sum = np.zeros((canvas_h, canvas_w), dtype=np.float32)

    blend_order = [3, 2, 4, 1, 5]

    for idx in blend_order:
        img = images[idx]
        h, w = img.shape[:2]

        H_canvas = translation @ H_to_center[idx]

        warped_img = cv.warpPerspective(
            img,
            H_canvas,
            (canvas_w, canvas_h),
            flags=cv.INTER_LINEAR,
            borderMode=cv.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )

        mask = np.ones((h, w), dtype=np.uint8) * 255

        warped_mask = cv.warpPerspective(
            mask,
            H_canvas,
            (canvas_w, canvas_h),
            flags=cv.INTER_NEAREST,
            borderMode=cv.BORDER_CONSTANT,
            borderValue=0
        )

        weight = make_feather_weight(warped_mask)

        result += warped_img.astype(np.float32) * weight[:, :, np.newaxis]
        weight_sum += weight

    result = result / np.maximum(weight_sum[:, :, np.newaxis], 1e-6)
    result = np.clip(result, 0, 255).astype(np.uint8)

    valid_mask = (weight_sum > 1e-6).astype(np.uint8) * 255

    return result, valid_mask


def crop_black_border(img, mask, margin=5):
    """Remove black borders around the panorama."""
    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        return img

    largest = max(contours, key=cv.contourArea)
    x, y, w, h = cv.boundingRect(largest)

    x1 = max(x + margin, 0)
    y1 = max(y + margin, 0)
    x2 = min(x + w - margin, img.shape[1])
    y2 = min(y + h - margin, img.shape[0])

    return img[y1:y2, x1:x2]


def make_preview(img, max_width=PREVIEW_MAX_WIDTH, max_height=PREVIEW_MAX_HEIGHT):
    """
    Resize the panorama only for display.
    The saved output image keeps its original result size.
    """
    h, w = img.shape[:2]

    scale_w = max_width / w
    scale_h = max_height / h
    scale = min(scale_w, scale_h, 1.0)

    preview_w = int(w * scale)
    preview_h = int(h * scale)

    preview = cv.resize(img, (preview_w, preview_h), interpolation=cv.INTER_AREA)

    return preview


def stitch_images(images):
    """Create a panorama from five input images."""
    H_to_center = compute_homographies_to_center(images)

    translation, canvas_w, canvas_h = compute_canvas(images, H_to_center)

    panorama, valid_mask = warp_and_blend(
        images,
        H_to_center,
        translation,
        canvas_w,
        canvas_h
    )

    panorama = crop_black_border(panorama, valid_mask)

    return panorama


def main():
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    images = load_images("images")
    images = resize_images(images)

    panorama = stitch_images(images)

    save_path = output_dir / "panorama.jpg"
    cv.imwrite(str(save_path), panorama)

    print(f"Saved result: {save_path}")

    preview = make_preview(panorama)

    cv.imshow("Panorama Preview", preview)
    cv.waitKey(0)
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()