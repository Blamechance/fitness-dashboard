import os
import datetime
import json
import pandas as pd
import sqlite3


from datetime import date, datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

from json import loads, dumps
from login_helpers import login_required


# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# TODO: Check if db file exists, if not, create it. 

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
app.config['WEIGHT_LOG_FOLDER'] = 'files/weight_logs'
app.config['TRAINING_LOG_FOLDER'] = 'files/training_logs'
app.config['LOG_ARCHIVE'] = 'files/log_archive'
app.config['PROCESSED_TRAINING_DATA'] = 'files/training_tabulator_data' # tabulator table data for heaviest PRs

#Define appropriate CSV headers + byte length for validate function: 
TRAINING_HEADERS = "Date,Exercise,Category,Weight,Weight Unit,Reps,Distance,Distance Unit,Time,Comment"

WEIGHT_HEADERS = "Date,Time,Measurement,Value,Unit,Comment"
T_HEADER_LENGTH = len(TRAINING_HEADERS) #works on logic that chars are one byte
W_HEADER_LENGTH = len(WEIGHT_HEADERS)
VALID_EXTENSIONS = ('.csv', '.txt', '.CSV', '.TXT')

#current time/date: 
CURRENT_TIME_DATE = datetime.now()


#return the current month as a digit
current_month = int(CURRENT_TIME_DATE.strftime("%m")) # %m prints month as digit
current_year = int(CURRENT_TIME_DATE.strftime("%Y")) #e.g 2013, 2019 etc.
current_day = int(CURRENT_TIME_DATE.strftime("%-d")) #e.g 1, 17, 31 etc. 
last_year = int(current_year) - 1

DATETIME_NOW = date(current_year, current_month, current_day) 

print(f"DATETIME_NOW = {DATETIME_NOW}")

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
            print(f"user exists - returning error.")
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
    return render_template("index.html") 

@app.route('/team-dashboard', methods=["GET", "POST"])
@login_required
def teamDashboard():
    return render_template("team-dashboard.html") 

@app.route('/athletes', methods=["GET", "POST"])
def athletes():
    return render_template("athletes.html") 

@app.route('/checkin', methods=["GET", "POST"])
@login_required
def checkin():
    return render_template("checkin.html") 

@app.route('/tommy', methods=["GET", "POST"])
@login_required
def tommy():
    #Prepare items to pass to Weight Line Graph -- dates on axis + points to plot:   
    x_axis_12 = fetch12mXAxis()
    x_axis_3 = fetch3mXAxis()
    x_axis_6 = fetch6mXAxis()    
     
    if request.method == "POST": # POST method indicates user was redirected to function by another. 
        # Muscle Group Pie Graph:
        # call volume analysis function -- currently just prints the option:
        print("Entering POST method for tommy(): ")
        return render_template("tommy.html", x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6) 

    else: # GET method indicates user put address to route to the function.  
        target_json_weight_file = select_latest_JSON("weight", "Tommy") # find the weight archive to load 
        
        # process most current JSON archive file with axis list to find average points to graph. 
        weight_graph_12m_points = json_string_to_weight_plots(x_axis_12, target_json_weight_file)
        weight_graph_6m_points = json_string_to_weight_plots(x_axis_6, target_json_weight_file)
        weight_graph_3m_points = json_string_to_weight_plots(x_axis_3, target_json_weight_file)
        current_weight = weight_graph_3m_points[-1]
        highest_W_table, all_training_table, SI_PR_table  = fetch_training_table_data("Tommy")
        
        
        # Fetch table data to serve to user page: 
        
        return render_template("tommy.html",
                               x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6,
                                weight_graph_12m_points = weight_graph_12m_points,
                                weight_graph_6m_points = weight_graph_6m_points,
                                weight_graph_3m_points = weight_graph_3m_points,
                                current_weight = current_weight,
                                highest_W_table = highest_W_table,
                                all_training_table = all_training_table,
                                SI_PR_table = SI_PR_table) 
            
@app.route('/nathan', methods=["GET", "POST"])
def nathan():
    return render_template("nathan.html") 

@app.route('/raymond', methods=["GET", "POST"])
def raymond():
    return render_template("raymond.html") 


