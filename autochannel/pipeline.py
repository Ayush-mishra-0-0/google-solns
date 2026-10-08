"""Autonomous math-video pipeline.

Topic discovery -> independent reference -> structured storyboard -> narrated
multi-layout Manim video -> media QA -> YouTube OAuth upload (optional).

Publishing is opt-in and private by default. Never commits secrets or videos.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from autochannel.research import rank_topics, research_reference

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
LAYOUTS = {"concept", "equation", "comparison", "graph", "timeline"}
CURVES = {"sin", "cos", "quadratic", "exponential", "normal"}
UNSAFE_LATEX = re.compile(
    r"\\(?:input|include|write|openin|openout|read|catcode|def|csname|usepackage|documentclass|directlua|special)\b",
    re.IGNORECASE,
)


def read_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    seeds = data.get("topic_seeds")
    channel = data.get("channel_id")
    if not isinstance(seeds, list) or not seeds or not all(isinstance(s, str) and s.strip() for s in seeds):
        raise ValueError("config needs non-empty topic_seeds")
    if not isinstance(channel, str) or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel):
        raise ValueError("config needs a YouTube channel_id beginning UC")
    return data


def validate_storyboard(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Story must be a JSON object")
    title = data.get("title")
    if not isinstance(title, str) or not 12 <= len(title.strip()) <= 95:
        raise ValueError("Video title must be between 12 and 95 characters")
    description = data.get("description")
    if not isinstance(description, str) or len(description.strip()) < 60:
        raise ValueError("Video needs an educational description")
    beats = data.get("beats")
    if not isinstance(beats, list) or not 5 <= len(beats) <= 12:
        raise ValueError("Storyboard needs 5-12 beats")
    layouts = set()
    for index, b in enumerate(beats):
        if not isinstance(b, dict) or b.get("layout") not in LAYOUTS:
            raise ValueError(f"Beat {index} has invalid layout")
        layouts.add(b["layout"])
        for name, low, high in (("heading", 3, 70), ("body", 10, 240),
                                ("narration", 60, 850)):
            value = b.get(name)
            if not isinstance(value, str) or not low <= len(value.strip()) <= high:
                raise ValueError(f"Beat {index} requires {name} ({low}-{high} characters)")
        if b["layout"] == "equation":
            equation = b.get("equation", "")
            if not isinstance(equation, str) or not equation or len(equation) > 400:
                raise ValueError(f"Beat {index} has missing/oversized equation")
            if UNSAFE_LATEX.search(equation):
                raise ValueError(f"Beat {index} contains unsafe LaTeX")
        elif b["layout"] == "comparison":
            if not all(isinstance(b.get(k), str) and 2 <= len(b[k]) <= 100
                       for k in ("left", "right")):
                raise ValueError(f"Beat {index} has invalid comparison")
        elif b["layout"] == "graph" and b.get("curve") not in CURVES:
            raise ValueError(f"Beat {index} has invalid curve")
        elif b["layout"] == "timeline":
            steps = b.get("steps")
            if (not isinstance(steps, list) or not 2 <= len(steps) <= 4
                    or not all(isinstance(s, str) and 2 <= len(s) <= 35 for s in steps)):
                raise ValueError(f"Beat {index} has invalid timeline")
    if len(layouts) < 3:
        raise ValueError("Rejecting visually repetitive plan: use at least three layouts")
    return data


def generate_storyboard(topic: str, reference: dict, signals: list[dict], model_name: str) -> dict:
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to generate a storyboard")
    client = genai.Client(api_key=api_key)
    signal_text = json.dumps([{"title": s["title"], "url": s["url"],
                               "views_per_day": s["views_per_day"]} for s in signals[:5]])
    prompt = f"""You are an outstanding educational mathematics/science video director.
Produce an ORIGINAL, accurate, engaging storyboard on: {topic}.
This is not a summary or remake of any existing video. Lead with a concrete
counterintuitive question. Build intuition, a worked example and a satisfying
ending. Script each narration as natural spoken English, not slide-reading.
Target 2-5 minutes, 6-10 beats, 3+ DISTINCT layout types, include at least
one explanatory diagram/graph/compare if sensible. Never fabricate evidence.
If a detail cannot be substantiated by the reference, avoid it.
The video must teach something substantive in every beat.

Independent factual research context (not automatically an authoritative
proof of every mathematical statement):
{json.dumps(reference, ensure_ascii=False)}

Current YouTube demand SIGNALS ONLY (do not copy their structures or wording):
{signal_text}

