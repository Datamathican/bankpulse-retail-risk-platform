"""Run from the repository root: python run.py all --customers 1200"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from bankpulse.cli import main
if __name__=="__main__":main()
