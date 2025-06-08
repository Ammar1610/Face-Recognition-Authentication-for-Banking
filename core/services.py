import cv2
import time
import logging
import numpy as np
from django.urls import reverse

logger = logging.getLogger(__name__)

class FaceVerificationService:
    @staticmethod
    def get_working_camera():
        """Try different camera backends and indices to find a working configuration"""
        backends = [
            cv2.CAP_DSHOW,  # DirectShow (usually works best on Windows)
            cv2.CAP_MSMF,   # Microsoft Media Foundation
            0               # Default backend
        ]
        
        for backend in backends:
            for camera_index in [0, 1]:  # Try first two cameras
                try:
                    cap = cv2.VideoCapture(camera_index, backend)
                    if cap.isOpened():
                        # Test if we can actually read a frame
                        for _ in range(3):  # Try 3 times
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                logger.info(f"Working camera found: index {camera_index}, backend {backend}")
                                return cap
                            time.sleep(0.1)
                        cap.release()
                except Exception as e:
                    logger.warning(f"Camera init failed with backend {backend}: {str(e)}")
                    continue
                    
        logger.error("No working camera configuration found")
        return None

    @staticmethod
    def capture_frame():
        """Capture frame from camera with error handling"""
        cap = FaceVerificationService.get_working_camera()
        if not cap:
            return None

        try:
            frame = None
            for _ in range(5):  # Try 5 times to get a frame
                ret, frame = cap.read()
                if ret:
                    break
                time.sleep(0.1)
            return frame if ret else None
        finally:
            cap.release()