def fetch_training_table_data(username): 
    """
        Fetchs the training table data and returns it as a JSON object. 
    """
    heaviest_PR_file = select_latest_JSON("HeaviestPRs", username)
    all_training_file = select_latest_JSON("All_Training_Data", username)
    SI_PR_file = select_latest_JSON("SI_PRs", username)

    file_list = [heaviest_PR_file, all_training_file, SI_PR_file]
    output_lists = []

    for file in file_list:
        filepath = os.path.join(app.config['PROCESSED_TRAINING_DATA'], file)
    
        with open(filepath, 'r') as open_file:
            output_lists.append(json.load(open_file))
    return output_lists



def fetch_days_in_month(input_month):
    MONTHS_WITH_31_DAYS = [1, 3, 5, 7, 8, 10, 12]  # January, March, May, July, August, October, December
    MONTHS_WITH_30_DAYS = [4, 6, 9, 11]  # April, June, September, November

    if input_month in MONTHS_WITH_30_DAYS:
        return 30
    elif input_month in MONTHS_WITH_31_DAYS:
        return 31
    return 28

# Following date functions should be refactored to decrement only before commiting a transaction.
def fetch12mXAxis():
    prev_12_months = []
    target_month = int(current_month)
    target_year= int(current_year)
    target_day = int(current_day)

    counter = 0

    while counter < 12: 
        if target_month == 1 and target_day < 31: # if month is Jan and not yet 31st, decrement to prev year Dec
            target_month = 12
            target_day = 31
            target_year = target_year - 1
            new_date = date(target_year, target_month, fetch_days_in_month(target_month))

            # decrement
            target_month -= 1
            target_day = fetch_days_in_month(target_day)            

        if target_day == fetch_days_in_month(target_month): #if last date of month, include current month: 
            new_date = date(target_year, target_month, fetch_days_in_month(target_month))
            if target_month == 1: # if month is jan, decrement properly now that object is made. 
                target_month = 12
                target_day = 31
                target_year = target_year - 1
            else:
                target_month -= 1
                target_day = fetch_days_in_month(target_month) 
    
        else: # if not yet last date of month, use last month: 
            target_month -= 1
            target_day = fetch_days_in_month(target_month) 
            new_date = date(target_year, target_month, fetch_days_in_month(target_month))

            # decrement: 
            if target_month == 1: # if month is jan, decrement properly now that object is made. 
                target_month = 12
                target_day = 31
                target_year = target_year - 1
            else:
                target_month -= 1
                target_day = fetch_days_in_month(target_month)     
        
        new_axis_tick = new_date.strftime("%d %b, %Y")
        prev_12_months.append(new_axis_tick)
        counter += 1 

    prev_12_months.reverse()
    return prev_12_months



def fetch6mXAxis():
    """ Datetime object to create should be either 15th or last day of month, whichever has most recently lapsed. 
    """
    prev_6_months = []
    target_year= int(current_year)
    target_day = int(current_day)
    target_month = int(current_month)
    counter = 0  

    while counter < 12: # Decrement datetime object, for next axis tick: 
        if target_month == 1 and target_day == 15: # if date is Jan 15th, decrement to prev year Dec 31st / perfect case
            new_date = date(target_year, target_month, target_day)
            target_month = 12
            target_year = target_year - 1
            target_day = 31

        elif target_day == fetch_days_in_month(target_month): # perfect case no decrement prior
            new_date = date(target_year, target_month, target_day)
            target_day = 15
        
        elif target_day >= 15: # if date is after 15th of month, set date to 15th of same month. 
            target_day = 15
            new_date = date(target_year, target_month, target_day)
            
            if target_month == 1:
                target_month = 12
                target_day = fetch_days_in_month(12)         

            else:
                target_month -= 1 # decrement month for next iteration   
                target_day = fetch_days_in_month(target_month)         
            
        else: # else, if prior to month midpoint, set to last date of last month. 
            if target_month == 1:
                target_month = 12
                target_day = fetch_days_in_month(target_month)
                new_date = date(target_year, target_month, target_day)
            else:
                target_month -= 1 # decrement month for next iteration  
                target_day = fetch_days_in_month(target_month)
                new_date = date(target_year, target_month, target_day)

            if target_month == 1: # decrement for next iteration
                target_month = 12
                target_day = fetch_days_in_month(12)         

            else:
                target_month -= 1 # decrement month for next iteration   
                target_day = fetch_days_in_month(target_month)               
        #create target month's datetimeobject and append to list
        new_axis_tick = new_date.strftime("%d %b, %Y")
        prev_6_months.append(new_axis_tick)

        counter += 1 

    prev_6_months.reverse()
    return prev_6_months




