"""
ComplyVision - Image Preprocessing Module
Implements FR-2 and NFR-3: Grayscale, CLAHE contrast enhancement, deskewing, and blur detection.
"""
import cv2
import numpy as np
import os

class ImagePreprocessor:
    def __init__(self, blur_threshold: float = 65.0):
        self.blur_threshold = blur_threshold

    def calculate_blur(self, gray_image: np.ndarray) -> float:
        """Computes variance of Laplacian as blur metric. Low variance means blurry."""
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance = float(laplacian.var())
        return variance

    def is_blurry(self, gray_image: np.ndarray) -> tuple[bool, float]:
        """Returns True if variance is below threshold, along with the score."""
        score = self.calculate_blur(gray_image)
        return (score < self.blur_threshold, score)

    def enhance_contrast(self, gray_image: np.ndarray) -> np.ndarray:
        """Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to balance uneven lighting."""
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return clahe.apply(gray_image)

    def deskew(self, image: np.ndarray, gray: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Detects predominant text orientation angle using thresholding and minAreaRect,
        and deskews the image. If skew angle is minimal (< 0.5 deg) or extreme (> 45 deg), leaves as is.
        """
        try:
            # Otsu thresholding to find text blocks
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find non-zero coordinates
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return image, 0.0

            # Compute minAreaRect
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]

            # Adjust angle for OpenCV convention
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Only deskew if angle is significant
            if abs(angle) < 0.5 or abs(angle) > 40:
                return image, 0.0

            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return deskewed, float(angle)
        except Exception:
            return image, 0.0

    def process(self, image_path: str, output_path: str = None) -> dict:
        """
        Full pre-processing pipeline:
        1. Read image
        2. Detect blur
        3. Convert to grayscale & apply CLAHE
        4. Deskew
        5. Return preprocessed image path & metadata
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not decode image at {image_path}")

        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Blur check (NFR-3)
        blurry, blur_score = self.is_blurry(gray)

        # Contrast enhancement
        enhanced_gray = self.enhance_contrast(gray)

        # Deskewing
        deskewed_color, skew_angle = self.deskew(image, gray)
        deskewed_gray = cv2.cvtColor(deskewed_color, cv2.COLOR_BGR2GRAY)
        deskewed_enhanced = self.enhance_contrast(deskewed_gray)

        # Save preprocessed image if path given
        if output_path is None:
            dir_name, base_name = os.path.split(image_path)
            output_path = os.path.join(dir_name, f"pre_{base_name}")

        cv2.imwrite(output_path, deskewed_enhanced)

        return {
            "original_path": image_path,
            "preprocessed_path": output_path,
            "width": w,
            "height": h,
            "is_blurry": blurry,
            "blur_score": round(blur_score, 2),
            "skew_angle": round(skew_angle, 2),
            "status": "warning_blurry" if blurry else "success"
        }
