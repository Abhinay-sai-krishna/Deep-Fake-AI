import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api/scan"

test_images = [
    {
        "name": "Test 1: Real Human Photo",
        "path": r"C:\Users\konda\.gemini\antigravity\brain\ec0d3dd8-1612-4a38-b4f3-3516647056b4\real_human_photo_1773465117661.png",
        "filename": "real_human_photo.png",
        "expected": "REAL"
    },
    {
        "name": "Test 2: AI Generated Face",
        "path": r"C:\Users\konda\.gemini\antigravity\brain\ec0d3dd8-1612-4a38-b4f3-3516647056b4\ai_generated_face_1773465133132.png",
        "filename": "ai_generated_face.png",
        "expected": "FAKE"
    },
    {
        "name": "Test 3: Ambiguous Portrait",
        "path": r"C:\Users\konda\.gemini\antigravity\brain\ec0d3dd8-1612-4a38-b4f3-3516647056b4\ambiguous_portrait_1773465151504.png",
        "filename": "portrait_photo.png",
        "expected": "AMBIGUOUS"
    }
]

output_lines = []

for test in test_images:
    output_lines.append("=" * 60)
    output_lines.append(test["name"])
    output_lines.append("Expected: " + test["expected"])
    
    try:
        with open(test["path"], "rb") as f:
            resp = requests.post(
                API_URL,
                files={"file": (test["filename"], f, "image/png")},
                data={"scan_type": "face"},
                timeout=60
            )
            r = resp.json()
            
            is_authentic = r.get("authentic", "N/A")
            ai_prob = r.get("details", {}).get("ai_probability", "N/A")
            human_prob = r.get("details", {}).get("human_probability", "N/A")
            manipulation = r.get("details", {}).get("manipulation_type", "N/A")
            model_used = r.get("details", {}).get("model_used", "N/A")
            raw_score = r.get("details", {}).get("raw_score", "N/A")
            confidence = r.get("confidence", "N/A")
            
            verdict = "REAL" if is_authentic else "FAKE"
            
            output_lines.append("RESULT: " + verdict)
            output_lines.append("  Authentic: " + str(is_authentic))
            output_lines.append("  AI Probability: " + str(ai_prob) + "%")
            output_lines.append("  Human Probability: " + str(human_prob) + "%")
            output_lines.append("  Confidence: " + str(confidence))
            output_lines.append("  Manipulation: " + str(manipulation))
            output_lines.append("  Model: " + str(model_used))
            output_lines.append("  Raw Score: " + str(raw_score))
            
            if test["expected"] == "REAL" and is_authentic:
                output_lines.append("  ACCURACY: PASS")
            elif test["expected"] == "FAKE" and not is_authentic:
                output_lines.append("  ACCURACY: PASS")
            elif test["expected"] == "AMBIGUOUS":
                output_lines.append("  ACCURACY: N/A (ambiguous)")
            else:
                output_lines.append("  ACCURACY: FAIL")
            
    except Exception as e:
        output_lines.append("ERROR: " + str(e))
    
    output_lines.append("")
    time.sleep(1)

output_lines.append("=" * 60)
output_lines.append("SUMMARY")
output_lines.append("=" * 60)

result_text = "\n".join(output_lines)
with open("test_results.txt", "w") as f:
    f.write(result_text)

print("Results written to test_results.txt")
