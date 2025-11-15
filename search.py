import os
import pickle
import argparse
import numpy as np
from PIL import Image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration ---
IMG_SIZE = 224
# Path to the saved features file from your "training" script
FEATURES_FILE = "product_features.pkl"
TOP_N = 5 # Number of similar results to show

# -----------------------------------------------------------------------------
#  MODEL & PRE-PROCESSING FUNCTIONS (Copied from previous script)
# -----------------------------------------------------------------------------

def get_feature_extraction_model():
    """
    Creates the VGG16 model pre-loaded with weights from ImageNet,
    modified to output feature vectors.
    """
    base_model = VGG16(weights='imagenet', include_top=False, 
                       input_shape=(IMG_SIZE, IMG_SIZE, 3))
    model = Model(inputs=base_model.input, 
                  outputs=base_model.get_layer('block5_pool').output)
    return model

def preprocess_image(img_path):
    """
    Loads, resizes, and pre-processes an image for VGG16.
    """
    try:
        img = image.load_img(img_path, target_size=(IMG_SIZE, IMG_SIZE))
        img_array = image.img_to_array(img)
        img_array_expanded = np.expand_dims(img_array, axis=0)
        return preprocess_input(img_array_expanded)
    except Exception as e:
        print(f"Error processing image {img_path}: {e}")
        return None

def extract_features(img_path, model):
    """
    Extracts the feature vector from a single image.
    """
    processed_img = preprocess_image(img_path)
    if processed_img is None:
        return None
    features = model.predict(processed_img, verbose=0) # Set verbose=0 to hide progress
    return features.flatten()

# -----------------------------------------------------------------------------
#  SEARCH FUNCTIONS
# -----------------------------------------------------------------------------

def load_feature_database(features_file):
    """Loads the pre-computed features from the pickle file."""
    if not os.path.exists(features_file):
        print(f"Error: Features file not found at {features_file}")
        print("Please run the indexing script first to create it.")
        return None
        
    with open(features_file, "rb") as f:
        features_db = pickle.load(f)
    
    # Separate the paths from the feature vectors for easy searching
    db_paths = list(features_db.keys())
    db_features_array = np.array(list(features_db.values()))
    
    print(f"Loaded feature database with {len(db_paths)} images.")
    return db_paths, db_features_array

def search_similar(query_features, db_features_array, db_paths, top_n):
    """
    Calculates cosine similarity and returns the top N matches.
    """
    # Reshape query features for comparison
    query_features_reshaped = query_features.reshape(1, -1)

    # Calculate cosine similarity
    similarities = cosine_similarity(query_features_reshaped, db_features_array)
    
    # Get the scores as a flat list
    similarity_scores = similarities[0]

    # Get the indices of the top_n most similar images
    top_indices = np.argsort(similarity_scores)[-top_n:][::-1]

    # Create a list of (path, score) tuples
    results = []
    for i in top_indices:
        results.append((db_paths[i], similarity_scores[i]))
    
    return results

# -----------------------------------------------------------------------------
#  MAIN EXECUTION
# -----------------------------------------------------------------------------

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Image Similarity Search")
    
    # Create a mutually exclusive group: user must supply one or the other
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", help="Path to a single query image.")
    group.add_argument("--folder", help="Path to a folder of query images.")
    
    args = parser.parse_args()

    # --- 1. Load Model and Feature Database ---
    print("Loading feature extraction model...")
    model = get_feature_extraction_model()
    
    print("Loading product feature database...")
    db_data = load_feature_database(FEATURES_FILE)
    if db_data is None:
        return # Exit if database couldn't be loaded
    
    db_paths, db_features_array = db_data

    # --- 2. Get list of images to query ---
    query_image_paths = []
    if args.image:
        if os.path.exists(args.image):
            query_image_paths.append(args.image)
        else:
            print(f"Error: Query image not found at {args.image}")
            return
            
    elif args.folder:
        if not os.path.exists(args.folder):
            print(f"Error: Query folder not found at {args.folder}")
            return
            
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        for filename in os.listdir(args.folder):
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_extensions:
                query_image_paths.append(os.path.join(args.folder, filename))
        
        if not query_image_paths:
            print(f"No valid images found in folder: {args.folder}")
            return
            
    # --- 3. Process each query image ---
    for query_path in query_image_paths:
        print(f"\n--- Querying for: {query_path} ---")
        
        # a. Extract features for the query image
        query_features = extract_features(query_path, model)
        if query_features is None:
            continue
            
        # b. Find similar images
        results = search_similar(query_features, db_features_array, db_paths, TOP_N)
        
        # c. Print results
        print(f"Top {TOP_N} similar results:")
        for path, score in results:
            # Don't show the query image itself if it's in the database
            if path == query_path and score > 0.999:
                continue
            print(f"  - Path: {path} (Similarity: {score:.4f})")
            
        print("-" * (18 + len(query_path))) # Print separator

if __name__ == "__main__":
    main()