import cv2
import time
import os
import numpy as np
from datetime import datetime

from insightface.app import FaceAnalysis
from src.face_recognition.anti_spoof_predict import AntiSpoofPredict
from src.face_recognition.face_database import FaceDatabase
from config.settings import RegistionParam, REGISTER_FACE_MATCHING_THRESHOLD

FACE_STATUS_VALID = 0
FACE_STATUS_INVALID = 1
FACE_STATUS_DUPLICATE = 2

class FaceRecorder:
    def __init__(self):
        # Initialize face analysis application
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1)  # Use GPU; set ctx_id=-1 if using CPU

        self.liveness_model = AntiSpoofPredict()

        # Dictionary to store face feature vectors
        self.face_database = FaceDatabase()
        # Registration-related parameters
        self.param = RegistionParam()

    def check_face_validity(self, frame, face, bbox):
        # Liveness detection
        is_real = self.liveness_model.predict(frame, bbox)

        if is_real & (face.det_score > self.param.confidence_threshold):
            embedding = face.normed_embedding
            max_similarity, identity = self.face_database.compare_faces(embedding, REGISTER_FACE_MATCHING_THRESHOLD)
            if max_similarity == 0:
                return FACE_STATUS_VALID
            else:
                print("Duplicate Face with user:{}".format(identity))
                return FACE_STATUS_DUPLICATE
        else:
            return FACE_STATUS_INVALID

    def register_face(self, name, embedding, face_img):
        """Register a new face"""
        self.face_database.face_data[name] = embedding

        # Save face image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        face_filename = os.path.join(self.face_database.save_dir, f"{name}_{timestamp}.jpg")
        cv2.imwrite(face_filename, face_img)

        # Save data to file
        self.face_database.save_faces()

        print(f"Successfully registered: {name}")
        return True

    def run(self, name):
        """Run the main program"""
        # Record start time
        start_time = time.time()
        # Time of the last valid frame
        last_collect_time = 0
        # Store collected valid feature vectors
        collected_embedding = []
        registration_completion = False

        # Initialize camera
        print("Turn on the camera")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while True:
            elapsed_time = time.time() - start_time
            ret, frame = cap.read()
            if not ret:
                print("Failed to get video frame")
                break

            # Horizontally flip the image (mirror effect)
            frame = cv2.flip(frame, 1)

            # Detect faces (without extracting features, for display only)
            faces = self.app.get(frame)

            if len(faces) == 0:
                # Prompt: No face detected
                face_valid = FACE_STATUS_INVALID
            else:
                # Get the largest face (calculated by area) for registration
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                bbox = face.bbox.astype(int)
                face_img = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]

                face_valid = self.check_face_validity(frame, face, bbox)

                if face_valid == FACE_STATUS_VALID:
                    label = "Valid Face"
                    color = (0, 255, 0)
                elif face_valid == FACE_STATUS_DUPLICATE:
                    label = "Duplicate Face"
                    color = (0, 0, 255)
                else:
                    label = "Invalid Face"
                    color = (0, 0, 255)

                # Draw bounding box
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                # Display label
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Determine current registration status
            if registration_completion:
                cv2.putText(frame, f"Face Detection Complete!", (200, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, f"Face Detection in Process...", (200, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                # Require a certain interval from the last valid frame
                if face_valid == FACE_STATUS_VALID & (time.time() - last_collect_time > self.param.frame_interval):
                    # Extract feature vector
                    current_embedding = face.normed_embedding

                    # Update valid frame timestamp
                    last_collect_time = time.time()
                    collected_embedding.append(current_embedding)
                    print("debug: saved face embedding:", len(collected_embedding))
                    if len(collected_embedding) >= self.param.required_frames:
                        # Collected enough valid frames, proceed with registration
                        avg_embedding = np.mean(collected_embedding, axis=0)
                        save_img = face_img
                        print("Register Successfully!")
                        registration_completion = True

            cv2.putText(frame, "Press 'q' to quit", (500, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Display image
            cv2.imshow('Face Registration', frame)

            # Keyboard operation
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("User manually exited the program")
                break

            # Check exit conditions
            if registration_completion:
                # Display for 2 seconds after successful registration before exiting
                if time.time() - last_collect_time > 3:
                    break
            elif elapsed_time > self.param.detection_time_limit:
                print("Registration time exceeded the limit!")
                break

        if registration_completion:
            self.register_face(name, avg_embedding, save_img)
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        print("Program exited")

        return registration_completion