def fetch3mXAxis():
    def closest_date_fact_7(input_date, input_month):
        exact_match = [7,14,21]
        if input_date in exact_match:
            return input_date
        if input_date == fetch_days_in_month(input_month):
            return input_date
        
        if input_date < 7:
            return fetch_days_in_month(input_month-1)
        if input_date < 14:
            return 7
        if input_date < 21:
            return 14
        return 21 #else, if in last stretch of month, just return the last date. 
    
    prev_3_months = []
    target_year= int(current_year)
    target_day = int(current_day)
    target_month = int(current_month)
    counter = 0
 
    while counter < 12: # Decrement datetime object, for next axis tick: 
        if target_month <= 1 and target_day == 7: # if date is Jan 7th, decrement to prev year Dec 31st
            new_date = date(target_year, target_month, target_day)
            target_month = 12
            target_year = target_year - 1
            target_day = 31
        
        elif target_day == fetch_days_in_month(target_month):
            new_date = date(target_year, target_month, target_day)
            target_day = 21

        elif target_day >= 21:
            target_day = 21
            new_date = date(target_year, target_month, target_day)
            target_day = 14

        else: #else, decrement to closest date that is factor of 7. 
            target_day = closest_date_fact_7(target_day, target_month)
            new_date = date(target_year, target_month, target_day)

            if target_day <= 7: 
                target_day = fetch_days_in_month(target_month-1)
                target_month = target_month-1
            else: 
                target_day -= 7

        #create target month's datetimeobject and append to list
        new_axis_tick = new_date.strftime("%d %b, %Y")
        prev_3_months.append(new_axis_tick)

        counter += 1 

    prev_3_months.reverse()
    return prev_3_months

    
@app.route('/upload', methods=["POST"])
def upload_file():
    """
    This function receives the file attached to the form submission for processing. 
    If file is found to not be of .csv/.txt or data validation fails, then file is deleted and error code is returned. 

    TODO: Pass an argument to process_weight_log() that contains username. 
    """
    #Received object with form data is a list-like structure (immutable dict): 
    if len(request.form.getlist("uploadType")) == 0: # null check -- using string literal as JSON "none" was received
        print("Error: Form submission type not selected.")
        return "Error: Form submission type not selected.", 400

    submission_type = request.form.getlist("uploadType")[0]
    
    if submission_type == "training":        
        uploaded_file = request.files['userUpload']
        file_name = uploaded_file.filename
        
        if not file_name.endswith(VALID_EXTENSIONS): # .csv, .CSV, .txt or .TXT
            print("File is not of .txt or .csv")
            return "File format error. Please export your file and try again. ", 400
        
        print("File name: ", file_name)
        #save to files folder -- extend this logic to ensure no duplicates: 
        uploaded_file.save(os.path.join(app.config['TRAINING_LOG_FOLDER'], file_name))
        
        if validate_CSV(file_name, submission_type) == False:
            print("Bad upload - validation failed. Deleting file.")
            os.remove((os.path.join(app.config['TRAINING_LOG_FOLDER'], file_name)))
            return "File format error. Please export your file and try again. ", 400
        
        # Process the submitted training CSV to receive 3 lists of data: 
        heaviest_prs_data, SI_PR_data, all_training_data = process_training_log()
        
        # Save the data as JSON, in training_tables folder: 
        heaviest_pr_filename = f"HeaviestPRs_username_{DATETIME_NOW}"
        SI_PR_filename = f"SI_PRs_username_{DATETIME_NOW}"
        all_training_data_filename = f"All_Training_Data_username_{DATETIME_NOW}"

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
        file_name = uploaded_file.filename
        
        if not file_name.endswith(VALID_EXTENSIONS): # .csv, .CSV, .txt or .TXT
            print("File is not of .txt or .csv")
            return "File format error. Please export your file and try again. ", 400
        
        print("File name: ", file_name)
        #save to files folder -- extend this logic to ensure no duplicates: 
        uploaded_file.save(os.path.join(app.config['WEIGHT_LOG_FOLDER'], file_name))
        validate_CSV(file_name, submission_type)
        
        if validate_CSV(file_name, submission_type) == False:
            os.remove((os.path.join(app.config['WEIGHT_LOG_FOLDER'], file_name)))
            print("Bad upload - validation failed. Deleting file.")
            return "File format error. Please export your file and try again. ", 400
        
        process_weight_log()
        return "Server file upload Success."

    return "Upload Error Occurred. Please contact Admin.", 400

