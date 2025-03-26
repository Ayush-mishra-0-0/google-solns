#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
script-code.py

A script that:
  1. Uses Google Generative AI to process a local video file (e.g. sample.webm),
     extract transcriptions in an XML-like format,
  2. Extracts slide content from the transcription,
  3. Generates structured JSON (with "content" and "speak" fields) for a Manim scene,
  4. Optionally generates Manim scene code.
  
Usage:
    python3 script-code.py <video_file>
"""

import sys
import os
import time
import ast
import re
import subprocess

import numpy as np
from manim import *  # Ensure manim is installed

#############################################
# Section 1: Utility Functions
#############################################

def generate_manim_code(title, elements):
    """Generates Manim scene code based on a title and a list of elements."""
    code = f"""
from manim import *

class GeneratedScene(MovingCameraScene):
    def get_final_camera_setup(self):
        # Create all mobjects first
        title = Tex(r"{title}", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title
"""
    # Generate code for each element
    for idx, elem in enumerate(elements):
        elem_type = elem['type']
        content_lines = elem['content']
        content_args = ", ".join([f'r"{line}"' for line in content_lines])
        # Use Tex for 'tex' type and MathTex for math content
        class_name = "Tex" if elem_type == "tex" else "MathTex"
        font_size = 40 if elem_type == "tex" and idx < 2 else (36 if elem_type == "tex" else 40)
        code += f"""
        element{idx} = {class_name}({content_args}, font_size={font_size}).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element{idx})
        prev_mobject = element{idx}
"""
    code += """
        # Group all content elements
        content = VGroup(*content_elements)
        self.add(title)
        title.set_opacity(0)
        self.camera.auto_zoom([title], margin=1)
        current_content = [title]
        for element in content_elements[1:]:
            self.add(element)
            element.set_opacity(0)
            current_content.append(element)
        self.play(
            self.camera.auto_zoom(
                content,
                margin=0.5,
                animate=True
            ).build(),
            run_time=2
        )
        self.camera.frame.save_state()
        self.camera.auto_zoom(content, margin=0.5)
        final_frame_center = self.camera.frame.get_center()
        final_focal_width = self.camera.frame.get_width()
        self.camera.frame.restore()
        return final_frame_center, final_focal_width

    def construct(self):
        # Get the final camera settings from a silent run
        final_center, final_width = self.get_final_camera_setup()
        title = Tex(r"{title}", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title
"""
    for idx, elem in enumerate(elements):
        elem_type = elem['type']
        content_lines = elem['content']
        content_args = ", ".join([f'r"{line}"' for line in content_lines])
        class_name = "Tex" if elem_type == "tex" else "MathTex"
        font_size = 40 if elem_type == "tex" and idx < 2 else (36 if elem_type == "tex" else 40)
        code += f"""
        element{idx} = {class_name}({content_args}, font_size={font_size}).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element{idx})
        prev_mobject = element{idx}
"""
    code += """
        content = VGroup(*content_elements)
        self.camera.frame.move_to(final_center)
        self.camera.frame.set_width(final_width)
        self.play(Write(title))
        self.wait(1)
"""
    for idx in range(len(elements)):
        code += f"""
        self.play(Write(element{idx}))
        self.wait(1)
"""
    code += """
        self.wait(2)
