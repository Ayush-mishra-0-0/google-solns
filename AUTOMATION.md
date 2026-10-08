# Autonomous educational YouTube pipeline (experimental)

This folder extends the original handwritten-lecture converter **without replacing it**.
It is a separate, declarative video workflow for the channel configured in
[settings.json](autochannel/settings.json). The original Flask/Manim application
still exists. Do not merge or enable scheduled public posting before completing
the acceptance checklist below.

## Flow

1. **Research demand:** YouTube Data API searches for recent videos in each configured
   educational topic, estimates view velocity, and penalizes similarity to recent
   public uploads from our own channel. Competitor video data is a **signal of
   audience demand only**, not a script or a source of mathematical facts.
2. **Research reference:** Retrieve an independent encyclopedia introduction
   (including its URL). Stop if the reference is unavailable.
3. **Plan:** Gemini produces a structured, original storyboard containing 5-12
   narrated beats. Storyboards are validated and must use 3+ different layouts.
4. **Render:** Generate per-beat speech, render Manim's predefined layouts,
   synchronize narration with animation, mux MP4 using ffmpeg, and create a
   custom image thumbnail. The model NEVER generates arbitrary executable code.
5. **Review gate:** Require readable 720p+ video, an audio track, plausible
   duration and content bounds. Store the storyboard/reference and QA results.
6. **Publish:** Optionally upload the result to the **specific** configured YouTube
   channel using OAuth, set metadata and thumbnail. Default privacy is PRIVATE.
   Record upload attempts before calling YouTube to discourage blind retries.

A deterministic video/metadata check is **not** a complete accuracy or originality
review. Mathematical derivations, narration timing, visual readability, and the
reference quality still need human acceptance before enabling unattended public
publishing. The channel's current audience/analytics were not accessible during
initial implementation, so topic seeds are starting assumptions, not validated
growth recommendations.

## Security: do this before using it

The existing public repository previously exposed **at least two distinct**
Gemini API keys in multiple files. They were removed from the new branch's latest
file versions, but may remain in git history, other clones, and prior commits.
**REVOKE BOTH OLD KEYS IN GOOGLE CLOUD AND CREATE NEW KEYS.** Never assume
moving them to environment variables retroactively protects them. A history
rewrite may reduce incidental exposure but cannot reverse a compromise.

Do not commit or paste an API key, OAuth client secret, token JSON, or personal
Google login password. The new .gitignore excludes local credentials, generated
audio/video, and temporary state.

## Local setup

Requirements: Python 3.11, ffmpeg/ffprobe, Cairo/Pango, Manim Community, a LaTeX
installation (TeX Live). Manim rendering can be CPU-intensive. On Linux:

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r autochannel/requirements.txt
python -m unittest discover -s autochannel/tests -v

# Put values in the shell or your secret manager, NEVER in source control.
export GEMINI_API_KEY="<your new Gemini key>"
export YOUTUBE_API_KEY="<your separate YouTube Data API key>"

# Research + storyboard + thumbnail (does not render or upload)
python -m autochannel.pipeline --mode plan

# Research + video + media QA, does not upload
python -m autochannel.pipeline --mode render
~~~

On Windows use PowerShell environment variables and a Manim installation that
supports ffmpeg, Pango, LaTeX and compiler dependencies. Run commands from the
repository root using python -m.

The pipeline uses Wikipedia's API for basic sourced context and YouTube's Data
API for topic demand. Both require network connectivity. The Gemini API has
usage limits; speech synthesis uses gTTS, an external online service. Generation
can fail closed if quotas, services, or Manim rendering are unavailable.

## One-time authorization for your YouTube channel

