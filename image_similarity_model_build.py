import os
import pickle
import numpy as np
from PIL import Image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration ---
IMG_SIZE = 224
# Path to your folder of product images
PRODUCT_FOLDER = "/Users/mshinde/Desktop/Portfolio/jif_train"
# Path to save the indexed features
FEATURES_FILE = "product_features.pkl"
# Path to the new image you want to find similar items for
QUERY_IMAGE = "/Users/mshinde/Desktop/Portfolio/ecom_violation_agent/jif_classifier/test/product/B0FLXL32B6_0.jpg"

# -----------------------------------------------------------------------------
#  HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_feature_extraction_model():
    """
    Creates the VGG16 model pre-loaded with weights from ImageNet,
    modified to output feature vectors.
    """
    # Load VGG16 model, excluding the top classification layers
    base_model = VGG16(weights='imagenet', include_top=False, 
                       input_shape=(IMG_SIZE, IMG_SIZE, 3))
    # We will use the output of the 'block5_pool' layer as our feature vector
    model = Model(inputs=base_model.input, 
                  outputs=base_model.get_layer('block5_pool').output)
    return model

def preprocess_image(img_path):
    """
    Loads, resizes, and pre-processes an image for VGG16.
    """
    try:
        # Load image, resizing to the standard 224x224
        img = image.load_img(img_path, target_size=(IMG_SIZE, IMG_SIZE))
        # Convert image to a numpy array
        img_array = image.img_to_array(img)
        # Expand dimensions to create a "batch" of 1
        img_array_expanded = np.expand_dims(img_array, axis=0)
        # Pre-process the image for VGG16 (e.g., color correction, normalization)
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
    # Get the feature vector
    features = model.predict(processed_img)
    # Flatten the 7x7x512 feature map into a 1D vector
    return features.flatten()

# -----------------------------------------------------------------------------
#  PART 1: "TRAIN" (INDEX) YOUR PRODUCT FOLDER
#  Run this function once to build your feature database.
# -----------------------------------------------------------------------------

def index_product_folder(folder_path, model):
    """
    Loops through all images in a folder, extracts their features,
    and saves them to a file.
    """
    print("Starting product indexing...")
    features_db = {}
    
    # Get a list of valid image file extensions
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}

    for img_file in os.listdir(folder_path):
        # Check for valid image extensions
        file_ext = os.path.splitext(img_file)[1].lower()
        if file_ext not in valid_extensions:
            continue
            
        img_path = os.path.join(folder_path, img_file)
        print(f"  Indexing {img_file}...")
        
        features = extract_features(img_path, model)
        if features is not None:
            features_db[img_path] = features

    print(f"\nIndexing complete. {len(features_db)} images indexed.")

    # Save the feature database to a file
    with open(FEATURES_FILE, "wb") as f:
        pickle.dump(features_db, f)
    print(f"Features saved to {FEATURES_FILE}")
    return features_db

# -----------------------------------------------------------------------------
#  PART 2: "SEARCH" (FIND SIMILAR IMAGES)
#  Run this function anytime you want to find similar items.
# -----------------------------------------------------------------------------

def find_similar_images(query_img_path, features_db, model, top_n=5):
    """
    Finds the 'top_n' most similar images from the feature database
    to the query image.
    """
    print(f"Loading features from {FEATURES_FILE}...")
    # Load the pre-computed features
    with open(FEATURES_FILE, "rb") as f:
        features_db = pickle.load(f)

    if not features_db:
        print("Feature database is empty. Please run indexing first.")
        return

    print(f"Extracting features for query image: {query_img_path}...")
    # Extract features for the new query image
    query_features = extract_features(query_img_path, model)
    if query_features is None:
        print("Could not process query image.")
        return

    # Prepare for similarity calculation
    db_paths = list(features_db.keys())
    db_features = np.array(list(features_db.values()))
    
    # Reshape query features for comparison
    query_features_reshaped = query_features.reshape(1, -1)

    print("Calculating similarities...")
    # Calculate cosine similarity between the query image and all product images
    similarities = cosine_similarity(query_features_reshaped, db_features)
    
    # Get the scores as a flat list
    similarity_scores = similarities[0]

    # Get the indices of the top_n most similar images
    # `argsort` sorts from smallest to largest, so we use `[-top_n:]`
    # and then reverse with `[::-1]` to get largest to smallest
    top_indices = np.argsort(similarity_scores)[-top_n:][::-1]

    print("\n--- Top 5 Similar Products ---")
    for i in top_indices:
        img_path = db_paths[i]
        score = similarity_scores[i]
        print(f"  - Path: {img_path} (Similarity: {score:.4f})")

# -----------------------------------------------------------------------------
#  MAIN EXECUTION
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
    # Load the model
    model = get_feature_extraction_model()

    # ---
    #  **Step 1: Run this block to index your folder**
    #  (You can comment this out after you run it once)
    # ---
    print("=== PART 1: INDEXING ===")
    index_product_folder(PRODUCT_FOLDER, model)
    print("\n" + "="*30 + "\n")

    # ---
    #  **Step 2: Run this block to search for an image**
    # ---
    print("=== PART 2: SEARCHING ===")
    if not os.path.exists(FEATURES_FILE):
        print("Features file not found. Please run the indexing part first.")
    elif not os.path.exists(QUERY_IMAGE):
        print(f"Query image not found at: {QUERY_IMAGE}")
    else:
        find_similar_images(QUERY_IMAGE, FEATURES_FILE, model, top_n=5)