#!/bin/bash
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo "Starting Meter Excel Processor..."
streamlit run streamdep.py