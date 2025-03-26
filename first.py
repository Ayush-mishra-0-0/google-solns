import os
import time
import ast
import re
import subprocess
import google.generativeai as genai

# Configure GenAI
API_KEY = "AIzaSyDNQ3uLiUTQVljD8Cj5vAAB1HLnk2FQnU4"
genai.configure(api_key=API_KEY)
# client= genai.Client()
# -------------------------------
# Step 1: Simulate Video Upload
# -------------------------------
class FakeVideoFile:
    def __init__(self, name):
        self.name = name
        self.uri = f"file://{os.path.abspath(name)}"
        # Simulate a READY state
        self.state = type('State', (), {'name': 'READY'})

def upload_video(video_path):
    print("Simulating video upload for", video_path)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file {video_path} not found.")
    return FakeVideoFile(video_path)

# -----------------------------------
# Step 2: Simulate Transcript Generation
# -----------------------------------
def generate_transcript(video_file):
    print("Simulating transcript generation for video:", video_file.name)
    transcript = """<content>
    <slide1>The Fourier Transform decomposes a function</slide1>
    <slide2>into its frequency components.</slide2>
    <slide3>F(\\omega) = \\int_{-\\infty}^{\\infty} f(t) e^{-i\\omega t} dt</slide3>
    <slide4>It is widely used in signal processing.</slide4>
    </content>"""
    return transcript

# -----------------------------------
# Step 3: Simulate JSON Generation from Slides
# -----------------------------------
prompt2vid2text='''This is a video of a teacher explaining mathematical concepts on sheets of paper. Your task is to extract and transcribe the exact content written on each sheet.

Guidelines:

The content may contain complex mathematical symbols, so use LaTeX for proper formatting.

The teacher's hand may partially obscure some parts of the text—do your best to infer but do not create your own content.

Strictly transcribe only what is written, without adding any additional explanations or assumptions.

Provide your response in the following structured format:

Ensure accuracy in transcription and formatting while maintaining the original structure of the content.

Response Format:

Structure the extracted content in the following XML-like format:

<content>
    <slide1>Extracted content from Slide 1</slide1>
    <slide2>Extracted content from Slide 2</slide2>
    <slide3>Extracted content from Slide 3</slide3>
    ...
</content>  '''

def generate_json_from_slides(slide_text):
    # In production, you might call:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[slide_text,prompt2vid2text ]
    )
    return response.text


# -----------------------------------
# NEW: Fix JSON-like string to valid JSON format
# -----------------------------------
def fix_json_string(json_str):
    # This regex adds quotes around keys (assuming keys are alphanumeric)
    fixed = re.sub(r'(?<=\{|,)\s*(\w+)\s*:', r'"\1":', json_str)
    return fixed

# -----------------------------------
# Updated: Convert JSON-like string to dictionary
# -----------------------------------
def convert_string_to_dict(input_str):
    # First, fix the JSON string so keys are quoted properly.
    fixed_str = fix_json_string(input_str)
    try:
        parsed_dict = ast.literal_eval(fixed_str)
    except Exception as e:
        raise ValueError(f"Error parsing JSON: {e}\nFixed string: {fixed_str}")
    return {
        "title": parsed_dict["title"],
        "elements": [
            {
                "type": elem["type"],
                "content": [item for item in elem["content"]],
                "speak": [item for item in elem["speak"]]
            }
            for elem in parsed_dict["elements"]
        ]
    }

# -----------------------------------
# Utility: Extract slide contents from transcript XML
# -----------------------------------
def extract_slide_content(xml_string):
    pattern = re.compile(r'<slide\d+>(.*?)</slide\d+>', re.DOTALL)
    return pattern.findall(xml_string)

# -----------------------------------
# Step 4: Generate Manim Scene Code
# -----------------------------------
def generate_manim_code(title, elements):
    code = f"""
from manim import *

class GeneratedScene(MovingCameraScene):
    def get_final_camera_setup(self):
        # Create all mobjects first
        title = Tex(r"{title}", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title
"""
    for idx, elem in enumerate(elements):
        elem_type = elem['type']
        content_lines = elem['content']
        content_args = ", ".join([f'r"{line}"' for line in content_lines])
        class_name = "Tex" if elem_type == "tex" else "MathTex"
        font_size = 40 if elem_type == "tex" and idx < 2 else 36 if elem_type == "tex" else 40
        code += f"""
        element{idx} = {class_name}({content_args}, font_size={font_size}).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element{idx})
        prev_mobject = element{idx}
"""
    code += """
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
        final_center, final_width = self.get_final_camera_setup()
        title = Tex(r"{title}", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title
""".format(title=title)
    for idx, elem in enumerate(elements):
        elem_type = elem['type']
        content_lines = elem['content']
        content_args = ", ".join([f'r"{line}"' for line in content_lines])
        class_name = "Tex" if elem_type == "tex" else "MathTex"
        font_size = 40 if elem_type == "tex" and idx < 2 else 36 if elem_type == "tex" else 40
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

# -----------------------------------
# Step 5: Main Processing Function
# -----------------------------------
def main():
    video_path = "sample.webm"
    
    video_file = upload_video(video_path)
    transcript_text = generate_transcript(video_file)
    print("Transcript generated:")
    print(transcript_text)
    
    json_text = generate_json_from_slides(transcript_text)
    print("Generated JSON content:")
    print(json_text)
    
    # Convert JSON text to a dictionary using the fixed JSON string
    result = convert_string_to_dict(json_text)
    title = result["title"]
    elements = result["elements"]
    
    manim_code = generate_manim_code(title, elements)
    manim_filename = "generated_scene.py"
    with open(manim_filename, "w", encoding="utf-8") as f:
        f.write(manim_code)
    print(f"Manim code written to {manim_filename}.")
    
    print("Generating animated video with Manim...")
    try:
        subprocess.run(["python", "-m", "manim", "-ql", manim_filename, "GeneratedScene"], check=True)
        print("Animated video generated successfully.")
    except subprocess.CalledProcessError as e:
        print("Error generating animated video:", e)

if __name__ == '__main__':
    main()
