"""
🎥 FaceForensics++ Dataset Preprocessor
========================================
Extracts frames from FaceForensics++ videos and organizes them 
into the real/fake folder structure expected by train_deepfake_detector.py

Usage:
    python prepare_faceforensics.py \
        --ff_root "C:/path/to/FaceForensics++" \
        --output_dir "./dataset" \
        --frames_per_video 10 \
        --compression c23 \
        --methods Deepfakes Face2Face FaceSwap NeuralTextures

This will populate:
    ./dataset/real/   ← frames from original_sequences
    ./dataset/fake/   ← frames from manipulated_sequences
"""

import os
import argparse
import cv2
import numpy as np
from pathlib import Path


def extract_frames(video_path: str, output_dir: str, prefix: str, num_frames: int = 10):
    """
    Extract evenly-spaced frames from a single video file.
    
    Args:
        video_path: Path to the .mp4 video
        output_dir: Directory to save extracted frames
        prefix: Filename prefix (e.g., 'real_000' or 'deepfakes_000')
        num_frames: Number of frames to extract per video
    
    Returns:
        Number of frames successfully extracted
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ⚠️  Could not open: {video_path}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return 0

    # Calculate evenly-spaced frame indices
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    
    saved = 0
    for i, frame_idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            # Resize to 224x224 to match EfficientNet input size
            frame_resized = cv2.resize(frame, (224, 224))
            filename = f"{prefix}_frame{i:03d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame_resized)
            saved += 1

    cap.release()
    return saved


def process_original_videos(ff_root: str, output_dir: str, compression: str, 
                            frames_per_video: int):
    """Extract frames from original (real) videos."""
    real_dir = os.path.join(output_dir, "real")
    os.makedirs(real_dir, exist_ok=True)

    video_dir = os.path.join(ff_root, "original_sequences", "youtube", compression, "videos")
    
    if not os.path.exists(video_dir):
        print(f"❌ Original videos not found at: {video_dir}")
        print(f"   Make sure you downloaded with: python download_script.py <path> -d original -c {compression} -t videos")
        return 0

    videos = sorted([f for f in os.listdir(video_dir) if f.endswith('.mp4')])
    print(f"\n📂 Found {len(videos)} original (real) videos in {video_dir}")

    total_frames = 0
    for idx, video_name in enumerate(videos):
        video_path = os.path.join(video_dir, video_name)
        video_id = Path(video_name).stem
        prefix = f"real_{video_id}"
        
        saved = extract_frames(video_path, real_dir, prefix, frames_per_video)
        total_frames += saved

        if (idx + 1) % 100 == 0 or idx == len(videos) - 1:
            print(f"  ✅ Processed {idx + 1}/{len(videos)} real videos ({total_frames} frames total)")

    return total_frames


def process_manipulated_videos(ff_root: str, output_dir: str, compression: str,
                                methods: list, frames_per_video: int):
    """Extract frames from manipulated (fake) videos."""
    fake_dir = os.path.join(output_dir, "fake")
    os.makedirs(fake_dir, exist_ok=True)

    total_frames = 0
    
    for method in methods:
        video_dir = os.path.join(ff_root, "manipulated_sequences", method, compression, "videos")
        
        if not os.path.exists(video_dir):
            print(f"⚠️  Manipulated videos for '{method}' not found at: {video_dir}")
            print(f"   Download with: python download_script.py <path> -d {method} -c {compression} -t videos")
            continue

        videos = sorted([f for f in os.listdir(video_dir) if f.endswith('.mp4')])
        print(f"\n📂 Found {len(videos)} {method} (fake) videos in {video_dir}")

        method_frames = 0
        for idx, video_name in enumerate(videos):
            video_path = os.path.join(video_dir, video_name)
            video_id = Path(video_name).stem
            prefix = f"fake_{method.lower()}_{video_id}"
            
            saved = extract_frames(video_path, fake_dir, prefix, frames_per_video)
            method_frames += saved

            if (idx + 1) % 100 == 0 or idx == len(videos) - 1:
                print(f"  ✅ Processed {idx + 1}/{len(videos)} {method} videos ({method_frames} frames)")

        total_frames += method_frames
        print(f"  📊 {method} total: {method_frames} fake frames extracted")

    return total_frames


def main():
    parser = argparse.ArgumentParser(
        description="🎥 FaceForensics++ Frame Extractor for Deepfake Training Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with Deepfakes only
  python prepare_faceforensics.py --ff_root ./FF++ --output_dir ./dataset

  # All 4 methods, 15 frames per video, c23 compression  
  python prepare_faceforensics.py --ff_root ./FF++ --output_dir ./dataset \\
      --frames_per_video 15 --compression c23 \\
      --methods Deepfakes Face2Face FaceSwap NeuralTextures

  # Include FaceShifter as well
  python prepare_faceforensics.py --ff_root ./FF++ --output_dir ./dataset \\
      --methods Deepfakes Face2Face FaceSwap NeuralTextures FaceShifter
        """
    )
    
    parser.add_argument("--ff_root", type=str, required=True,
                        help="Root directory of the FaceForensics++ dataset")
    parser.add_argument("--output_dir", type=str, default="./dataset",
                        help="Output directory for extracted frames (default: ./dataset)")
    parser.add_argument("--frames_per_video", type=int, default=10,
                        help="Number of frames to extract per video (default: 10)")
    parser.add_argument("--compression", type=str, default="c23", choices=["raw", "c23", "c40"],
                        help="Compression level to use (default: c23)")
    parser.add_argument("--methods", nargs="+", 
                        default=["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"],
                        help="Manipulation methods to include (default: all 4 original methods)")
    parser.add_argument("--clear_existing", action="store_true",
                        help="Clear existing dataset/real and dataset/fake folders before extraction")

    args = parser.parse_args()

    print("=" * 60)
    print("🎥 FaceForensics++ Dataset Preprocessor")
    print("=" * 60)
    print(f"  📁 FF++ Root:         {args.ff_root}")
    print(f"  📁 Output Dir:        {args.output_dir}")
    print(f"  🖼️  Frames/Video:      {args.frames_per_video}")
    print(f"  📦 Compression:       {args.compression}")
    print(f"  🔧 Methods:           {', '.join(args.methods)}")
    print("=" * 60)

    if args.clear_existing:
        import shutil
        for subfolder in ["real", "fake"]:
            path = os.path.join(args.output_dir, subfolder)
            if os.path.exists(path):
                print(f"🗑️  Clearing {path}...")
                shutil.rmtree(path)

    # 1. Process Real Videos
    real_count = process_original_videos(
        args.ff_root, args.output_dir, args.compression, args.frames_per_video
    )

    # 2. Process Fake Videos (all selected methods)
    fake_count = process_manipulated_videos(
        args.ff_root, args.output_dir, args.compression, args.methods, args.frames_per_video
    )

    # Summary
    print("\n" + "=" * 60)
    print("📊 EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"  ✅ Real frames:  {real_count:,}")
    print(f"  ✅ Fake frames:  {fake_count:,}")
    print(f"  📁 Total:        {real_count + fake_count:,}")
    print(f"\n  🗂️  Real saved to: {os.path.join(args.output_dir, 'real')}")
    print(f"  🗂️  Fake saved to: {os.path.join(args.output_dir, 'fake')}")
    print(f"\n💡 Now run: python train_deepfake_detector.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