1. Open [Google Cloud Console](https://console.cloud.google.com/) and enable
   **YouTube Data API v3**. Create a separate restricted key for public
   research requests. Keep it as YOUTUBE_API_KEY.
2. Create an **OAuth Client ID** of type *Desktop application*. Download the
   credential JSON into a local file such as client_secret.json (ignored by git).
   Add yourself as a test user if the OAuth consent screen is in testing mode.
3. From the repository root, run:

~~~bash
export YOUTUBE_CLIENT_SECRETS_FILE="$PWD/client_secret.json"
python -m autochannel.pipeline --mode upload --privacy private
~~~

The first run opens Google authorization in your local browser and stores an
OAuth refreshable token in youtube_token.json (ignored by git). **Choose the
correct YouTube/Brand channel during consent.** The code verifies that the OAuth
channel ID matches settings.json and refuses to upload elsewhere.

After that, unattended runs can use the existing token. For GitHub Actions,
encode youtube_token.json locally and paste the output into a GitHub Actions
**encrypted repository secret** named YOUTUBE_TOKEN_JSON_BASE64:

~~~bash
python -c "import base64,pathlib;print(base64.b64encode(pathlib.Path('youtube_token.json').read_bytes()).decode())"
~~~

Keep the original local file protected. OAuth testing-mode refresh tokens can
expire; reconnect and update the encrypted secret when needed.

**Important YouTube platform restriction:** uploads from unverified API
projects created after July 28, 2020 may be forced to private visibility until
the API project passes YouTube's compliance audit, even if 'public' is requested.
See https://developers.google.com/youtube/v3/docs/videos/insert . Never bypass
this restriction with browser automation or account-sharing tricks.

## GitHub Actions scheduling

The .github/workflows/autochannel.yml file has an optional manual trigger
and a scheduled run twice weekly. Scheduled workflows become active only after
the workflow is on the repository's default branch.

Configure encrypted repository secrets:
- GEMINI_API_KEY
- YOUTUBE_API_KEY
- YOUTUBE_TOKEN_JSON_BASE64 (needed only for upload mode)

Configure repository **variables**:
- AUTOCHANNEL_MODE = plan (safe default), render, or upload
- AUTOCHANNEL_PRIVACY = private (safe default), unlisted, or public

**Start with AUTOCHANNEL_MODE=plan**, then test render, then upload privately.
Do not set automatic public mode until content quality, permissions, disclosure,
and upload compliance are verified.

For unattended runs, generated artifacts are attached to the workflow run for
7 days. A small topic/upload ledger is committed back to the repository after a
run (including interrupted upload attempts); the video files themselves are
NEVER committed. The ledger avoids reselecting topics on the next run. If
someone edits the ledger manually, repeat suppression becomes unreliable.

## What is implemented vs still needed

Implemented on the feature branch (subject to testing):
- Public YouTube demand scan, channel duplicate check, topic ranking
- Source-backed context lookup and constrained Gemini storyboard
- Five distinct Manim layouts: concept, equation, graph, comparison, timeline
- Per-beat gTTS voice with approximate beat-to-audio duration sync
- MP4 media checks, simple PNG thumbnail, YouTube OAuth upload integration
- Optional GitHub schedule, with safe defaults and a persistent run ledger

Not yet demonstrated:
- A complete real local/hosted render with genuine credentials
- Successful OAuth upload to your channel or API audit/public posting ability
- Accurate word-level subtitles, music mixing, studio-quality narration
- Real mathematical proof checking or frame-by-frame visual QC
- Sophisticated hand-designed diagrams, programmatic 3D visualizations,
  B-roll/license-aware asset sourcing, retention-driven optimization
- A/B title/thumbnail testing and YouTube Analytics feedback

The old original_code.py includes notebook-era code that is not a valid
standalone script. It was only sanitized, not adopted as an execution path.
Use python -m autochannel.pipeline instead.

## Acceptance checklist before unattended public publishing

- [ ] Revoke the two historically exposed keys
- [ ] Unit tests green on GitHub
- [ ] Run pipeline once with real Google credentials (plan)
- [ ] Visually inspect a complete high-quality rendered video (render)
- [ ] Check derivations, layout clipping, audio levels, timing and claims
- [ ] Confirm chosen OAuth account/channel and private YouTube upload
- [ ] Verify the uploaded custom thumbnail and video metadata
- [ ] Confirm privacy, quota, compliance audit and applicable AI disclosures
- [ ] Run two unattended executions without duplicates or token leaks
- [ ] Enable public scheduling only after measured success

## Official resources

- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/docs/thumbnails/set
- https://developers.google.com/youtube/v3/guides/auth/installed-apps
- https://support.google.com/youtube/answer/1311392
