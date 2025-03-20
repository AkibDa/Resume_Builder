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
from typing import Optional
from pathlib import Path
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from groq import Groq
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Constants
MODEL_NAME = "llama-3.3-70b-versatile"
OUTPUT_DIR = "output"
MAX_TOKENS = 1024

def setup_environment() -> None:
    """Load environment variables and create necessary directories."""
    load_dotenv()
    if not os.getenv('GROQ_API_KEY'):
        raise ValueError("GROQ_API_KEY environment variable is not set")
    
    # Create output directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

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
        
        return completion.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        return None

def save_output(content: str) -> Optional[str]:
    """
    Save the generated content to a file with timestamp.
    
    Args:
        content (str): Content to save
        
    Returns:
        Optional[str]: Path to the saved file or None if there's an error
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_file = Path(OUTPUT_DIR) / f"resume-{timestamp}.txt"
        
        with open(output_file, "w", encoding='utf-8') as output:
            output.write(content)
        
        logger.info(f"Output saved to: {output_file}")
        return str(output_file)
    except Exception as e:
        logger.error(f"Error saving output file: {str(e)}")
        return None

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_resume():
    """Handle resume generation request."""
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data or 'resume' not in data or 'job_description' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        resume = data['resume']
        job_description = data['job_description']
        
        # Generate customized resume
        generated_resume = generate_custom_resume(resume, job_description)
        
        if not generated_resume:
            return jsonify({'error': 'Failed to generate resume'}), 500
        
        # Save the generated resume
        save_output(generated_resume)
        
        return jsonify({'resume': generated_resume})
        
    except Exception as e:
        logger.error(f"Error in generate_resume route: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Setup environment
    setup_environment()
    
    # Run the Flask app
    app.run(debug=True)
