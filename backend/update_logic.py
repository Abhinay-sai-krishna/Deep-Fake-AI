import os, re

# Update scraping_agent.py
scraping_path = r'c:\Users\konda\OneDrive\Desktop\cybersecurity\backend\scraping_agent.py'
with open(scraping_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Instead of regex copying which might break, we can just append a def that calls analyze_url and transforms the output!
# This is much cleaner and doesn't duplicate the 150 lines of yt-dlp scraping code.
append_code = """
def analyze_social_deepfake_url(url: str):
    # Call the base logic which already extracted all AI probability accurately
    res = analyze_url(url)
    
    # Override the "Fake Platform" vs "Verified Platform" logic with Deepfake Media logic
    # using the underlying raw probabilities calculated
    
    base_ai_prob = float(res['ai_generated_probability'].replace('%', '')) / 100.0
    
    if base_ai_prob > 0.6:
        res["status"] = "danger"
        res["message"] = f"High Risk - AI Generated {res.get('media_target_type', 'Media').replace('Verified Platform', 'Media').replace('Fake Platform', 'Media')} Found"
        res["final_result"] = f"AI Generated Media"
    else:
        res["status"] = "safe"
        res["message"] = f"Verified Safe - Authentic Human Media"
        res["final_result"] = f"Real Human Media"
        
    # Correct media type and active model
    # We still have the active model, but we need to infer the original media type (Video vs Image)
    # The active model is XceptionNet for Video, EfficientNet for Image.
    original_media = "Video" if res["active_model"] == "XceptionNet" else "Image"
    
    res["media_target_type"] = original_media
    if base_ai_prob > 0.6:
        res["final_result"] = f"AI Generated {original_media}"
    else:
        res["final_result"] = f"Real Human {original_media}"
        
    # Tweak AI Suggestion for Social Media Content vs Platforms
    if base_ai_prob > 0.6:
        res["ai_suggestion"] = f"⚠️ AI Agent Warning: The {original_media} contained in this link is highly likely to be AI Generated (Deepfake). Please be extremely cautious and do not trust its authenticity."
    else:
        res["ai_suggestion"] = f"✅ AI Agent Verified: The {original_media} contained in this link appears to be authentic Real Human content. No significant synthetic generation traces were detected."

    return res
"""

if "def analyze_social_deepfake_url" not in code:
    with open(scraping_path, 'a', encoding='utf-8') as f:
        f.write(append_code)
    print("Added analyze_social_deepfake_url to scraping_agent.py")

# Update main.py
main_path = r'c:\Users\konda\OneDrive\Desktop\cybersecurity\backend\main.py'
with open(main_path, 'r', encoding='utf-8') as f:
    main_code = f.read()

if "/api/analyze-social-deepfake" not in main_code:
    route_code = """
@app.post("/api/analyze-social-deepfake")
async def analyze_social_media_deepfake(req: LinkRequest):
    return scraping_agent.analyze_social_deepfake_url(req.url)
"""
    # insert before @app.post("/api/scan")
    main_code = main_code.replace('@app.post("/api/scan")', route_code + '\n@app.post("/api/scan")')
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_code)
    print("Added /api/analyze-social-deepfake to main.py")