"""
    return code

def convert_string_to_dict(input_str):
    """
    Converts a JSON-like string (with unquoted keys) into a Python dictionary.
    Expected format:
    {
      title : "Some Title",
      elements : [
          {"type": "tex", "content": ["..."], "speak": ["..."]},
          ...
      ]
    }
    Also escapes ampersands to prevent LaTeX errors.
    """
    cleaned_str = input_str.strip().strip('`').replace('json\n', '')
    parsed_dict = ast.literal_eval(cleaned_str)
    # Escape ampersands in all content and speak strings.
    for elem in parsed_dict["elements"]:
        elem["content"] = [item.replace("&", r"\&") for item in elem["content"]]
        elem["speak"] = [item.replace("&", r"\&") for item in elem["speak"]]
    return {
        "title": parsed_dict["title"],
        "elements": [
            {
                "type": elem["type"],
                "content": elem["content"],
                "speak": elem["speak"]
            }
            for elem in parsed_dict["elements"]
        ]
    }

def extract_slide_content(xml_string):
    """
    Extracts slide content from an XML-like string.
    For example, given:
        <content>
            <slide1>Text from slide 1</slide1>
            <slide2>Text from slide 2</slide2>
        </content>
    it returns a list like ["Text from slide 1", "Text from slide 2"].
    """
    pattern = re.compile(r'<slide\d+>(.*?)</slide\d+>', re.DOTALL)
    return pattern.findall(xml_string)

def download_audio(youtube_url, output_path="./"):
    """
    Downloads audio from a YouTube URL as an MP3 file using yt-dlp.
    """
    import yt_dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_audio': True,
        'audio_format': 'mp3',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s')
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

#############################################
# Section 2: Google Generative AI Integration
#############################################
# IMPORTANT: Ensure you have installed the official google-generativeai package:
#   pip install google-generativeai

import google.generativeai as genai
# from google import genai

# Configure the API key (there's no Client class in the new version)
API_KEY = "AIzaSyDNQ3uLiUTQVljD8Cj5vAAB1HLnk2FQnU4"
genai.configure(api_key=API_KEY)

# Import file functions; the current version uses upload_file.
from google.generativeai import files

#############################################
# Section 3: Video File Processing and Transcription
#############################################
def process_video(video_path):
    """
    Uploads a video file, waits for processing, and returns the file object.
    """
    print("Uploading file:", video_path)
    
    # Correct file upload method
    video_file = genai.upload_file(path=video_path)
    
    print(f"Completed upload: {video_file.uri}")
    print("File metadata:", video_file.video_metadata)
    
    # Wait for processing
    print("Waiting for processing", end='')
    while video_file.state.name == "PROCESSING":
        print('.', end='', flush=True)
        time.sleep(5)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name != "ACTIVE":
        raise ValueError(f"Video processing failed with state: {video_file.state.name}")
    
    print("\nFile processing completed successfully")
    return video_file

def transcribe_video(video_file):
    """
    Generates a transcription for the given video file using a Gemini model.
    """
    prompt2vid2text = '''This is a video of a teacher explaining mathematical concepts on sheets of paper. 
Your task is to extract and transcribe the exact content written on each sheet.
Guidelines:
- Use LaTeX for mathematical symbols.
- Do not add any extra explanation.
- Provide the output in the following XML-like format:
<content>
    <slide1>Extracted content from Slide 1</slide1>
    <slide2>Extracted content from Slide 2</slide2>
    <slide3>Extracted content from Slide 3</slide3>
    ...
</content>'''
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(contents=[video_file, prompt2vid2text])
    print("Transcription response:")
    print(response.text)
    return response.text

#############################################
# Section 4: Generate Structured JSON for Manim
#############################################
def generate_json_for_manim(slide_text):
    """
    Uses a Gemini model to produce JSON (with 'speak' field) for a Manim scene,
    based on slide text and a prompt.
    """
    prompt = """Write this in the given format only dont write anything else json format only
{
title : "Introduction to Fourier Transform"
elements : [
    {"type": "tex", "content": ["The Fourier Transform decomposes a function"], "speak":["The Fourier Transform decomposes a function."]},
    {"type": "tex", "content": ["into its frequency components."], "speak":["into its frequency components."]},
    {"type": "math", "content": [r"F(\\omega) = \\int_{-\\infty}^{\\infty} f(t) e^{-i\\omega t} dt"], "speak":["Explain the equation."]},
    {"type": "tex", "content": ["It is widely used in signal processing."], "speak":["It is widely used in signal processing."]}
]
}
RETURN your answer in the given format
{
  title: str,
  elements: list of dictionary(with keys type, content, and speak)
}
"""
    combined_input = slide_text + "  " + prompt + " "
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(contents=combined_input)
    print("JSON response:")
    print(response.text)
    result = convert_string_to_dict(response.text)
    return result

#############################################
# Section 5: Main Execution Flow
#############################################
def main():
    # Expect the local video file path as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python3 script-code.py <video_file>")
        sys.exit(1)
    video_path = sys.argv[1]
    
    # Process video and get transcription
    video_file = process_video(video_path)
    transcription_text = transcribe_video(video_file)
    
    # Extract slide content from transcription
    slides = extract_slide_content(transcription_text)
    print("Extracted slides:", slides)
    if len(slides) == 0:
        print("No slides extracted. Exiting.")
        sys.exit(1)
    
    # Use the second slide (if available) for generating JSON, otherwise the first slide.
    slide_for_json = slides[1] if len(slides) > 1 else slides[0]
    structured_result = generate_json_for_manim(slide_for_json)
    
    # Extract title and elements from the structured JSON
    title = structured_result["title"]
    elements = structured_result["elements"]
    for elem in elements:
        print("Content:", elem['content'])
        # Optionally print the speak field:
        # print("Speak:", elem['speak'])
    
    # (Optional) Generate Manim scene code and save to a file
    manim_code = generate_manim_code(title, elements)
    with open("generated_scene.py", "w") as f:
        f.write(manim_code)
    print("Manim scene code saved to generated_scene.py")
    
    # (Optional) Run the generated scene using subprocess (if desired)
    # Uncomment the following lines to render the scene:
    import subprocess
    import shutil
    subprocess.run(["python3", "-m", "manim", "-ql", "generated_scene.py", "GeneratedScene"], check=True)
    # After rendering the Manim scene
    manim_output_dir = os.path.join("media", "videos", "generated_scene", "480p15")
    generated_video_path = os.path.join(manim_output_dir, "GeneratedScene.mp4")
    destination_path = os.path.join("media", "videos", "GeneratedScene.mp4")

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    # Copy the generated video to the expected location
    if os.path.exists(generated_video_path):
        shutil.copy(generated_video_path, destination_path)
    else:
        print(f"Error: Generated video not found at {generated_video_path}")
    
if __name__ == '__main__':
    main()

#############################################
# Section 6: Download Audio from YouTube (Optional)
#############################################
def download_youtube_audio():
    youtube_link = "https://www.youtube.com/watch?v=nYVig7BfuEA"
    download_audio(youtube_link)
    print("Downloaded audio from YouTube.")

# Uncomment the following line if you wish to download YouTube audio:
# download_youtube_audio()
