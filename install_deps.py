import subprocess
import sys
import os

def install_dependencies():
    """Install all required dependencies"""
    requirements = [
        'streamlit>=1.28.0',
        'pandas>=2.0.0',
        'openpyxl>=3.1.0', 
        'xlrd>=2.0.0'
    ]
    
    print("Installing dependencies for Meter Excel Processor...")
    
    for requirement in requirements:
        try:
            print(f"Installing {requirement}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", requirement
            ])
        except subprocess.CalledProcessError as e:
            print(f"Error installing {requirement}: {e}")
            return False
    
    print("✅ All dependencies installed successfully!")
    return True

def run_streamlit():
    """Run the Streamlit application"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_file = os.path.join(script_dir, "streamdep.py")
    
    print("Starting Streamlit application...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_file])

if __name__ == "__main__":
    if install_dependencies():
        run_streamlit()
    else:
        print("❌ Failed to install dependencies. Please install manually:")
        print("pip install streamlit pandas openpyxl xlrd")