def validate_CSV(file_name, type):
    """
    This function checks that the uploaded file is:
     - A text/CSV file
     - of correct header format and length, for the respective chosen file type
     
    """
    print("Type is: ", type)
    
    if type == "training": 
        #set location of file: 
        file_location = os.path.join(app.config['TRAINING_LOG_FOLDER'], file_name)
        
        #open uploaded file
        reader = open(file_location, "r")
        reader.flush()
        
        #read all file contents: 
        file_headers = reader.read(T_HEADER_LENGTH)
        
        #check if headers are as expected: 
        if file_headers == TRAINING_HEADERS:
            print("Training file headers are valid -  in submission. Uploading file. ")
            reader.close
            return True

        else: # delete the file from directory and return error 400 to user as file is invalid
            print("CSV file not in expected format - aborting upload.")
            reader.close
            return False 
    
    if type == "weight":
        #set location of file: 
        file_location = os.path.join(app.config['WEIGHT_LOG_FOLDER'], file_name)
        
        #open uploaded file
        reader = open(file_location, "r")
        reader.flush()
        
        #read all file contents: 
        file_headers = reader.read(W_HEADER_LENGTH)
        
        #check if headers are as expected: 
        if file_headers == WEIGHT_HEADERS:
            reader.close
            return True

        else: # delete the file from directory and return error 400 to user as file is invalid
            print("CSV file not in expected format - aborting upload.")
            reader.close
            return False 
    return False
    
def select_latest_csv(data_type):
    log_dir = os.listdir(app.config[f"{data_type}"])    
    input_format = "%Y_%m_%d_%H_%M_%S" 
    output_iso_format = "%Y-%m-%dT%H:%M:%S"
    file_suffix = ".csv"
    date_list = {} 

    if data_type == "WEIGHT_LOG_FOLDER":
        file_prefix = "/FitNotes_BodyTracker_Export_" 

    elif data_type == "TRAINING_LOG_FOLDER":
        file_prefix = "/FitNotes_Export_" 


    #Check for most recent file, in weight log folder. Use that most recent folder to create JSON string archive file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 

    #NOTE: Wrap in a try-except so the except can delete temp file on error.
    #TODO: Need to integrate username checking logic. 

    for item in log_dir: 
        sliced_filename = item[item.index("202"):item.index(".csv")] #index between year and csv (inclusive of year but not csv)
        unformatted_date = datetime.strptime(sliced_filename, input_format)
        iso_date = unformatted_date.strftime(output_iso_format)
        date_list[sliced_filename] = iso_date


    latest_fitnotes_file = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable
    filename = f"{file_prefix}{latest_fitnotes_file}{file_suffix}"
    return filename

def select_latest_JSON(data_type, username):
    datetime_format = "%Y-%m-%d"
    date_list = []

    if data_type == "weight":
        log_dir = os.listdir(app.config['LOG_ARCHIVE'])
        file_prefix = "WeightLog_" 

    elif data_type == "HeaviestPRs":
        log_dir = os.listdir(app.config['PROCESSED_TRAINING_DATA'])
        file_prefix = "HeaviestPRs_" 

    elif data_type == "All_Training_Data":
        log_dir = os.listdir(app.config['PROCESSED_TRAINING_DATA'])
        file_prefix = "All_Training_Data_" 

    elif data_type == "SI_PRs":
        log_dir = os.listdir(app.config['PROCESSED_TRAINING_DATA'])
        file_prefix = "SI_PRs_" 

    for item in log_dir: 
        sliced_filename = item[item.index("202"):] #index between year and csv (inclusive of year but not csv)
        date_list.append(sliced_filename)
    
    filename = f"{file_prefix}{username}_{str(max(date_list))}"
    return filename

    

