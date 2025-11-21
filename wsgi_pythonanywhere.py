# PythonAnywhere WSGI Configuration File
#
# Copy this content to your WSGI file at:
# /var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py
#
# Replace YOUR_USERNAME with your actual PythonAnywhere username

import sys
import os

# Add your project directory to path
# IMPORTANT: Replace YOUR_USERNAME with your actual username
project_home = '/home/YOUR_USERNAME/racing-ai'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable for the app
os.environ['FLASK_ENV'] = 'production'

# Import the Flask app
from app_pythonanywhere import app as application
