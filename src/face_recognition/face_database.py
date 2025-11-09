import os
import json
import numpy as np
from config.paths import FACE_SAMPLE_DIR, FACE_DATA_FILE
from config.settings import FACE_MATCHING_THRESHOLD

class FaceDatabase:
    def __init__(self):
        # Dictionary to store face feature vectors
        self.face_data = {}

        # Create folder for saving face data
        self.save_dir = FACE_SAMPLE_DIR
        self.face_data_file = FACE_DATA_FILE

        # Load existing face data
        self.load_faces()

    def load_faces(self):
        # Load registered face data from file
        if not os.path.exists(self.face_data_file):
            with open(self.face_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        else:
            with open(self.face_data_file, 'r') as f:
                data = json.load(f)
                # Convert list data back to numpy array
                for name, embedding_list in data.items():
                    self.face_data[name] = np.array(embedding_list)
            print(f"Loaded {len(self.face_data)} face data entries")

    def save_faces(self):
        # Save face data to file
        # Convert numpy arrays to lists for JSON serialization
        save_data = {name: embedding.tolist() for name, embedding in self.face_data.items()}
        with open(self.face_data_file, 'w') as f:
            json.dump(save_data, f)
        print(f"Saved {len(self.face_data)} face data entries")

    def delete_faces(self, name):
        # Delete face data by name
        if name in self.face_data:
            del self.face_data[name]
            # Synchronize and save to local file
            self.save_faces()
            print(f"Successfully deleted face data for {name}")
            return True
        else:
            print(f"No face data found for {name}")
            return False

    def compare_faces(self, input_embedding, threshold):
        # Find the vector most matching the input face feature in the current database (must exceed the matching threshold), return similarity and name
        if not self.face_data:
            print("Face database is empty, cannot perform comparison")
            return 0, "Unknown"

        # Initialize return values
        max_similarity = 0
        most_similar_name = "Unknown"

        for name, db_embedding in self.face_data.items():
            # Calculate similarity
            similarity = np.dot(input_embedding, db_embedding)

            # If similarity exceeds the threshold, it is considered a successful match
            if similarity > threshold:
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_name = name

        print(f"Maximum similarity: {max_similarity:.4f}, corresponding name: {most_similar_name}")
        return max_similarity, most_similar_name

    def show_names(self):
        for name in self.face_data:
            print(name)