def process_weight_log():

    """
        This function is called when the user prompts a button on the check-in page of website. 
        - All sheets in the related file directories are processed to pull out relevant data into a  {"date":"weight"} JSON list. 
        - These JSON files will be backed up on the file system to operate as a "snapshot" in the archive folder. 
    """
    # Parse for non-bodyweight rows to delete,
    # then drop irrelevant column in target file, creating a python dictionary of {date:weight} 
    # build file name using the date of the most recent submitted fitnotes sheet
    filename = select_latest_csv("WEIGHT_LOG_FOLDER")
    df = pd.read_csv(app.config['WEIGHT_LOG_FOLDER']+filename)
    drop_columns = ["Time", "Measurement", "Unit", "Comment"]



    # use pandas to extract log entry dates and weights, but only if it's bodyweight data
    df = df.loc[df["Measurement"] == "Bodyweight" ]
    cleaned_df = df.drop(drop_columns, axis='columns')
    parsed_entries_string = cleaned_df.to_json(orient='split') #argument to convert output to json string

    # load that data into a string of dates. 
    loaded_entries = json.loads(parsed_entries_string)
    log_entry_data = loaded_entries["data"]
    log_entry_dates = []

    for item in log_entry_data:
        log_entry_dates.append(item[0])


    # take the last date entry as the most recent one -- create final output file name:
    latest_entry_date = log_entry_dates[len(log_entry_dates)-1]

    output_filename = f"WeightLog_username_{latest_entry_date}"
    output_filepath = os.path.join(app.config['LOG_ARCHIVE'], output_filename)
    print(f"Output file path in weight is: {output_filepath}")

    with open(output_filepath, 'w', encoding="utf-8") as final_json_output:
        final_json_output.write(parsed_entries_string)

    return "Entered process_csv."

