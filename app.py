from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import uuid
import os
import subprocess
from threading import Thread
import time
import sys

import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  

app = Flask(__name__)
# app.secret_key = 'your-secret-key-here'

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'media/videos'
ALLOWED_EXTENSIONS = {'webm', 'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_video(upload_id):
    try:
        input_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], f'{upload_id}.webm'))
        output_path = os.path.abspath(os.path.join(app.config['PROCESSED_FOLDER'], f'{upload_id}.mp4'))
        
        # Run script with explicit Python executable
        process = subprocess.Popen(
            [sys.executable, 'script-code.py', input_path],  # Use sys.executable
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.getcwd()  # Set working directory explicitly
        )
        
        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[PROCESSING LOG] {output.strip()}")
        
        # Add explicit completion check
        if process.returncode == 0:
            print("Processing completed successfully")
            generated_path = os.path.abspath(os.path.join('media', 'videos', 'GeneratedScene.mp4'))
            if os.path.exists(generated_path):
                os.rename(generated_path, output_path)
                return True
        return False
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video' not in request.files:
            return redirect(request.url)
        file = request.files['video']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            upload_id = str(uuid.uuid4())
            filename = f'{upload_id}.webm'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            session['upload_id'] = upload_id
            session['processing'] = True
            
            thread = Thread(target=process_video, args=(upload_id,))
            thread.start()
            
            return redirect(url_for('processing'))
    return render_template('index.html')

@app.route('/processing')
def processing():
    return render_template('processing.html')

@app.route('/check_status')
def check_status():
    upload_id = session.get('upload_id')
    if upload_id:
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], f'{upload_id}.mp4')
        if os.path.exists(output_path):
            session['processing'] = False
            return {'status': 'complete'}
    return {'status': 'processing'}

@app.route('/result')
def result():
    upload_id = session.get('upload_id')
    if not upload_id:
        return redirect(url_for('index'))
    return render_template('result.html', video_id=upload_id)

@app.route('/download/<video_id>')
def download(video_id):
    return send_from_directory(
        app.config['PROCESSED_FOLDER'],
        f'{video_id}.mp4',
        as_attachment=True
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
