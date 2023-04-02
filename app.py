import os
import time
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def index():
    return render_template("index.html") 



