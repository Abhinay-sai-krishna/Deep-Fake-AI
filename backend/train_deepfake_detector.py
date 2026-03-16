# pyre-ignore-all-errors
import os
import io
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset, WeightedRandomSampler, random_split
from torchvision import models, transforms
from PIL import Image
import numpy as np
import sys

# Force UTF-8 output on Windows (fixes encoding issues in PowerShell)
try:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# =====================================================================
# Deepfake Detector v2.1 - Fast Resume Training
# Model: EfficientNet-B0 (Transfer Learning)
# Task: Binary Classification (Real=0, Fake=1)
# Dataset: FaceForensics++ Benchmark Images
# =====================================================================

BATCH_SIZE    = 32
NUM_EPOCHS    = 8
LEARNING_RATE = 0.001
VAL_SPLIT     = 0.15
CHECKPOINT    = "deepfake_efficientnet_model.pth"
DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")

REAL_DIR = os.path.join("dataset", "real")
FAKE_DIR = os.path.join("dataset", "fake")


class FaceDataset(Dataset):
    def __init__(self, real_dir, fake_dir, transform=None):
        self.transform = transform
        self.data = []

        for p in os.listdir(real_dir):
            if p.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.data.append((os.path.join(real_dir, p), 0))
        for p in os.listdir(fake_dir):
            if p.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.data.append((os.path.join(fake_dir, p), 1))

        real_n = sum(1 for _, l in self.data if l == 0)
        fake_n = sum(1 for _, l in self.data if l == 1)
        print(f"  Real: {real_n}  |  Fake: {fake_n}  |  Total: {len(self.data)}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        path, label = self.data[i]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, torch.tensor(label, dtype=torch.float32)


def build_model():
    m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    for p in m.parameters():
        p.requires_grad = False
    # Unfreeze last feature block for face-specific learning
    for p in m.features[-1].parameters():
        p.requires_grad = True
    nf = m.classifier[1].in_features
    m.classifier[1] = nn.Sequential(
        nn.Linear(nf, 128),
        nn.ReLU(),
        nn.Dropout(0.4),
        nn.Linear(128, 1),
        nn.Sigmoid()
    )
    return m.to(DEVICE)


def train():
    print("=" * 55)
    print("Deepfake Detector - Training Pipeline v2.1")
    print(f"  Device : {DEVICE}")
    print(f"  Epochs : {NUM_EPOCHS}   Batch size : {BATCH_SIZE}")
    print("=" * 55)

    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Guard: ensure dataset directories are not empty
    if not os.path.isdir(REAL_DIR) or not os.path.isdir(FAKE_DIR):
        raise FileNotFoundError(
            f"Dataset directories not found.\n"
            f"Expected: {os.path.abspath(REAL_DIR)}  and  {os.path.abspath(FAKE_DIR)}\n"
            "Please populate them with .jpg/.png images before training."
        )

    print("\nLoading dataset...")
    # FIX: Use two separate dataset objects so that applying val_tf does NOT
    # overwrite the training transforms (random_split shares the same object).
    full_ds_for_split = FaceDataset(REAL_DIR, FAKE_DIR, transform=None)  # labels only
    n_val   = int(len(full_ds_for_split) * VAL_SPLIT)
    n_train = len(full_ds_for_split) - n_val
    train_indices, val_indices = random_split(
        range(len(full_ds_for_split)), [n_train, n_val],
        generator=torch.Generator().manual_seed(42)
    )
    train_indices = list(train_indices)
    val_indices   = list(val_indices)

    # Build independent datasets with correct transforms
    train_ds_full = FaceDataset(REAL_DIR, FAKE_DIR, transform=train_tf)
    val_ds_full   = FaceDataset(REAL_DIR, FAKE_DIR, transform=val_tf)
    train_ds = Subset(train_ds_full, train_indices)
    val_ds   = Subset(val_ds_full,   val_indices)
    print(f"  Train: {n_train}  |  Val: {n_val}")

    # Weighted sampler to fix class imbalance
    all_labels   = np.array([full_ds_for_split.data[i][1] for i in range(len(full_ds_for_split))])
    train_labels = all_labels[train_indices]
    n_real = max(int(np.sum(train_labels == 0)), 1)
    n_fake = max(int(np.sum(train_labels == 1)), 1)
    # FIX: convert to Python list to avoid WeightedRandomSampler dtype warning
    w = np.where(train_labels == 0, 1.0 / n_real, 1.0 / n_fake).tolist()
    sampler = WeightedRandomSampler(w, len(w), replacement=True)
    print(f"  Imbalance fix: real images boosted x{n_fake / n_real:.1f}\n")

    train_ld = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)
    val_ld   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,   num_workers=0)

    print("Building model...")
    model = build_model()

    if os.path.exists(CHECKPOINT):
        try:
            # FIX: weights_only=True silences the torch.load deprecation warning
            model.load_state_dict(torch.load(CHECKPOINT, map_location=DEVICE, weights_only=True))
            print(f"  [OK] Resumed from checkpoint: {CHECKPOINT}")
        except Exception as e:
            print(f"  [WARN] Checkpoint incompatible ({e}). Starting fresh.")
    else:
        print("  [INFO] No checkpoint found - starting fresh.")

    criterion = nn.BCELoss()
    optimizer = optim.Adam([
        {'params': model.features[-1].parameters(), 'lr': LEARNING_RATE * 0.1},
        {'params': model.classifier.parameters(),   'lr': LEARNING_RATE},
    ])
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.5)

    best_val_acc = 0.0
    print("\n{:^55}".format("--- Starting Training ---"))
    print(f"{'Epoch':<8} {'Train%':>7} {'Val%':>6} {'Real%':>7} {'Fake%':>7} {'Status':>8}")
    print("-" * 55)

    for epoch in range(NUM_EPOCHS):
        # Training
        model.train()
        t_loss, t_correct, t_total = 0.0, 0, 0
        for imgs, lbls in train_ld:
            imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE).unsqueeze(1)
            out  = model(imgs)
            loss = criterion(out, lbls)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            t_correct += ((out > 0.5).float() == lbls).sum().item()
            t_total   += lbls.size(0)
            t_loss    += loss.item()

        # Validation
        model.eval()
        v_correct, v_total = 0, 0
        real_ok, real_tot, fake_ok, fake_tot = 0, 0, 0, 0
        with torch.no_grad():
            for imgs, lbls in val_ld:
                imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE).unsqueeze(1)
                out  = model(imgs)
                pred = (out > 0.5).float()
                v_correct += (pred == lbls).sum().item()
                v_total   += lbls.size(0)
                real_ok   += (pred[lbls == 0] == 0).sum().item()
                real_tot  += (lbls == 0).sum().item()
                fake_ok   += (pred[lbls == 1] == 1).sum().item()
                fake_tot  += (lbls == 1).sum().item()

        scheduler.step()

        t_acc = t_correct / max(t_total, 1) * 100
        v_acc = v_correct / max(v_total, 1) * 100
        r_acc = real_ok   / max(real_tot, 1) * 100
        f_acc = fake_ok   / max(fake_tot, 1) * 100

        status = ""
        if v_acc > best_val_acc:
            best_val_acc = v_acc
            torch.save(model.state_dict(), CHECKPOINT)
            status = "SAVED"

        print(f"{epoch+1:02d}/{NUM_EPOCHS:<5} {t_acc:>7.1f} {v_acc:>6.1f} {r_acc:>7.1f} {f_acc:>7.1f} {status:>8}")

    print("=" * 55)
    print(f"DONE!  Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved -> {CHECKPOINT}")
    print("=" * 55)


if __name__ == "__main__":
    train()
