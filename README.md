# 📽️ AI-Powered Handwritten Mathematical Video to Animated Lecture Generator

This project converts a **handwritten or teacher-recorded educational video** (e.g., a math lecture on paper) into a **clean, high-quality Manim animation**. It integrates Flask for uploading videos, Gemini (Google Generative AI) for content extraction, and Manim for animation rendering. It simulates intelligent scene understanding and automates visual generation of lecture-style animations.

---

## 🚀 Features

- 🎞️ Upload `.webm` or `.mp4` educational video clips
- 🤖 Extract slide-wise content using **LLM-based reasoning (Gemini 2.0)**
- 🧠 Supports **LaTeX**-based mathematical parsing
- 🎨 Converts detected content into a clean **Manim animation scene**
- 💻 Render and download the final `.mp4` video
- 🐳 Docker support for easy deployment
- 📡 Real-time processing with asynchronous background tasks

---

## 🧠 How It Works (Architecture Overview)

```text
User Uploads Handwritten Video
            |
            v
    Flask Upload Handler
            |
            v
   Background Worker Thread -----> script-code.py
            |                              |
            |                      [1] Upload video (simulated)
            |                      [2] Extract transcript (mocked)
            |                      [3] Call Gemini AI for parsing
            |                      [4] Generate JSON structure
            |                      [5] Write Manim code
            |                      [6] Render Manim animation
            v                              |
     Save to /media/videos       <--------/
            |
            v
  Display Result & Enable Download
````

---

## 🗂️ Project Structure

```
.
├── app.py                # Flask backend for video upload & processing
├── script-code.py        # Main processing pipeline using Gemini & Manim
├── generated_scene.py    # Auto-generated Manim code
├── requirements.txt      # All Python dependencies
├── dockerfile            # Docker configuration
├── uploads/              # Temporary storage for uploaded videos
├── media/videos/         # Final rendered output videos
├── templates/
│   ├── index.html        # Upload form
│   ├── processing.html   # Loading spinner page
│   └── result.html       # Result & download link
├── sample.webm           # Sample input video
└── .gitignore
```

---

## 🧪 Example

### Input

📹 `sample.webm`
A mock video simulating a teacher writing the following content:

```latex
The Fourier Transform decomposes a function  
into its frequency components.  
F(ω) = ∫_{-∞}^{∞} f(t) e^{-iωt} dt  
It is widely used in signal processing.
```

### Output

🎬 A clean Manim-rendered `.mp4` with animated slides and camera zooms.

---

## 🔧 Setup Instructions

### 📦 Python Virtual Environment

```bash
# Clone repository
git clone https://github.com/Ayush-mishra-0-0/ai-video-manim.git
cd ai-video-manim

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### ▶️ Run Flask Server

```bash
python app.py
```

Open your browser at: [http://localhost:10000](http://localhost:10000)

---

## 🐳 Docker Instructions (Optional)

```bash
# Build Docker image
docker build -t ai-video-manim .

# Run container
docker run -p 10000:10000 ai-video-manim
```

---

## 📜 API Flow Summary

| Endpoint         | Method   | Description                       |
| ---------------- | -------- | --------------------------------- |
| `/`              | GET/POST | Upload video & start processing   |
| `/processing`    | GET      | Show loading page while rendering |
| `/check_status`  | GET      | Polls to check if video is done   |
| `/result`        | GET      | View & download final animation   |
| `/download/<id>` | GET      | Download rendered `.mp4` video    |

---

## 📦 Key Python Packages

* `Flask` - web server and routing
* `subprocess` - to run Manim CLI
* `uuid` - unique upload tracking
* `google-generativeai` - Gemini API client
* `manim` - animation engine
* `PyTorch`, `NumPy`, `OpenAI Whisper`, etc. for future enhancements

Full list in `requirements.txt`

---

## ✨ AI Prompting Logic (Gemini)

```text
Prompt:
"This is a video of a teacher explaining mathematical concepts on sheets of paper. Your task is to extract and transcribe the exact content written on each sheet..."

Format:
<content>
    <slide1> ... </slide1>
    <slide2> ... </slide2>
    ...
</content>
```

---

## 📌 Limitations

* Gemini API is simulated (for now); real video OCR is mocked
* Works best with clean educational content and printed handwriting
* Manim rendering uses low-quality (-ql) to speed up preview

---

## 📥 Future Improvements

* Integrate OCR (e.g. Tesseract or Whisper) for real handwriting detection
* Add full Gemini support for auto JSON/scene generation
* Support voice-to-text narration syncing
* Add frontend progress bar with WebSocket

---

## 👤 Author

**Ayush Kumar Mishra**
[LinkedIn](https://www.linkedin.com/in/ayush-mishra-20b63b290) • [GitHub](https://github.com/Ayush-mishra-0-0)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🧠 Acknowledgements

* [Manim Community](https://www.manim.community/)
* [Google Gemini](https://ai.google.dev/)
* [Flask](https://flask.palletsprojects.com/)
