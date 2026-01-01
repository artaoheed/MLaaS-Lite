import os
import joblib
import pandas as pd
from fastapi import FastAPI, Request
from google.cloud import storage

app = FastAPI()
model = None

@app.on_event("startup")
def load_model():
    global model
    print("🚀 Starting Model Server (GCP Mode)...")
    
    try:
        # 1. Setup GCS Client
        # It automatically looks for GOOGLE_APPLICATION_CREDENTIALS env var
        storage_client = storage.Client()
        
        bucket_name = os.getenv("GCP_BUCKET_NAME", "ml-models")
        blob_path = os.getenv("MODEL_S3_KEY") # e.g. "omega/1/model.pkl"
        
        print(f"📥 Downloading gs://{bucket_name}/{blob_path} ...")
        
        # 2. Download
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename("/app/model.pkl")
        
        # 3. Load
        model = joblib.load("/app/model.pkl")
        print("✅ Model loaded successfully!")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR loading model: {e}")
        raise e

@app.post("/predict")
async def predict(request: Request):
    if not model:
        return {"error": "Model not loaded"}
    
    data = await request.json()
    df = pd.DataFrame(data["features"])
    prediction = model.predict(df)
    return {"prediction": prediction.tolist()}

@app.get("/health")
def health():
    return {"status": "healthy"}