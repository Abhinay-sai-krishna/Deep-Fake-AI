"""
🧠 FaceForensics++ Benchmark Inference & Dataset Splitter
==========================================================
1. Runs the trained EfficientNet-B0 model on all 1,000 benchmark images
2. Classifies each as Real or Fake with confidence scores
3. Splits them into dataset/real and dataset/fake folders for retraining
4. Generates a detailed summary report
"""

import os
import sys
import shutil
import json
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from collections import Counter

# ===================== CONFIG =====================
BENCHMARK_DIR = os.path.join("faceforensics_benchmark", "faceforensics_benchmark_images")
DATASET_DIR = "./dataset"
REAL_DIR = os.path.join(DATASET_DIR, "real")
FAKE_DIR = os.path.join(DATASET_DIR, "fake")
MODEL_PATH = "deepfake_efficientnet_model.pth"
THRESHOLD = 0.5  # >= 0.5 = Fake, < 0.5 = Real
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===================== MODEL =====================
def build_model():
    model = models.efficientnet_b0(pretrained=False)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
        nn.Linear(num_ftrs, 128),
        nn.ReLU(),
        nn.Dropout(0.4),
        nn.Linear(128, 1),
        nn.Sigmoid()
    )
    return model

# ===================== MAIN =====================
def main():
    print("=" * 65)
    print("🧠 FaceForensics++ Benchmark — Model Inference & Dataset Split")
    print("=" * 65)
    print(f"  📁 Benchmark Dir:  {os.path.abspath(BENCHMARK_DIR)}")
    print(f"  🧪 Model:          {MODEL_PATH}")
    print(f"  📍 Device:         {DEVICE}")
    print(f"  🎯 Threshold:      {THRESHOLD} (>= Fake, < Real)")
    print("=" * 65)

    # 1. Load the model
    print("\n📦 Loading trained EfficientNet-B0 model...")
    model = build_model()
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        print(f"  ✅ Loaded weights from {MODEL_PATH}")
    else:
        print(f"  ⚠️  WARNING: {MODEL_PATH} not found! Using untrained model (results will be random).")
    
    model.to(DEVICE)
    model.eval()

    # 2. Define transforms (same as training)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 3. Get all benchmark images
    if not os.path.exists(BENCHMARK_DIR):
        print(f"❌ Benchmark directory not found: {BENCHMARK_DIR}")
        sys.exit(1)

    images = sorted([f for f in os.listdir(BENCHMARK_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))])
    print(f"\n🖼️  Found {len(images)} benchmark images\n")

    # 4. Run inference on each image
    results = []
    real_count = 0
    fake_count = 0
    confidence_real = []
    confidence_fake = []

    print("🔬 Running inference...")
    print("-" * 65)

    for idx, img_name in enumerate(images):
        img_path = os.path.join(BENCHMARK_DIR, img_name)
        
        try:
            image = Image.open(img_path).convert("RGB")
            input_tensor = transform(image).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                output = model(input_tensor)
                prob = output.item()
            
            is_fake = prob >= THRESHOLD
            label = "FAKE" if is_fake else "REAL"
            confidence = prob if is_fake else (1.0 - prob)
            
            if is_fake:
                fake_count += 1
                confidence_fake.append(prob)
            else:
                real_count += 1
                confidence_real.append(1.0 - prob)

            results.append({
                "filename": img_name,
                "probability": round(prob, 4),
                "classification": label,
                "confidence": round(confidence, 4)
            })

            # Print progress every 100 images
            if (idx + 1) % 100 == 0:
                print(f"  ✅ Processed {idx + 1}/{len(images)} images  |  Real: {real_count}  Fake: {fake_count}")

        except Exception as e:
            print(f"  ⚠️  Error on {img_name}: {e}")
            results.append({
                "filename": img_name,
                "probability": -1,
                "classification": "ERROR",
                "confidence": 0
            })

    # 5. Print Summary
    print("\n" + "=" * 65)
    print("📊 INFERENCE RESULTS SUMMARY")
    print("=" * 65)
    print(f"  🟢 Classified as REAL:  {real_count:>5} images ({real_count/len(images)*100:.1f}%)")
    print(f"  🔴 Classified as FAKE:  {fake_count:>5} images ({fake_count/len(images)*100:.1f}%)")
    print(f"  📏 Total:               {len(images):>5} images")
    
    if confidence_real:
        print(f"\n  🟢 Real Confidence:  avg={np.mean(confidence_real):.4f}  min={np.min(confidence_real):.4f}  max={np.max(confidence_real):.4f}")
    if confidence_fake:
        print(f"  🔴 Fake Confidence:  avg={np.mean(confidence_fake):.4f}  min={np.min(confidence_fake):.4f}  max={np.max(confidence_fake):.4f}")

    # Probability distribution
    probs = [r["probability"] for r in results if r["probability"] >= 0]
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    hist, _ = np.histogram(probs, bins=bins)
    
    print(f"\n  📈 Fake Probability Distribution:")
    for i in range(len(hist)):
        bar = "█" * (hist[i] // 5) if hist[i] > 0 else ""
        label = "REAL" if bins[i] < THRESHOLD else "FAKE"
        print(f"    {bins[i]:.1f}-{bins[i+1]:.1f}: {hist[i]:>4} {bar}  [{label}]")

    # 6. Split into dataset/real and dataset/fake
    print(f"\n{'=' * 65}")
    print("📂 SPLITTING INTO TRAINING DATASET")
    print("=" * 65)
    
    os.makedirs(REAL_DIR, exist_ok=True)
    os.makedirs(FAKE_DIR, exist_ok=True)
    
    copied_real = 0
    copied_fake = 0
    
    for r in results:
        if r["classification"] == "ERROR":
            continue
        
        src = os.path.join(BENCHMARK_DIR, r["filename"])
        
        if r["classification"] == "REAL":
            dst = os.path.join(REAL_DIR, f"ff_bench_{r['filename']}")
            shutil.copy2(src, dst)
            copied_real += 1
        else:
            dst = os.path.join(FAKE_DIR, f"ff_bench_{r['filename']}")
            shutil.copy2(src, dst)
            copied_fake += 1
    
    print(f"  ✅ Copied {copied_real} images → dataset/real/")
    print(f"  ✅ Copied {copied_fake} images → dataset/fake/")
    print(f"  📁 Total training images now available: {copied_real + copied_fake}")

    # 7. Save results to JSON for inspection
    results_path = "benchmark_inference_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "summary": {
                "total_images": len(images),
                "classified_real": real_count,
                "classified_fake": fake_count,
                "threshold": THRESHOLD,
                "device": str(DEVICE),
                "model": MODEL_PATH,
                "avg_confidence_real": round(float(np.mean(confidence_real)), 4) if confidence_real else 0,
                "avg_confidence_fake": round(float(np.mean(confidence_fake)), 4) if confidence_fake else 0,
            },
            "results": results
        }, f, indent=2)
    print(f"\n  💾 Full results saved to: {results_path}")

    # 8. Show 10 most confident Real and Fake
    sorted_by_prob = sorted([r for r in results if r["probability"] >= 0], key=lambda x: x["probability"])
    
    print(f"\n{'=' * 65}")
    print("🏆 TOP 10 MOST CONFIDENT PREDICTIONS")
    print("=" * 65)
    
    print("\n  🟢 Most Confident REAL (lowest fake probability):")
    for r in sorted_by_prob[:10]:
        print(f"    {r['filename']}  →  prob={r['probability']:.4f}  confidence={1-r['probability']:.1%}")
    
    print(f"\n  🔴 Most Confident FAKE (highest fake probability):")
    for r in sorted_by_prob[-10:]:
        print(f"    {r['filename']}  →  prob={r['probability']:.4f}  confidence={r['probability']:.1%}")

    print(f"\n{'=' * 65}")
    print("✅ ALL DONE!")
    print("=" * 65)
    print(f"\n💡 Next Steps:")
    print(f"   1. Review results in '{results_path}'")
    print(f"   2. Retrain with enriched dataset: python train_deepfake_detector.py")
    print(f"   3. For labeled data, fill out: https://docs.google.com/forms/d/e/1FAIpQLSdRRR3L5zAv6tQ_CKxmK4W96tAab_pfBu2EKAgQbeDVhmXagg/viewform")


if __name__ == "__main__":
    main()
