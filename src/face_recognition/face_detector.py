import time
import cv2
from insightface.app import FaceAnalysis

from config.settings import FACE_MATCHING_THRESHOLD
from src.face_recognition.face_database import FaceDatabase
from src.face_recognition.anti_spoof_predict import AntiSpoofPredict

class FaceDetector:
    def __init__(self):
        # Initialize face analysis application
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # Use GPU; set ctx_id=-1 if using CPU

        # Dictionary to store face feature vectors
        self.face_database = FaceDatabase()

        self.liveness_model = AntiSpoofPredict()

    def run(self, username):
        start_time = time.time()
        last_detect_time = 0
        detection_counts = 0
        face_detection = False
        identity_result = None

        # Initialize camera
        cap = cv2.VideoCapture(0)  # 0 indicates the default camera

        # Set camera parameters (optional)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("Press 'q' to exit the program")

        while True:
            current_time = time.time()
            # Read a frame
            ret, frame = cap.read()
            if not ret:
                print("Failed to get video frame")
                break

            # Horizontally flip the image (mirror effect)
            frame = cv2.flip(frame, 1)

            # Perform face detection and analysis
            faces = self.app.get(frame)

            if len(faces) == 0:
                # Display prompt
                cv2.putText(frame, "No face detected. Please adjust your position", (250, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # Display the number of detected faces
                cv2.putText(frame, f"Faces: {len(faces)}", (250, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Get the largest face (calculated by area)
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

                # Get face bounding box
                bbox = face.bbox.astype(int)

                # Liveness detection
                is_real = self.liveness_model.predict(frame, bbox)
                if is_real:
                    print("It's a real face")
                    # Get feature vector
                    embedding = face.normed_embedding

                    # Get comparison result
                    max_similarity, identity = self.face_database.compare_faces(embedding, FACE_MATCHING_THRESHOLD)

                    if max_similarity > 0 & (current_time - last_detect_time > 0.5):
                        if not face_detection:
                            detection_counts += 1
                            last_detect_time = current_time
                            identity_result = identity
                            if detection_counts > 5:
                                face_detection = True

                    # Display recognition result
                    label = f"{identity} ({max_similarity:.2f})"
                    color = (0, 255, 0)  # Green box
                else:
                    print("It's a fake face")
                    label = f"Fake Face"
                    color = (0, 0, 255) # Red box

                # Draw bounding box
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                # Display label
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Display image
            cv2.imshow('Real-time Face Detection', frame)

            # Exit if face is detected
            if face_detection:
                if current_time - last_detect_time > 2:
                    break

            # Detection timeout
            if current_time - start_time > 15:
                print("Time Out!")
                break

            # Press 'q' to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release resources
        cap.release()
        cv2.destroyAllWindows()

        if identity_result == username:
            return True
        else:
            return False