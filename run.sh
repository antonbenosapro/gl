#!/bin/bash

# Navigate to project directory
cd "$(dirname "$0")"

# Activate virtual environment
source env/bin/activate

# Launch Streamlit using venv environment
streamlit run Home.py

