import unittest
import numpy as np
import cv2
import os
import tempfile
from ocr.preprocessor import ImagePreprocessor

class TestImagePreprocessor(unittest.TestCase):
    def setUp(self):
        self.preprocessor = ImagePreprocessor(blur_threshold=65.0)

    def test_sharp_image_blur_detection(self):
        # Create a synthetic sharp image with strong edges
        img = np.zeros((300, 300), dtype=np.uint8)
        img[50:250, 50:250] = 255
        cv2.line(img, (0, 0), (300, 300), 255, 5)
        
        is_blurry, score = self.preprocessor.is_blurry(img)
        self.assertFalse(is_blurry)
        self.assertGreater(score, 65.0)

    def test_blurred_image_detection(self):
        # Create a heavily blurred image
        img = np.zeros((300, 300), dtype=np.uint8)
        img[50:250, 50:250] = 255
        blurred = cv2.GaussianBlur(img, (51, 51), 0)
        
        is_blurry, score = self.preprocessor.is_blurry(blurred)
        self.assertTrue(is_blurry)
        self.assertLess(score, 65.0)

    def test_clahe_contrast_enhancement(self):
        img = np.full((100, 100), 128, dtype=np.uint8)
        enhanced = self.preprocessor.enhance_contrast(img)
        self.assertEqual(enhanced.shape, img.shape)

if __name__ == '__main__':
    unittest.main()