Return ONLY a JSON object with:
"title": compelling but truthful clickable title (12-95 chars);
"description": 2+ sentence educational summary (60+ chars);
"beats": list of 5-12 objects, each with
"heading" (3-70 chars), "body" (10-240 chars, on-screen teaching point),
"narration" (60-850 chars, spoken explanation),
"layout" one of "concept","equation","comparison","graph","timeline".
For "equation", add valid self-contained "equation" LaTeX (NO dollar signs).
For "comparison", add "left" and "right" short texts (2-100 chars).
For "graph", add "curve" from sin,cos,quadratic,exponential,normal.
For "timeline", add "steps" array of 2-4 short labels.
Mix layouts according to PEDAGOGY, not randomly. Any math must be correct.
Use ASCII-compatible plain text on-screen, Unicode narration is fine.
Do not use citations inside LaTeX. No trademarks, copying or unverifiable hype.
"""
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0.45},
    )
    if not response.text:
        raise RuntimeError("The storyboard model returned no text")
    return validate_storyboard(json.loads(response.text))


def execute(command: list[str], **kwargs) -> None:
    subprocess.run(command, check=True, **kwargs)


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def duration_seconds(path: Path) -> float:
    result = probe(path)
    duration = float(result.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise ValueError(f"No measurable media duration: {path}")
    return duration


def synthesize_audio(story: dict, workdir: Path) -> tuple[Path, list[float]]:
    from gtts import gTTS
    folder = workdir / "narration_parts"
    folder.mkdir(parents=True, exist_ok=True)
    paths, durations = [], []
    for index, beat in enumerate(story["beats"]):
        path = folder / f"{index:02}.mp3"
        last_error = None
        for attempt in range(3):
            try:
                gTTS(text=beat["narration"], lang="en", slow=False).save(str(path))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                time.sleep(2 ** attempt)
        if last_error:
            raise RuntimeError(f"Speech synthesis failed for beat {index}") from last_error
        paths.append(path)
        durations.append(duration_seconds(path) + 0.20)
    listing = folder / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in paths), encoding="utf-8")
    audio = workdir / "narration.wav"
    execute(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-ac", "2", "-ar", "44100", str(audio)])
    return audio, durations


def render(story: dict, workdir: Path) -> Path:
    audio, durations = synthesize_audio(story, workdir)
    scene_spec = workdir / "render_spec.json"
    scene_spec.write_text(json.dumps({**story, "durations": durations},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    env = {**os.environ, "AUTOCHANNEL_SPEC": str(scene_spec.resolve())}
    scene_file = Path(__file__).with_name("scene.py").resolve()
    manim_folder = workdir / "manim"
    execute([sys.executable, "-m", "manim", "-qh",
             "--media_dir", str(manim_folder), "-o", "visual.mp4",
             str(scene_file), "AutoChannelScene"], env=env)
    candidates = [p for p in manim_folder.rglob("visual.mp4")
                  if "partial_movie_files" not in str(p)]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one rendered Manim video, found {len(candidates)}")
    output = workdir / "final.mp4"
    execute(["ffmpeg", "-y", "-v", "error", "-i", str(candidates[0]), "-i", str(audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)])
    return output


def verify_video(path: Path, story: dict) -> dict:
    if not path.exists() or path.stat().st_size < 100_000:
        raise ValueError("Rendered video missing or suspiciously small")
    media = probe(path)
    streams = media.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    length = duration_seconds(path)
    if not video or int(video.get("width", 0)) < 1280 or int(video.get("height", 0)) < 720:
        raise ValueError("Video track missing or below 720p")
    if not audio:
        raise ValueError("Audio track missing")
    if not 30 <= length <= 900:
        raise ValueError(f"Suspicious length {length:.1f}s; review instead of uploading")
    if len(story["beats"]) < 5:
        raise ValueError("Storyboard is too shallow")
    return {"duration_seconds": round(length, 2), "width": video["width"],
            "height": video["height"], "audio_codec": audio.get("codec_name")}


def create_thumbnail(title: str, output: Path) -> None:
    """Simple custom thumbnail. No copyrighted images or AI stock imagery."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1280, 720), "#0B1120")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((45, 50, 1235, 670), radius=38,
                           outline="#22D3EE", width=8, fill="#17233C")
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font = ImageFont.truetype(font_path, size=88)
        small = ImageFont.truetype(font_path, size=34)
    except OSError:
        font = ImageFont.load_default()
        small = ImageFont.load_default()
    words, lines, line = title.split(), [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > 1060 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    if len(lines) > 3:
        lines = lines[:2] + [" ".join(lines[2:])[:34] + "..."]
    y = 260 - 57 * (len(lines) - 1)
    for line in lines:
        draw.text((110, y), line, font=font, fill="#F8FAFC")
        y += 110
    draw.text((110, 585), "VISUAL EXPLANATION", font=small, fill="#22D3EE")
    img.save(output)


def upload_to_youtube(path: Path, story: dict, reference: dict, channel_id: str,
                      privacy: str, token_path: Path) -> str:
    """OAuth belongs to the user. Refuse to upload to the wrong channel."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    b64 = os.environ.get("YOUTUBE_TOKEN_JSON_BASE64")
    if b64:
        creds = Credentials.from_authorized_user_info(
            json.loads(base64.b64decode(b64).decode("utf-8")), SCOPES)
    elif token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    elif os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE"):
        flow = InstalledAppFlow.from_client_secrets_file(
            os.environ["YOUTUBE_CLIENT_SECRETS_FILE"], SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        raise RuntimeError("OAuth not configured: supply YOUTUBE_CLIENT_SECRETS_FILE for first local login")

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds.valid:
        raise RuntimeError("No valid YouTube OAuth credentials; reconnect locally")
    if not b64:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        try:
            token_path.chmod(0o600)
        except OSError:
            pass

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    channels = youtube.channels().list(part="id", mine=True).execute().get("items", [])
    if channel_id not in [x.get("id") for x in channels]:
        raise RuntimeError("OAuth points to a different YouTube channel. Upload aborted.")
    body = {
        "snippet": {
            "title": story["title"], "categoryId": "27",
            "description": story["description"].strip() +
                "\n\nFurther reading:\n" + reference["url"] +
                "\n\nCreated with original script and animation.",
            "tags": ["math", "visual explanation", "education"],
            "defaultLanguage": "en",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    request = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), chunksize=8 * 1024 * 1024,
                                   resumable=True, mimetype="video/mp4"))
    response = None
    while response is None:
        _, response = request.next_chunk(num_retries=3)
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("YouTube returned no video ID")
    return video_id


def record_state(state_path: Path, data: dict):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    current = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else []
    current.append(data)
    temp = state_path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, indent=2), encoding="utf-8")
    temp.replace(state_path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("autochannel/settings.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--state", type=Path, default=Path("outputs/ledger.json"))
    parser.add_argument("--mode", choices=("plan", "render", "upload"), default="plan")
    parser.add_argument("--privacy", choices=("private", "unlisted", "public"), default="private")
    parser.add_argument("--topic", help="Optional manually selected topic for one run")
    args = parser.parse_args(argv)

    settings = read_config(args.config)
    selected = None
    if args.topic:
        selected = {"topic": args.topic, "signals": []}
    else:
        yt_key = os.environ.get("YOUTUBE_API_KEY")
        if not yt_key:
            raise RuntimeError("YOUTUBE_API_KEY is required for topic discovery")
        ranked = rank_topics(yt_key, settings["channel_id"], settings["topic_seeds"],
                             max_topics=len(settings["topic_seeds"]))
        recent = json.loads(args.state.read_text()) if args.state.exists() else []
        used = {entry.get("topic", "").lower() for entry in recent}
        selected = next((x for x in ranked if x["topic"].lower() not in used), None)
        if selected is None:
            raise RuntimeError("No new sufficiently researched topics; add new seeds")

    topic = selected["topic"]
    print(f"Selected topic: {topic}", flush=True)
    reference = research_reference(topic)
    story = generate_storyboard(topic, reference, selected["signals"],
                                settings.get("gemini_model", "gemini-2.5-flash"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = args.output_dir / f"{run_id}-{re.sub(r'[^a-z0-9]+', '-', topic.lower())[:45]}"
    workdir.mkdir(parents=True, exist_ok=False)
    (workdir / "storyboard.json").write_text(
        json.dumps({"topic": topic, "source": reference, **story}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    create_thumbnail(story["title"], workdir / "thumbnail.png")
    print(f"Storyboard: {workdir / 'storyboard.json'}", flush=True)

    if args.mode == "plan":
        return 0

    video = render(story, workdir)
    qa = verify_video(video, story)
    (workdir / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(f"Rendered & checked: {video} {qa}", flush=True)

    entry = {"topic": topic, "title": story["title"], "created_at": run_id,
             "artifact": str(video), "status": "rendered"}
    if args.mode == "upload":
        # Persist an ambiguous upload attempt before calling YouTube: an interrupted
        # upload should not be blindly retried, potentially duplicating a video.
        entry["status"] = "upload_attempted"
        record_state(args.state, entry)
        video_id = upload_to_youtube(
            video, story, reference, settings["channel_id"], args.privacy,
            Path(os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")))
        entry["status"], entry["video_id"] = "uploaded", video_id
        record_state(args.state, entry)
        print(f"Uploaded: https://youtu.be/{video_id} (requested {args.privacy})", flush=True)
    else:
        record_state(args.state, entry)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Autovideo stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
