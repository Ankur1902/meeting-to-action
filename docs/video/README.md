# Product video

`docs/demo.mp4` is recorded from the real UI and API, not a mockup:

- `stage.html`: a branded stage that frames the app (iframe) in a window and adds the camera (zoom/pan), cursor, click ripples, captions and intro/outro cards.
- `director.js`: a Playwright script that drives the app and the camera and captures frames through Chrome's screencast at half speed, then writes an ffmpeg concat list that restores real-time speed (smooth ~36 fps capture → 30 fps output).

To re-record:

```bash
make demo                      # offline demo API on :8000 (or the real API with GEMINI_API_KEY)
cd frontend && npm run build && npm start   # :3000
cd docs/video && python3 -m http.server 4000 &
node director.js
ffmpeg -f concat -safe 0 -i frames.txt -vf "fps=30,format=yuv420p" -c:v libx264 -crf 20 -preset slow -movflags +faststart ../demo.mp4
```