def process_training_log():
    def calculate_SI(index):
        """
        This function takes a df row of the training data, and uses it to return a 
        strength index score. 
        
        The key for the rep range factor represents the lower and upper rep count for each range. 
        The value representing the factor to use in the calculation. 
        if the rep range is outside of the rep_range_factor, then return "N/A". 
        """
        rep_count = df.at[index, "Reps"]
        rep_range_factor = {
            (1, 2):3.3,
            (3,6):1.4,
            (7,10):1,
            (11,15):0.8,
        }
        
        if rep_count < 15 and rep_count > 1:
            for key, value in rep_range_factor.items(): # for each range in the rep_rage dict, what factor current reps should get: 
                if rep_count >= key[0] and rep_count <= key[1]: 
                    factor = value
                    break
            rep_count = df.loc[index]
            SI_output = (df.at[index, "Reps"] * df.at[index, "Weight"] * 10) / (df.at[index, "Bodyweight"] * factor)
            return round(SI_output,2)
        return 0
    
    username = "Tommy"
    latest_training_csv = select_latest_csv("TRAINING_LOG_FOLDER")
    latest_weight_json = select_latest_JSON("weight", username) 
    latest_weight_archive_location = os.path.join(app.config['LOG_ARCHIVE'] , latest_weight_json)
    df_format_archive = "%Y-%m-%d"
    drop_columns = ["Distance", "Distance Unit", "Time"]
    
    # Drop all unrelated columns in dataframe + drop any sets of same details within same day + add columns for BW/SI
    df = pd.read_csv(app.config['TRAINING_LOG_FOLDER']+latest_training_csv)
    df.drop(drop_columns, axis='columns', inplace=True)
    df.drop_duplicates(keep="first", inplace=True, ignore_index=True)
    
    # convert all NaN fields to a generic datatypes for easier handling 
    df['Comment'] = df['Comment'].fillna("N/A") 
    df['Weight'] = df['Weight'].fillna(0) 
    df['Weight Unit'] = df['Weight Unit'].fillna("kgs") 
    df['Reps'] = df['Reps'].fillna(0) 

    # This loop iterates through each of the training log data rows to do the following: 
    # 1. Takes the date the lift was executed to seach through the most recent weight log archive file. 
    #    Any weight entries for dates +/-3 days from lift date, get averaged and appended to the row.
    # 2. Using the user weight and weight lifted, calculate a strength index. 
    # 3. If no matches at all, set BW + Strength Index to 00. 
    
    for index, row in df.iterrows():
        lift_date = datetime.strftime(datetime.strptime(row["Date"], df_format_archive), df_format_archive) # date as string
        
        # Define the 7 day window as a list of dates:
        lower_date = datetime.strptime(lift_date, df_format_archive) - timedelta(days=3)
        search_dates = []
        matching_weight = [] 

        # helper dicts to store df rows, of {exercise_name:{dicts of lift details}}
        heaviest_weight_helper_dict = {} # list containing dicts of exercises that are the top PR's 
        SI_PR_helper_dict = {}
    

        # Following are the output lists to return: 
        heaviest_weight_prs = []
        strength_index_prs = []
        all_training_data = []

        for i in range(7):
            search_dates.append((lower_date + timedelta(days=i)).strftime(df_format_archive))

        # Parse through the JSON archive file to check if there are any weight check-ins matching any of the dates. 
        # if so, average all matching dates and return -- otherwise, return None: 
        with open(latest_weight_archive_location) as reader:
            # Load the JSON string file into variable as a python dict
            WLog_entries_dict = json.loads(reader.read()) 
            for pair in WLog_entries_dict["data"]:
                if pair[0] == lift_date:
                    matching_weight.append(pair[1]) # otherwise, append close dates to list
                    df.at[index, 'Bodyweight'] = pair[1] # if precise weight record found, return just that
                    continue
                
                if pair[0] in search_dates:
                    matching_weight.append(pair[1]) # otherwise, append close dates to list
                    
        # If not weight data, skip appending BW + SI: 
        if not matching_weight:    
            df.at[index, 'Bodyweight'] = 0
            df.at[index, 'Strength Index'] = 0
            continue
        
        # Otherwise, append found weight to df + calculate strength index. 
        average_weight = round(sum(matching_weight) / len(matching_weight), 2) # average the list of close weight records to return result
        df.at[index, 'Bodyweight'] = average_weight # Update the 'Bodyweight' of the current row      
        
        # Update the 'Strength Index' of the current row  
        s_index = calculate_SI(index)
        df.at[index, 'Strength Index'] = s_index     

    for index, row in df.iterrows():
       ### 1. Iterate over df, searching for heaviest weight PRs to append: 
        # Check if the PR list contains a dict entry with the same key as this exerise - if not, append this one as {ex_name: entire_row}
        if df.at[index, 'Exercise'] not in heaviest_weight_helper_dict: 
            heaviest_weight_helper_dict[df.at[index, 'Exercise']] = row.to_dict()
        
        # if exists and current row is better than one in PR, replace it. Table data will hold date lift was first hit:         
        for exercise, lift_data in heaviest_weight_helper_dict.items():    
            #only replace row if more reps and more weight, or same weight and higher reps        
            if df.at[index, 'Weight'] > lift_data["Weight"] and df.at[index, 'Exercise'] == exercise:
                heaviest_weight_helper_dict[exercise] = row.to_dict()
                      
            elif df.at[index, 'Weight'] == lift_data["Weight"] and df.at[index, 'Exercise'] == exercise and df.at[index, "Reps"] > lift_data["Reps"]: 
                heaviest_weight_helper_dict[exercise] = row.to_dict()   

    ### 2. Iterate over df, searching for Highest Strength Index Lifts to append:
        if df.at[index, 'Exercise'] not in SI_PR_helper_dict and df.at[index, 'Strength Index'] > 0 : 
            SI_PR_helper_dict[df.at[index, 'Exercise']] = row.to_dict()
        
        # if exists and current row is better than one in PR, replace it. Table data will hold date lift was first hit:         
        for exercise, lift_data in SI_PR_helper_dict.items():
            # if no strength index data, skip row: 
            if df.at[index, 'Strength Index'] == 0:
                continue    

            # if new row has better strength index for the exercise, update it:         
            if df.at[index, 'Strength Index'] > lift_data["Strength Index"] and df.at[index, 'Exercise'] == exercise:
                SI_PR_helper_dict[exercise] = row.to_dict()

            # if matched in strength index, update anyway for more current data:           
            elif df.at[index, 'Strength Index'] == lift_data["Strength Index"] and df.at[index, 'Exercise'] == exercise: 
                SI_PR_helper_dict[exercise] = row.to_dict()   


    # output aggregated data as list of dicts, to be parsed into JSON later: 
    [heaviest_weight_prs.append(value) for value in heaviest_weight_helper_dict.values()]
    [strength_index_prs.append(value) for value in SI_PR_helper_dict.values()]
    all_training_data = df.to_dict('records') # 3. All lifts, unsorted.  
    
    return heaviest_weight_prs, strength_index_prs, all_training_data
        
    

