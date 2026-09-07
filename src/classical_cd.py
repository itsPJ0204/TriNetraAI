import cv2
import numpy as np

def run_classical_cd(img_t1: np.ndarray, img_t2: np.ndarray, threshold: int = 40) -> np.ndarray:
    gray1 = cv2.cvtColor(img_t1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img_t2, cv2.COLOR_RGB2GRAY)

    blur1 = cv2.GaussianBlur(gray1, (5, 5), 0)
    blur2 = cv2.GaussianBlur(gray2, (5, 5), 0)

    diff = cv2.absdiff(blur1, blur2)
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    return mask
