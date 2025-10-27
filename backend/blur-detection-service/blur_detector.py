import cv2
import numpy as np
import logging
from typing import Tuple, Optional, List
from io import BytesIO
import blur_detector as bd

logger = logging.getLogger(__name__)

class BlurDetector:

    def __init__(self):
        self.laplacian_threshold = 100.0
        self.variance_threshold = 500.0
        # blur-detector parameters
        self.downsampling_factor = 1
        self.num_scales = 3
        self.scale_start = 1
        self.num_iterations_RF_filter = 3
        self.show_progress = False

        # Face detection cascade classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    def detect_blur_from_bytes(
        self,
        image_bytes: bytes,
        threshold: float = 0.30,
        method: str = "hybrid",
        use_face_detection: bool = True
    ) -> Tuple[float, bool]:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Image loading failed")
            return self._analyze_blur(image, threshold, method, use_face_detection)
        except Exception as e:
            logger.error(f"An error occurred during image shake detection.: {e}")
            raise

    def detect_blur_from_file(
        self,
        image_path: str,
        threshold: float = 0.30,
        method: str = "hybrid",
        use_face_detection: bool = True
    ) -> Tuple[float, bool]:
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"The image file cannot be loaded.: {image_path}")
            return self._analyze_blur(image, threshold, method, use_face_detection)
        except Exception as e:
            logger.error(f"An error occurred during hand shake detection from the file.: {e}")
            raise

    def _detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces from image and return face coordinates
        Returns: List of (x, y, w, h) tuples representing face rectangles
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Adjust face detection parameters (for improved accuracy)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        # Sort by face size (prioritize larger faces)
        faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)

        logger.info(f"Detected {len(faces)} faces")
        return faces

    def _get_face_roi(self, image: np.ndarray, face_rect: Tuple[int, int, int, int],
                     expand_ratio: float = 0.30) -> np.ndarray:
        x, y, w, h = face_rect
        img_h, img_w = image.shape[:2]

        # Calculate margin
        expand_w = int(w * expand_ratio)
        expand_h = int(h * expand_ratio)

        # Calculate extended coordinates (keep within image bounds)
        x1 = max(0, x - expand_w)
        y1 = max(0, y - expand_h)
        x2 = min(img_w, x + w + expand_w)
        y2 = min(img_h, y + h + expand_h)

        return image[y1:y2, x1:x2]

    def _analyze_face_blur(self, image: np.ndarray, faces: List[Tuple[int, int, int, int]],
                          threshold: float, method: str) -> Tuple[float, bool]:
        """
        Perform blur detection only on detected face regions
        """
        if not faces:
            logger.warning("No faces detected, falling back to full image analysis")
            return self._analyze_blur(image, threshold, method, use_face_detection=False)

        # Select the largest face
        main_face = faces[0]
        face_roi = self._get_face_roi(image, main_face)

        if face_roi.size == 0:
            logger.warning("Face ROI is empty, falling back to full image analysis")
            return self._analyze_blur(image, threshold, method, use_face_detection=False)

        logger.info(f"Analyzing face region: {face_roi.shape}")

        # Perform blur detection on face region
        return self._analyze_blur(face_roi, threshold, method, use_face_detection=False)

    def _fft_blur_score(self, gray: np.ndarray) -> float:
        """
        Analyze high-frequency components of image using FFT to calculate blur score
        """
        # 2D FFT
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = np.abs(fft_shift)
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        # Mask center portion (low frequency)
        mask = np.ones((h, w), dtype=bool)
        mask[center_y - h//4:center_y + h//4, center_x - w//4:center_x + w//4] = False
        high_freq_energy = np.sum(magnitude_spectrum[mask])
        total_energy = np.sum(magnitude_spectrum) + 1e-8
        high_freq_ratio = high_freq_energy / total_energy
        # Lower high-frequency ratio indicates more blur -> normalize
        blur_score = 1.0 - min(high_freq_ratio * 2.0, 1.0)  # scale factor=2 to fit in 0-1 range
        return blur_score

    def _analyze_blur(self, image: np.ndarray, threshold: float, method: str = "hybrid",
                     use_face_detection: bool = True) -> Tuple[float, bool]:
        # If face detection is enabled, analyze face region only
        if use_face_detection:
            faces = self._detect_faces(image)
            if faces:
                return self._analyze_face_blur(image, faces, threshold, method)

        # If face detection is disabled or no faces found, analyze entire image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if method == "laplacian":
            # ① Laplacian variance
            fm = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_score = 1.0 / (1.0 + fm / 40.0)
        elif method == "fft":
            # ② FFT high-frequency ratio
            blur_score = self._fft_blur_score(gray)
        elif method == "hybrid":
            # ① + ② combination
            lap_score = 1.0 / (1.0 + cv2.Laplacian(gray, cv2.CV_64F).var() / 100.0)
            fft_score = self._fft_blur_score(gray)
            # Weighting (based on empirical values)
            blur_score = 0.5 * lap_score + 0.5 * fft_score
        else:
            # Traditional blur-detector fallback
            try:
                blur_map = bd.detectBlur(
                    gray,
                    downsampling_factor=self.downsampling_factor,
                    num_scales=self.num_scales,
                    scale_start=self.scale_start,
                    num_iterations_RF_filter=self.num_iterations_RF_filter,
                    show_progress=self.show_progress
                )
                blur_score = np.mean(blur_map) / 255.0
            except Exception as e:
                logger.warning(f"blur-detector failed, fallback to Laplacian variance: {e}")
                fm = cv2.Laplacian(gray, cv2.CV_64F).var()
                blur_score = 1.0 / (1.0 + fm / 40.0)

        blur_score = max(0.0, min(1.0, blur_score))
        is_blurred = blur_score > threshold
        logger.info(f"Method={method}, score={blur_score:.4f}, threshold={threshold}, blurred={is_blurred}")
        return blur_score, is_blurred

    def _laplacian_variance(self, gray: np.ndarray) -> float:
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        normalized = 1.0 / (1.0 + variance / self.laplacian_threshold)
        return normalized

    def _gradient_magnitude(self, gray: np.ndarray) -> float:
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        mean_magnitude = np.mean(magnitude)
        normalized = 1.0 / (1.0 + mean_magnitude / 50.0)
        return normalized

    def _fft_analysis(self, gray: np.ndarray) -> float:
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = np.abs(fft_shift)
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        mask = np.ones((h, w), dtype=bool)
        mask[center_y-h//8:center_y+h//8, center_x-w//8:center_x+w//8] = False
        high_freq_energy = np.sum(magnitude_spectrum[mask])
        total_energy = np.sum(magnitude_spectrum)
        high_freq_ratio = high_freq_energy / (total_energy + 1e-8)
        normalized = 1.0 - min(high_freq_ratio * 2.0, 1.0)
        return normalized

    def get_blur_quality_description(self, blur_score: float) -> str:
        if blur_score < 0.2:
            return "Very sharp"
        elif blur_score < 0.4:
            return "Sharp"
        elif blur_score < 0.6:
            return "Somewhat blurry"
        elif blur_score < 0.8:
            return "Blurry"
        else:
            return "Very blurry"

blur_detector = BlurDetector()
