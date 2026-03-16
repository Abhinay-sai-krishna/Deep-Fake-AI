# Deep-Fake-AI

A comprehensive AI-powered platform for detecting deepfakes, synthetic media, and manipulated content across various formats (images, videos, and audio).

## Features
- **Image Analysis**: Detects AI-generated images vs. real human photos using Gemini AI and a fallback EfficientNet-B0 model.
- **Video Analysis**: Frame-by-frame CNN inference to identify manipulation, face swaps, and AI-generated video content.
- **Audio/Voice Analysis**: Voice clone and synthetic audio detection.
- **Social Media Deepfake Analysis**: Analyze links for deepfake content.
- **React Frontend**: A modern, interactive user interface built with Vite, React, and TailwindCSS to upload media and view the analysis results.
- **FastAPI Backend**: A high-performance Python backend handling file uploads, model inferences, and AI analysis.

## Project Structure
- `frontend/`: Contains the React + Vite frontend application.
- `backend/`: Contains the FastAPI server, PyTorch models (`deepfake_efficientnet_model.pth`), and inference/scraping logic.
- `README.md`: This documentation file.

## Step-by-Step Installation and Setup

### Prerequisites
- Node.js (v16+)
- Python 3.9+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Abhinay-sai-krishna/Deep-Fake-AI.git
cd Deep-Fake-AI
```

### 2. Backend Setup
Navigate into the backend directory:
```bash
cd backend
```
Create a virtual environment (optional but recommended):
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
```
Install the Python dependencies:
```bash
pip install -r requirements.txt
# Additionally, install standard ML libraries if not already: torch, torchvision, opencv-python, etc.
```
Run the FastAPI backend:
```bash
python main.py
# Or run with uvicorn directly:
# uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
The backend should now be running on `http://127.0.0.1:8000`.

### 3. Frontend Setup
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```
Install the Node.js dependencies:
```bash
npm install
```
Configure environment variables:
- Create a `.env` file in the `frontend` directory.
- Add your Firebase or Gemini keys if they are needed by the frontend.

Run the development server:
```bash
npm run dev
```
The frontend should now be running on `http://localhost:5173` (or the port specified by Vite).

## Usage
1. Open the frontend in your web browser.
2. Upload an image, video, or audio file, or provide a URL for analysis.
3. The platform will process the media and provide a confidence score detailing whether the content strictly authentic or AI-generated.

## How It Works
- **Frontend App**: Sends the media payload to the `/api/scan` endpoint.
- **FastAPI Core**: `main.py` processes the uploaded file.
- **Image Inference**: Uses a primary Gemini AI query for advanced context-aware detection, falling back to a locally trained PyTorch `EfficientNet-B0` architecture for robust visual artifact detection.
- **Video Processing**: Extracts frames using OpenCV and scores them through the neural network.

## License
MIT License
