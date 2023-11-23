import os
import datetime
import json
import sqlite3
import pandas as pd


from datetime import date, datetime, timedelta
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

from helpers import login_required, select_latest_csv, select_latest_JSON, fetch3mXAxis, fetch6mXAxis, fetch12mXAxis, validate_CSV
from app_core.blueprints.weight_processing_bp import weight_processing_bp, json_string_to_weight_plots, process_weight_log
from app_core.blueprints.training_processing_bp import fetch_training_table_data, process_training_log


CURRENT_TIME_DATE = datetime.now()
current_month = int(CURRENT_TIME_DATE.strftime("%m")) # %m prints month as digit
current_year = int(CURRENT_TIME_DATE.strftime("%Y")) #e.g 2013, 2019 etc.
current_day = int(CURRENT_TIME_DATE.strftime("%-d")) #e.g 1, 17, 31 etc. 
last_year = int(current_year) - 1

DATETIME_NOW = date(current_year, current_month, current_day) 

# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Registering blueprints
app.register_blueprint(weight_processing_bp)


# TODO: Check if db file exists, if not, create it

# Configure the user DB and engine for DB operations:
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# DB session factory/manager:
engine = create_engine('sqlite:///users.db') # simplifies DB interactions w/o manual creation of connections
DB_session_creator = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

users_table = Table(
    'users',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(64), unique=True, nullable=False),
    Column('password_hash', String(128), nullable=False),
)

# Disable caching + enable debug/auto reload of page:
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Define path to upload folders
app.config['WEIGHT_SUBMISSION_FOLDER'] = 'app_core/all_user_data/weight_data_submissions'
app.config['PROCESSED_WLOG_ARCHIVE'] = 'app_core/all_user_data/w_log_archive'
app.config['TRAINING_SUBMISSION_FOLDER'] = 'app_core/all_user_data/training_data_submissions'
app.config['PROCESSED_TRAINING_DATA'] = 'app_core/all_user_data/training_log_archive' # tabulator table data for heaviest PRs

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Clear any current user_id -- this page shouldn't render if user logged in anyway. 
    session.clear()
    error = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username").lower():
            error = "Please provide a username!"          

        # Ensure password was submitted
        elif not request.form.get("password"):
            error = "Please provide a password!"

        else:
            db_session = DB_session_creator()
            user = db_session.query(users_table).filter_by(username=request.form.get("username")).first() # return the first result using passed username as filter

            if user is None or not check_password_hash(user.password_hash, request.form.get("password")): 
                error = "Invalid username and/or password."
                return render_template("login.html", error=error)


            if error is None:
                # Remember which user has logged in
                session["user_id"] = user[1]
                print(f"Session saved for {(user[1]).capitalize()}")

            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        if not request.form.get("username"): #this will only execute if username is empty
            error = "Username cannot be empty."
            return render_template("register.html", error=error)

        if not request.form.get("password"):
            error = "Please enter a password."
            return render_template("register.html", error=error)

        elif not request.form.get("confirmation"):
            error = "Please confirm your password."
            return render_template("register.html", error=error)


        elif not request.form.get("password") == request.form.get("confirmation"):
            error = "Passwords do not match! Please try again."
            return render_template("register.html", error=error)

        # QueryDB to see if username exists, if so, return error. 
        db_session = DB_session_creator()
        name_check = db_session.query(users_table).filter_by(username=request.form.get("username")).first()

        if name_check:
            error = "Sorry, Username already exists - please try another one!"
            print("user exists - returning error.")
            return render_template("register.html", error=error)

        new_password = request.form.get("password")
        new_username = request.form.get("username")


        # New register valid -- hash the user's password and add them to DB
        hashed_password = generate_password_hash(new_password)
        db_session.execute(users_table.insert(), {'username': new_username, 'password_hash': hashed_password})
        db_session.commit()
        success = "Account Created! Please Sign in."

        return render_template("login.html", success=success)

    else:
        #this ensures that if the page was not reached by redirection (thus GET), it will show the new fields for new entry.
        return render_template("register.html")

@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    current_username = str(session["user_id"]).capitalize()

    return render_template("index.html", current_username = current_username)

@app.route('/team-dashboard', methods=["GET", "POST"])
@login_required
def teamDashboard():
    return render_template("team-dashboard.html") 

@app.route('/faq', methods=["GET", "POST"])
@login_required
def faq():
    return render_template("faq.html") 

@app.route('/tdee', methods=["GET", "POST"])
@login_required
def tdee():
    return render_template("tdee.html") 


@app.route('/checkin', methods=["GET", "POST"])
@login_required
def checkin():
    return render_template("checkin.html") 

