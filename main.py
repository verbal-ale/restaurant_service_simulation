from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/")
def run_sim():
    subprocess.run(["python", "run_sim.py"])
    return "Simulation executed!", 200
