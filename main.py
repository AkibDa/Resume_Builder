#!/usr/bin/env python3
"""
Resume Builder Web Application using Groq API
This web application allows users to input their resume and job description
and generates a customized resume tailored to the job posting using the Groq API.
"""

import os
import datetime
import logging
import json
import magic
import traceback
from typing import Optional, Tuple
from pathlib import Path
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file
from groq import Groq
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf'}

# Constants
MODEL_NAME = "llama-3.3-70b-versatile"
OUTPUT_DIR = "output"
MAX_TOKENS = 1024

def setup_environment() -> None:
    """Load environment variables and create necessary directories."""
    try:
        load_dotenv()
        if not os.getenv('GROQ_API_KEY'):
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        # Create necessary directories
        Path(OUTPUT_DIR).mkdir(exist_ok=True)
        Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
        logger.info("Environment setup completed successfully")
    except Exception as e:
        logger.error(f"Environment setup failed: {str(e)}")
        raise

def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        logger.info(f"Successfully extracted text from PDF: {pdf_path}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def create_pdf_from_text(text: str, output_path: str) -> None:
    """
    Create a PDF file from text content.
    
    Args:
        text (str): Text content to write to PDF
        output_path (str): Path where to save the PDF
    """
    try:
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Set font and size
        c.setFont("Helvetica", 12)
        
        # Split text into lines and write to PDF
        lines = text.split('\n')
        y = height - 50  # Start 50 points from top
        
        for line in lines:
            if y < 50:  # If we're near the bottom, start a new page
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            
            c.drawString(50, y, line)
            y -= 15  # Move down 15 points for next line
        
        c.save()
        logger.info(f"Successfully created PDF at: {output_path}")
    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def generate_custom_resume(resume: str, job_description: str) -> Optional[str]:
    """
    Generate a customized resume using the Groq API.
    
    Args:
        resume (str): The original resume text
        job_description (str): The job description text
        
    Returns:
        Optional[str]: The generated resume or None if there's an error
    """
    try:
        # Initialize Groq client
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        
        # Prepare the prompt
        prompt = f"Build a custom resume for this job posting here is the resume: {resume} and here is the job description: {job_description}"
        
        # Generate completion
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "Please provide the job posting details, and I'll create a resume tailored to the job description."}
            ],
            temperature=1,
            max_completion_tokens=MAX_TOKENS,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        generated_content = completion.choices[0].message.content
        logger.info("Successfully generated resume content")
        return generated_content
        
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def save_output(content: str, is_pdf: bool = False) -> Optional[str]:
    """
    Save the generated content to a file with timestamp.
    
    Args:
        content (str): Content to save
        is_pdf (bool): Whether to save as PDF
        
    Returns:
        Optional[str]: Path to the saved file or None if there's an error
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if is_pdf:
            output_file = Path(OUTPUT_DIR) / f"resume-{timestamp}.pdf"
            create_pdf_from_text(content, str(output_file))
        else:
            output_file = Path(OUTPUT_DIR) / f"resume-{timestamp}.txt"
            with open(output_file, "w", encoding='utf-8') as output:
                output.write(content)
        
        logger.info(f"Output saved to: {output_file}")
        return str(output_file)
    except Exception as e:
        logger.error(f"Error saving output file: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    """Handle resume file upload."""
    try:
        if 'resume' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF
            resume_text = extract_text_from_pdf(filepath)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'resume_text': resume_text
            })
        
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.error(f"Error in upload_resume route: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/generate', methods=['POST'])
def generate_resume():
    """Handle resume generation request."""
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400
            
        if 'resume' not in data or 'job_description' not in data:
            logger.error(f"Missing required fields. Received data: {data}")
            return jsonify({'error': 'Missing required fields'}), 400
        
        resume = data['resume']
        job_description = data['job_description']
        
        logger.info("Starting resume generation")
        
        # Generate customized resume
        generated_resume = generate_custom_resume(resume, job_description)
        
        if not generated_resume:
            logger.error("Failed to generate resume content")
            return jsonify({'error': 'Failed to generate resume'}), 500
        
        # Save the generated resume as PDF
        output_file = save_output(generated_resume, is_pdf=True)
        
        if not output_file:
            logger.error("Failed to save output file")
            return jsonify({'error': 'Failed to save resume'}), 500
        
        return jsonify({
            'success': True,
            'resume': generated_resume,
            'pdf_path': output_file
        })
        
    except Exception as e:
        logger.error(f"Error in generate_resume route: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Handle file download."""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

if __name__ == "__main__":
    # Setup environment
    setup_environment()
    
    # Run the Flask app
    app.run(debug=True)
