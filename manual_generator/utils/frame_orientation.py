import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

"""フレームの強制的な向き補正ユーティリティ.

現在の要件:
    - 常に上下反転を行う (以前の症状: 取得画像が上下逆)
    - さらに左右も常に反転して欲しい (新規要望)

OpenCV の cv2.flip の flipCode:
    0  : x軸(上下)反転
    1  : y軸(左右)反転
    -1 : 両方反転 (上下 + 左右)

ここでは両方反転をデフォルトとし、フラグで将来制御できるようにする。
"""

ALWAYS_FLIP_VERTICAL = True   # 互換性維持用 (上下反転要求)
ALWAYS_FLIP_HORIZONTAL = True # 新要件 (左右反転要求)


def enforce_vertical_orientation(frame: np.ndarray) -> np.ndarray:
    """強制的にフレームを反転補正する。

    現仕様:
      - ALWAYS_FLIP_VERTICAL と ALWAYS_FLIP_HORIZONTAL が両方 True の場合は
        cv2.flip(frame, -1) で同時反転。
      - 片方のみ True の場合はそれぞれ 0 または 1 を指定。
      - どちらも False の場合はそのまま返す。
    今後 EXIF / メタデータ判定へ差し替え可能な拡張ポイント。
    """
    try:
        if frame is None:
            return frame
        if ALWAYS_FLIP_VERTICAL and ALWAYS_FLIP_HORIZONTAL:
            return cv2.flip(frame, -1)
        if ALWAYS_FLIP_VERTICAL:
            return cv2.flip(frame, 0)
        if ALWAYS_FLIP_HORIZONTAL:
            return cv2.flip(frame, 1)
        return frame
    except Exception:
        return frame

__all__ = [
    "enforce_vertical_orientation",
    "ALWAYS_FLIP_VERTICAL",
    "ALWAYS_FLIP_HORIZONTAL",
]