def json_string_to_weight_plots(axis, filename):
    """ This function takes a filename string that points to a JSON string file and returns a python list object.
        Args: (list of axis ticks), (JSON file to use's name)
    
        Input file is as provided by process_weight_log(), consisting of json weight log entries. 
        The JSON data is processed, creating average values respective of the window between axis points. 
        
        e.g if received list is ['14 Aug, 2023', '21 Aug, 2023']:
            - the value for "21 Aug, 2023" will be an average of all entries between then and the prev date ("14 Aug, 2023"), 
            - This logic will follow up until the first date. 
                - If the first date has entries before it, then use the same logic. 
            - If any window/tick does not have entries before it to average, it will:
                - If it's first or last point, it will use the closest calculated point. 
                - If it's between calculated points, it will instead average the two closest calcualted points. 
        
    """
    datetime_format = "%Y-%m-%d"
    axis_format = "%d %b, %Y" 
    file_location = os.path.join(app.config['LOG_ARCHIVE'], filename)    
    
    with open(file_location) as reader:
        # Load the JSON string file into variable as a python dict
        WLog_entries_dict = json.loads(reader.read()) 
        output_data = []
        input_weight_data = {} # to sort weight entries into. {axis point: [list of dates belonging to that window]}
        min_date =  datetime.strptime(axis[0], axis_format) - (datetime.strptime(axis[1], axis_format) - datetime.strptime(axis[0], axis_format)) # Find the increment distance for this axis, and do not further than one decrement from first axis. 

        for axis_date in axis: # take axis input as the keys for new dict -- values will a list bucket for all appropriate entries
            date = datetime.strptime(axis_date, axis_format)
            input_weight_data[date] = []
        
        # filter each weight entry through the time periods to sort - if it's within scope of axis dates:   
        for pair in WLog_entries_dict["data"]:
            for i in range(len(axis)):
                target_date = datetime.strptime(pair[0], datetime_format)
                target_axis_date = datetime.strptime(axis[i], axis_format)

                if (target_date >= min_date and
                    target_date <= target_axis_date):
                        input_weight_data[target_axis_date].append(pair[1])
                        break
        
        # check if each axis has a list, if not, generate an average value
        previous_list = [] # holder for previous valid data, to swap for any zero lists.

        if not any(input_weight_data.values()): # no matching data points at all, return empty list.
            print(f"No relevant data found in file for graph!") 
            return [0] * len(axis)

        for values in input_weight_data.values(): # take at least one data point to fill zero list replacement variable. 
            if values:
                previous_list = values.copy()
                break 

        for key, values in input_weight_data.items(): # update prev valid list var, if valid
            if values:
                previous_list = values.copy()
            
            elif not values: # if empty list detected, take previous valid list as estimate. 
                input_weight_data[key] = previous_list.copy()


        # average lists to find final list of values to return:
        for value in input_weight_data.values():                
            average_for_period = sum(value) / len(value)
            output_data.append(round(average_for_period, 2))

        return output_data
    
if __name__ == "__main__":
    app.run(debug=True)