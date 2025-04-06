import os
import subprocess
import uuid
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv
from datetime import datetime # Ensure datetime is imported

load_dotenv()

app = Flask(__name__, static_url_path='', static_folder='output')
app.config['OUTPUT_FOLDER'] = 'output'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("OpenRouter API key not found in environment variables.")

def generate_filename(filename):
    """
    Generate a unique filename to prevent conflicts.
    """
    ext = filename.rsplit('.', 1)[1].lower()
    unique_id = uuid.uuid4()
    return f"{unique_id}.{ext}"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_media():
    if 'mediaFile' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400

    file = request.files['mediaFile']
    prompt = request.form.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided.'}), 400

    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    print("File received:", file.filename)  # Add logging
    print("Prompt received:", prompt)  # Add logging

    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        unique_filename = generate_filename(filename)
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(input_filepath)

        # Define potential output filepath
        file_extension = os.path.splitext(filename)[1]
        base_filename = os.path.basename(filename).rsplit('.', 1)[0]
        potential_output_filename = f"{base_filename}-processed{file_extension}"
        potential_output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], potential_output_filename)

        # Construct AI prompt
        ai_prompt = f"""
        Based on the user's request, generate ONLY the FFmpeg command needed to process the input file. If the user asks to resize the image to a 2:2 aspect ratio, generate the following FFmpeg command: ffmpeg -i "{input_filepath}" -vf scale=2:2 "{potential_output_filepath}".
        Input file path: "{input_filepath}"
        User request: "{prompt}"
        Desired output file path: "{potential_output_filepath}"

        Constraints:
        - Provide ONLY the complete ffmpeg command, starting with "ffmpeg".
        - Do NOT include any explanations, comments, backticks (`), or markdown formatting.
        - Ensure the command correctly uses the provided input and output file paths.
        - **IMPORTANT**: If the output is a video, ensure it is in MP4 format with H.264 video codec (`-c:v libx264`) and AAC audio codec (`-c:a aac`) for web compatibility, unless the user explicitly requests a different format/codec. Adjust the output file extension to `.mp4` if necessary.
        - If the request seems impossible or unsafe with FFmpeg, respond with "ERROR: Cannot fulfill request".
        """

        # Call OpenRouter API
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://ffmpeg-agent.local',  # Required by OpenRouter
            'X-Title': 'FFmpeg Agent Tool'  # Required by OpenRouter
        }
        data = {
            'model': 'deepseek/deepseek-chat-v3-0324:free',  # Changed to DeepSeek model
            'messages': [{'role': 'user', 'content': ai_prompt}]
        }
        print("Calling OpenRouter API...")
        response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        ai_response = response.json()
        print("OpenRouter API response:", ai_response)
        ffmpeg_command = ai_response['choices'][0]['message']['content'].strip()

        if ffmpeg_command.startswith('ERROR:') or not ffmpeg_command.lower().startswith('ffmpeg'):
            os.remove(input_filepath)
            return jsonify({'error': f'AI could not generate a valid command: {ffmpeg_command}'}), 400

        # Adjust command to use absolute paths
        from datetime import datetime  # Ensure datetime is imported
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_output_filename = f"{timestamp}_{generate_filename(potential_output_filename)}"
        unique_output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], unique_output_filename)
        ffmpeg_command = ffmpeg_command.replace(f'"{potential_output_filepath}"', f'"{os.path.abspath(unique_output_filepath)}"')
        ffmpeg_command = ffmpeg_command.replace(f"'{potential_output_filepath}'", f"'{os.path.abspath(unique_output_filepath)}'")
        ffmpeg_command = ffmpeg_command.replace(f'"{input_filepath}"', f'"{os.path.abspath(input_filepath)}"')
        ffmpeg_command = ffmpeg_command.replace(f"'{input_filepath}'", f"'{os.path.abspath(input_filepath)}'")

        # Execute FFmpeg command
        print("Executing FFmpeg command:", ffmpeg_command)
        process = subprocess.Popen(ffmpeg_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        print("FFmpeg command executed.")

        # Clean up uploaded file
        os.remove(input_filepath)

        if process.returncode != 0:
            return jsonify({'error': 'FFmpeg command execution failed.', 'details': stderr.decode('utf-8')}), 500

        # Check if the unique output file exists (using the path passed to ffmpeg)
        if not os.path.exists(unique_output_filepath):
            print("Output file not found:", unique_output_filepath)
            error_details = stderr.decode('utf-8', errors='ignore') if stderr else "No stderr output."
            print(f"FFmpeg stderr: {error_details}")
            return jsonify({'error': 'FFmpeg command seemed to succeed, but the expected output file was not found.', 'details': error_details}), 500

        # Construct the URL based on the unique filename and static path config
        # Since static_url_path='', files in 'output' folder are served from root '/'
        output_url = f'/{os.path.basename(unique_output_filepath)}'
        print("Processing successful! Output URL:", output_url)
        return jsonify({'message': 'Processing successful!', 'outputUrl': output_url}), 200

    except requests.exceptions.RequestException as e:
        # Handle API errors
        if 'input_filepath' in locals() and os.path.exists(input_filepath): # Ensure input_filepath exists before removing
             os.remove(input_filepath)
        print(f"OpenRouter API Error: {str(e)}")
        print(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response'}")
        if isinstance(e, requests.exceptions.ConnectionError):
            return jsonify({'error': 'Failed to connect to OpenRouter API. Please check your internet connection.'}), 500
        elif isinstance(e, requests.exceptions.Timeout):
            return jsonify({'error': 'OpenRouter API request timed out. Please try again later.'}), 500
        else:
            return jsonify({
                'error': f'Failed to communicate with OpenRouter API: {str(e)}',
                'message': 'An error occurred while communicating with the OpenRouter API.',
                'details': e.response.text if hasattr(e, 'response') else None
            }), 500
    except Exception as e:
        # Handle other errors
        if 'input_filepath' in locals() and os.path.exists(input_filepath): # Ensure input_filepath exists before removing
             os.remove(input_filepath)
        print(f"Unexpected error: {str(e)}") # Added print for better debugging
        return jsonify({'error': f'An unexpected error occurred: {str(e)}', 'message': 'An unexpected error occurred.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3002)
