console.log("Starting server.js..."); // Added logging
require('dotenv').config();
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 3002; // You can change this port if needed

// --- Configuration ---
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const UPLOAD_DIR = 'uploads';
const OUTPUT_DIR = 'output'; // Directory to store processed files

// Create output directory if it doesn't exist
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR);
}

// --- Multer Setup for File Uploads ---
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, UPLOAD_DIR);
    },
    filename: function (req, file, cb) {
        // Keep original filename but add timestamp to avoid conflicts
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, uniqueSuffix + '-' + file.originalname);
    }
});
const upload = multer({ storage: storage });

// --- Middleware ---
app.use(express.json()); // For parsing application/json
app.use(express.urlencoded({ extended: true })); // For parsing application/x-www-form-urlencoded
app.use(express.static(__dirname)); // Serve static files (like index.html) from the root directory
app.use('/output', express.static(path.join(__dirname, OUTPUT_DIR))); // Serve processed files

// --- API Endpoint ---
app.post('/process', upload.single('mediaFile'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded.' });
    }
    if (!req.body.prompt) {
        return res.status(400).json({ error: 'No prompt provided.' });
    }
    if (!OPENROUTER_API_KEY || OPENROUTER_API_KEY === 'YOUR_OPENROUTER_API_KEY') {
         // Clean up uploaded file if API key is missing
        fs.unlinkSync(req.file.path);
        return res.status(500).json({ error: 'OpenRouter API key not configured in .env file.' });
    }

    const inputFile = req.file.path;
    const prompt = req.body.prompt;
    const originalFilename = req.file.originalname;
    const fileExtension = path.extname(originalFilename);
    const baseFilename = path.basename(originalFilename, fileExtension);
    // Define a potential output filename (the AI might suggest a different one)
    const potentialOutputFile = path.join(OUTPUT_DIR, `${baseFilename}-processed${fileExtension}`);

    console.log(`Received file: ${inputFile}, Prompt: "${prompt}"`);

    try {
        // 1. Call OpenRouter/Gemini to get the FFmpeg command
        console.log('Asking AI for FFmpeg command...');
        const aiPrompt = `
Based on the user's request, generate ONLY the FFmpeg command needed to process the input file.
Input file path: "${inputFile}"
User request: "${prompt}"
Desired output file path: "${potentialOutputFile}"

Constraints:
- Provide ONLY the complete ffmpeg command, starting with "ffmpeg".
- Do NOT include any explanations, comments, backticks (\`), or markdown formatting.
- Ensure the command correctly uses the provided input and output file paths. If the user asks for a format change, adjust the output file extension accordingly.
- If the request seems impossible or unsafe with FFmpeg, respond with "ERROR: Cannot fulfill request".
`;

        const response = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
            model: 'google/gemini-pro-1.5', // Using Gemini Pro 1.5 as requested (adjust if needed)
            messages: [{ role: 'user', content: aiPrompt }],
            // Add other parameters like temperature if needed
        }, {
            headers: {
                'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        let ffmpegCommand = response.data.choices[0].message.content.trim();
        console.log(`AI suggested command: ${ffmpegCommand}`);

        if (ffmpegCommand.startsWith('ERROR:') || !ffmpegCommand.toLowerCase().startsWith('ffmpeg')) {
             // Clean up uploaded file
            fs.unlinkSync(inputFile);
            return res.status(400).json({ error: `AI could not generate a valid command: ${ffmpegCommand}` });
        }

        // Ensure the output path in the command uses the OUTPUT_DIR
        // This is a basic replacement, might need refinement depending on AI output variability
        ffmpegCommand = ffmpegCommand.replace(`"${potentialOutputFile}"`, `"${path.join(__dirname, potentialOutputFile)}"`);
        ffmpegCommand = ffmpegCommand.replace(`'${potentialOutputFile}'`, `'${path.join(__dirname, potentialOutputFile)}'`);
         // Also replace input path just in case AI didn't use the absolute one provided
        ffmpegCommand = ffmpegCommand.replace(`"${inputFile}"`, `"${path.join(__dirname, inputFile)}"`);
        ffmpegCommand = ffmpegCommand.replace(`'${inputFile}'`, `'${path.join(__dirname, inputFile)}'`);


        // 2. Execute the FFmpeg command
        console.log(`Executing: ${ffmpegCommand}`);
        exec(ffmpegCommand, (error, stdout, stderr) => {
            // Clean up the original uploaded file regardless of success/failure
            fs.unlink(inputFile, (err) => {
                if (err) console.error(`Error deleting uploaded file ${inputFile}:`, err);
            });

            if (error) {
                console.error(`FFmpeg execution error: ${error.message}`);
                console.error(`FFmpeg stderr: ${stderr}`);
                return res.status(500).json({
                    error: 'FFmpeg command execution failed.',
                    details: stderr || error.message
                });
            }

            console.log(`FFmpeg stdout: ${stdout}`);
            console.log(`FFmpeg stderr: ${stderr}`); // Log stderr even on success, might contain warnings

            // Determine the actual output file path from the command (more robust)
            // This regex tries to find the last argument that looks like a file path within OUTPUT_DIR
            const outputFilePathMatch = ffmpegCommand.match(/["']?(\.\/|output\/|\/.*?\/output\/)([^"'\s]+)["']?\s*$/i);
            let finalOutputFile = potentialOutputFile; // Default
             if (outputFilePathMatch && outputFilePathMatch[2]) {
                 // Construct the path relative to the server's root for the client URL
                 finalOutputFile = path.join(OUTPUT_DIR, path.basename(outputFilePathMatch[2]));
                 console.log("Detected output file:", finalOutputFile);
             } else {
                 console.warn("Could not reliably detect output file path from command, using default:", potentialOutputFile);
                 // Check if the default potential output file exists
                 if (!fs.existsSync(potentialOutputFile)) {
                     return res.status(500).json({ error: 'FFmpeg command seemed to succeed, but the expected output file was not found.' });
                 }
             }

            // Send back the path to the processed file
            res.json({
                message: 'Processing successful!',
                outputUrl: `/${finalOutputFile}` // URL relative to the server root
            });
        });

    } catch (error) {
        // Clean up uploaded file on error
        fs.unlinkSync(inputFile);

        console.error('Error during processing:', error);
        if (axios.isAxiosError(error)) {
            console.error('Axios error details:', error.response?.data);
             res.status(500).json({ error: 'Failed to communicate with OpenRouter API.', details: error.response?.data });
        } else {
             res.status(500).json({ error: 'An unexpected error occurred.', details: error.message });
        }
    }
});

// --- Start Server ---
app.listen(port, () => {
    console.log(`FFmpeg Agent server listening at http://localhost:${port}`);
});