@app.route('/my-dashboard', methods=["GET", "POST"])
@login_required
def my_dashboard():
    highest_W_table = []
    all_training_table = []
    SI_PR_table = []
    
    current_username = str(session["user_id"]).capitalize()

    #Prepare items to pass to Weight Line Graph -- dates on axis + points to plot:   
    x_axis_12 = fetch12mXAxis()
    x_axis_3 = fetch3mXAxis()
    x_axis_6 = fetch6mXAxis()    
     
    if request.method == "POST": # POST method indicates user was redirected to function by another. 
        return render_template("my_dashboard.html", x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6) 

    target_json_weight_file = select_latest_JSON("weight", session["user_id"]) # find the weight archive to load, for this user 
    
    # process most current JSON archive file with axis list to find average points to graph. 
    weight_graph_12m_points = json_string_to_weight_plots(x_axis_12, target_json_weight_file)
    weight_graph_6m_points = json_string_to_weight_plots(x_axis_6, target_json_weight_file)
    weight_graph_3m_points = json_string_to_weight_plots(x_axis_3, target_json_weight_file)
    current_weight = weight_graph_3m_points[-1]
    highest_W_table, all_training_table, SI_PR_table  = fetch_training_table_data(session["user_id"])
        
        
        # Fetch table data to serve to user page: 
        
    return render_template("my_dashboard.html",
                            current_username = current_username,
                            x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6,
                            weight_graph_12m_points = weight_graph_12m_points,
                            weight_graph_6m_points = weight_graph_6m_points,
                            weight_graph_3m_points = weight_graph_3m_points,
                            current_weight = current_weight,
                            highest_W_table = highest_W_table,
                            all_training_table = all_training_table,
                            SI_PR_table = SI_PR_table) 
            
    
@app.route('/upload', methods=["POST"])
def upload_file():
    """
    This function receives the file attached to the form submission for processing. 
    If file is found to not be of .csv/.txt or data validation fails, then file is deleted and error code is returned. 
    """

    VALID_EXTENSIONS = ('.csv', '.txt', '.CSV', '.TXT')
    heaviest_prs_data = []
    SI_PR_data = []
    all_training_data = []
    #Received object with form data is a list-like structure (immutable dict): 
    if len(request.form.getlist("uploadType")) == 0: # null check -- using string literal as JSON "none" was received
        print("Error: Form submission type not selected.")
        return "Error: Form submission type not selected.", 400

    submission_type = request.form.getlist("uploadType")[0]
    
    if submission_type == "training":        
        uploaded_file = request.files['userUpload']
        file_name = session["user_id"] + "_" + uploaded_file.filename
        
        if not file_name.endswith(VALID_EXTENSIONS): # .csv, .CSV, .txt or .TXT
            print("File is not of .txt or .csv")
            return "File format error. Please export your file and try again. ", 400
        
        print("File name: ", file_name)
        #save to files folder -- extend this logic to ensure no duplicates: 
        uploaded_file.save(os.path.join(app.config['TRAINING_SUBMISSION_FOLDER'], file_name))
        
        if validate_CSV(file_name, submission_type) == False:
            print("Bad upload - validation failed. Deleting file.")
            os.remove((os.path.join(app.config['TRAINING_SUBMISSION_FOLDER'], file_name)))
            return "File format error. Please export your file and try again. ", 400
        
        # Process the submitted training CSV to receive 3 lists of data: 
        heaviest_prs_data, SI_PR_data, all_training_data = process_training_log(session['user_id'])
        
        # Save the data as JSON, in training_tables folder: 
        heaviest_pr_filename = f"HeaviestPRs_{session['user_id']}_{DATETIME_NOW}"
        SI_PR_filename = f"SI_PRs_{session['user_id']}_{DATETIME_NOW}"
        all_training_data_filename = f"All_Training_Data_{session['user_id']}_{DATETIME_NOW}"

        filename_list = {heaviest_pr_filename:heaviest_prs_data, SI_PR_filename : SI_PR_data, all_training_data_filename: all_training_data}

        for filename, data_list in filename_list.items(): 
            output_filepath = os.path.join(app.config['PROCESSED_TRAINING_DATA'], filename)

            with open(output_filepath, 'w', encoding="utf-8") as output:
                output.write(json.dumps(data_list))

        return "Server file upload Success."        
    
    # Detect weight file and call processing function
    if submission_type == "weight":
        print("Detected Weight file... uploading.")
        
        uploaded_file = request.files['userUpload']
        file_name = session['user_id'] + "_" + uploaded_file.filename
        
        if not file_name.endswith(VALID_EXTENSIONS): # .csv, .CSV, .txt or .TXT
            print("File is not of .txt or .csv")
            return "File format error. Please export your file and try again. ", 400
        
        print("File name: ", file_name)
        #save to files folder -- extend this logic to ensure no duplicates: 
        uploaded_file.save(os.path.join(app.config['WEIGHT_SUBMISSION_FOLDER'], file_name))
        validate_CSV(file_name, submission_type)
        
        if not validate_CSV(file_name, submission_type):
            os.remove((os.path.join(app.config['WEIGHT_SUBMISSION_FOLDER'], file_name)))
            print("Bad upload - validation failed. Deleting file.")
            return "File format error. Please export your file and try again. ", 400
        
        process_weight_log(session['user_id'])
        return "Server file upload Success."

    return "Upload Error Occurred. Please contact Admin.", 400

if __name__ == "__main__":
    app.run(debug=True)