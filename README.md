# FFmpeg Agent 🎬

A simple web application that uses AI to generate and execute FFmpeg commands based on user prompts. Upload a media file, describe what you want to do, and let the AI handle the FFmpeg magic! ✨

## Features ✨

*   **AI-Powered FFmpeg:** Leverages the OpenRouter API (specifically DeepSeek model) to interpret natural language prompts and generate corresponding FFmpeg commands.
*   **Web Interface:** Simple HTML frontend for uploading files and entering prompts.
*   **Output Preview:** Displays the processed image or video directly in the browser.
*   **Download Link:** Provides a link to download the processed file.
*   **Unique Filenames:** Automatically generates unique, timestamped filenames for output to prevent overwrites.
*   **Web-Compatible Output:** Aims to produce web-friendly video formats (MP4 H.264/AAC) by default.

## Setup ⚙️

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/biswatma/ffmpeg-agent.git
    cd ffmpeg-agent
    ```
    *(Note: If you are setting this up locally without cloning, ensure all project files are in a directory named `ffmpeg-agent`)*

2.  **Install FFmpeg:** Ensure you have FFmpeg installed on your system and accessible from your command line. Installation methods vary by OS:
    *   **macOS (using Homebrew):** `brew install ffmpeg`
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`
    *   **Windows:** Download from the [official FFmpeg website](https://ffmpeg.org/download.html) and add it to your system's PATH.

3.  **Install Python Dependencies:** Navigate to the project directory (`ffmpeg-agent`) in your terminal and install the required packages (preferably within a virtual environment):
    ```bash
    # Optional: Create and activate a virtual environment
    # python3 -m venv .venv
    # source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

    pip install flask requests python-dotenv werkzeug
    ```

4.  **Set up API Key:**
    *   Create a file named `.env` in the `ffmpeg-agent` directory.
    *   Add your OpenRouter API key to this file:
        ```
        OPENROUTER_API_KEY='YOUR_OPENROUTER_API_KEY_HERE'
        ```
    *   Get your key from [OpenRouter.ai](https://openrouter.ai/).
    *   The `.gitignore` file is already configured to prevent this file from being committed to Git.

## Running the Server 🚀

1.  Open your terminal.
2.  Navigate to the `ffmpeg-agent` directory.
3.  (Optional) Activate your virtual environment if you created one (`source .venv/bin/activate`).
4.  Run the Flask server:
    ```bash
    python server.py
    ```
5.  The server will start, usually on `http://127.0.0.1:3002`.

## Usage 🖱️

1.  Open your web browser and go to `http://127.0.0.1:3002`.
2.  Select an image or video file using the file input.
3.  Describe the desired operation in the text area (e.g., "convert to mp4", "make grayscale", "resize to 100x100"). You can also use the sample command buttons.
4.  Click "Process Media".
5.  Wait for the processing to complete (indicated by the spinner stopping).
6.  The output preview will appear on the right, and a download link will become available.

Enjoy simplifying your FFmpeg tasks! 🎉
