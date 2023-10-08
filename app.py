import os
import datetime
import json
import pandas as pd


from datetime import date
from datetime import datetime
from boltons import timeutils

from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from json import loads, dumps
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash


# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

# Disable caching + enable debug/auto reload of page:
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Define path to upload folders
app.config['WEIGHT_LOG_FOLDER'] = 'files/weight_logs'
app.config['TRAINING_LOG_FOLDER'] = 'files/training_logs'
app.config['LOG_ARCHIVE'] = 'files/log_archive'
app.config['MAX_CONTENT_PATH'] = 50000 #sample files average 20KB. 

#Define appropriate CSV headers + byte length for validate function: 
TRAINING_HEADERS = "Date,Exercise,Category,Weight (kgs),Reps,Distance,Distance Unit,Time,Comment"
WEIGHT_HEADERS = "Date,Time,Measurement,Value,Unit,Comment"
T_HEADER_LENGTH = len(TRAINING_HEADERS) #works on logic that chars are one byte
W_HEADER_LENGTH = len(WEIGHT_HEADERS)
VALID_EXTENSIONS = ('.csv', '.txt', '.CSV', '.TXT')

#current time/date: 
CURRENT_TIME_DATE = datetime.now()


#return the current month as a digit
current_month = int(CURRENT_TIME_DATE.strftime("%m")) #%m prints month as digit
current_year = int(CURRENT_TIME_DATE.strftime("%Y")) #e.g 2013, 2019 etc.
current_day = int(CURRENT_TIME_DATE.strftime("%-d")) #e.g 1, 17, 31 etc. 
last_year = int(current_year) - 1

DATETIME_NOW = date(current_year, current_month, current_day) # use previous variables to build dateobject
print(f"DATETIME_NOW = {DATETIME_NOW}")

# test date object: 
current_month = 1 #%m prints month as digit
current_year = int(CURRENT_TIME_DATE.strftime("%Y")) #e.g 2013, 2019 etc.
current_day = 2 #e.g 1, 17, 31 etc. 
last_year = int(current_year) - 1

DATETIME_NOW = date(current_year, current_month, current_day) # use previous variables to build dateobject

@app.route('/', methods=["GET", "POST"])
def index():
    return render_template("index.html") 

@app.route('/team-dashboard', methods=["GET", "POST"])
def teamDashboard():
    return render_template("team-dashboard.html") 

@app.route('/athletes', methods=["GET", "POST"])
def athletes():
    return render_template("athletes.html") 

@app.route('/checkin', methods=["GET", "POST"])
def checkin():
    return render_template("checkin.html") 

#Athelete pages - maybe they can share a single function to call? 
@app.route('/tommy', methods=["GET", "POST"])
def tommy():
    #Prepare items to pass to Weight Line Graph:   
    x_axis_12 = fetch12mXAxis()
    x_axis_3 = fetch3mXAxis()
    x_axis_6 = fetch6mXAxis()
    
    if request.method == "POST": #POST method indicates user was redirected to function by another. 
        #Muscle Group Pie Graph:
        #call volume analysis function -- currently just prints the option:
        print("Entering POST method for tommy(): ")
        return render_template("tommy.html", x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6) 

    else: #GET method indicates user put address to route to the function.  
        return render_template("tommy.html", x_axis_12 = x_axis_12, x_axis_3 = x_axis_3, x_axis_6 = x_axis_6) 
            
@app.route('/nathan', methods=["GET", "POST"])
def nathan():
    return render_template("nathan.html") 

@app.route('/raymond', methods=["GET", "POST"])
def raymond():
    return render_template("raymond.html") 




def fetch_days_in_month(input_month):
    MONTHS_WITH_31_DAYS = [1, 3, 5, 7, 8, 10, 12]  # January, March, May, July, August, October, December
    MONTHS_WITH_30_DAYS = [4, 6, 9, 11]  # April, June, September, November

    if input_month in MONTHS_WITH_30_DAYS:
        return 30
    elif input_month in MONTHS_WITH_31_DAYS:
        return 31
    return 28


def fetch12mXAxis():
    prev_12_months = []

    # Find and append the first date to list, i.e, the last lapsed month, or if today is last day of month, today. : 
    if current_day == fetch_days_in_month(current_month):
        target_day = fetch_days_in_month(current_month)
        target_month = int(current_month)
        
    else:
        target_day = fetch_days_in_month(current_month -1)
        target_month = int(current_month) -1 

    target_year= int(current_year)

    new_date = date(target_year, target_month, target_day)
    data_point = new_date.strftime("%d %b, %Y")
    prev_12_months.append(data_point)
    counter = 1 

    while counter < 12: 
        if target_month == 1: # if month is Jan, decrement to prev year Dec
            target_month = 12
            target_year = target_year - 1
            target_month += 1
        
        target_month -= 1 # otherwise, just decrement month value and take last day of month to list:
        new_date = date(target_year, target_month, fetch_days_in_month(target_month))
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

    # Find and append the first date to list, i.e, the last lapsed month. If today is last day of month, use today:
    if current_day == fetch_days_in_month(current_month):
        target_day = fetch_days_in_month(current_month)
        target_month = int(current_month)

        new_date = date(target_year, target_month, target_day)
        target_day = 15
    
        
    elif current_day >= 15: # if it's greater than or equal to 15 (but not yet last date of month), set it to 15
        target_day = 15
        target_month = int(current_month)
        new_date = date(target_year, target_month, target_day)
        
        target_day = fetch_days_in_month(current_month-1)
        target_month = int(current_month-1)

    else:   # if current day is less than 15, set date to last day of prev month
        target_day = fetch_days_in_month(current_month-1)
        target_month = int(current_month-1)
        new_date = date(target_year, target_month, target_day)

    data_point = new_date.strftime("%d %b, %Y")
    prev_6_months.append(data_point)
    counter = 1 
 

    while counter < 12: # Decrement datetime object, for next axis tick: 
        if target_month <= 1 and target_day == 15: # if date is Jan 15th, decrement to prev year Dec 31st
            new_date = date(target_year, target_month, target_day)
            target_month = 12
            target_year = target_year - 1
            target_day = 31

        elif target_day == fetch_days_in_month(target_month):
            new_date = date(target_year, target_month, target_day)
            target_day = 15
        
        elif target_day >= 15: # if date is after 15th of month, set date to 15th of same month. 
            target_day = 15
            new_date = date(target_year, target_month, target_day)
            
            if target_month == 1:
                target_month = 12
            else:
                target_month -= 1 # decrement month for next iteration   
            target_day = fetch_days_in_month(target_month)         
            
        else: # else, if prior to month midpoint, set to last date of last month. 
            target_day = fetch_days_in_month(target_month)
            target_month -= 1 # decrement month for next iteration            
            new_date = date(target_year, target_month, target_day)
            
        #create target month's datetimeobject and append to list
        new_axis_tick = new_date.strftime("%d %b, %Y")
        prev_6_months.append(new_axis_tick)

        counter += 1 

    prev_6_months.reverse()
    return prev_6_months

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


def fetch3mXAxis():
    """ Datetime object to create should be either 15th or last day of month, whichever has most recently lapsed. 
        Current: not yet accounted for january edge case. 
    """

    prev_3_months = []
    target_year= int(current_year)

    # Find and append the first date to list, i.e, the last lapsed month, or if today is last day of month, today:
    if current_day == fetch_days_in_month(current_month):
        target_day = fetch_days_in_month(current_month)
        target_month = int(current_month)
        new_date = date(target_year, target_month, target_day)

        target_day = 21

    elif current_day == 7 and current_month == 1:
        target_day = 31
        target_month = 12
        target_year -= 1

    elif current_day == 7:
        target_day = current_month
        target_month = current_month

        new_date = date(target_year, current_month, current_day)
        target_month -= 1
        target_day = fetch_days_in_month(current_month-1)

    else: #else, set to closest fact 7 date. 
        target_day = closest_date_fact_7(current_day, current_month)
        target_month = int(current_month)
        new_date = date(target_year, target_month, target_day)
        
        target_day -= 7 # <-------- not assigning to variable? 
        print(f"first date append 3m: {target_day}")

    print(f"date before appending first time: {target_year} - {target_month} - {target_day}")
    new_axis_tick = new_date.strftime("%d %b, %Y")
    prev_3_months.append(new_axis_tick)
    counter = 1 
 

    while counter < 12: # Decrement datetime object, for next axis tick: 
        """ it's skipping months when using the 15th in datetime object
        """
        if target_month <= 1 and target_day == 7: # if date is Jan 7th, decrement to prev year Dec 31st
            target_month = 12
            target_year = target_year - 1
            target_day = 31
            new_date = date(target_year, target_month, target_day)
            target_day -= 7
        
        elif target_day == 7:
            new_date = date(target_year, target_month, target_day)
            target_day -= 8
            
        elif target_day < 7: #if 7th of any other month, decrement to last date of prev month. 
            target_month -= 1
            target_day = fetch_days_in_month(target_month)
            new_date = date(target_year, target_month, target_day)
            target_day = fetch_days_in_month(target_month-1)
        
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


@app.route('/volume_analysis', methods=["POST"])
def volume_analysis():
    print("Entered volume_analysis.")
    target_period = request.get_json("userPeriod") #this is not fetching the option properly.... 
    print("volume_analysis print of target_period: ", target_period)
    return jsonify(target_period)
    
    
@app.route('/upload', methods=["POST"])
def upload_file():
    """
    This function receives the file attached to the form submission for processing. 
    If file is found to not be of .csv/.txt or data validation fails, then file is deleted and error code is returned. 
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
        
        process_weight_log()
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
            print("File headers are valid - uploading file. ")
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
    


def process_weight_log():
    """
        This function is called when the user prompts a button on the check-in page of website. 
        - All sheets in the related file directories are processed to pull out relevant data into a  {"date":"weight"} JSON list. 
        - These JSON files will be backed up on the file system to operate as a "snapshot". 
        - Eventually, these snapshots will be viewable, and recoverable.         
    """
    #TODO: Might need to revisit after working on sessions and user authentication. 
    #NOTE: This function will delete existing copies of the json file, so insert a backup function before proceeding

    #Create a JSON file to populate in the archive folder, 
    #TODO: Upload to/create within folder according to username
    temp_file = "temp_processing.json"
    weight_history = {}
    temp_file_location = os.path.join(app.config['LOG_ARCHIVE'], temp_file)

    #create temp file the existing json log file. 
    with open(temp_file_location, 'w', encoding="utf-8") as weight_history_log:
        weight_history_log.write(json.dumps(weight_history))

    #Start processing the CSV's, extracting relevant data into a python dictionary.
     

    #Check for most recent file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 
    weight_logs_directory = os.listdir(app.config['WEIGHT_LOG_FOLDER'])    

    input_format = "%Y_%m_%d_%H_%M_%S" 
    output_iso_format = "%Y-%m-%dT%H:%M:%S"
    file_prefix = "/FitNotes_BodyTracker_Export_" 
    file_suffix = ".csv"
    date_list = {} 


    for item in weight_logs_directory: 
        sliced_filename = item[item.index("202"):item.index(".csv")] #index between year and csv (inclusive of year but not csv)
        unformatted_date = datetime.strptime(sliced_filename, input_format)
        iso_date = unformatted_date.strftime(output_iso_format)
        date_list[sliced_filename] = iso_date


    latest_fitnotes_file = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable

    # drop irrelevant columsn in target file, creating a python dictionary of {date:weight} 
    drop_columns = ["Time", "Measurement", "Unit", "Comment"]

    # build file name using the date of the most recent submitted fitnotes sheet
    filename = f"{file_prefix}{latest_fitnotes_file}{file_suffix}"
    df = pd.read_csv(app.config['WEIGHT_LOG_FOLDER']+filename)

    # use pandas to extract log entry dates and weights
    cleaned_df = df.drop(drop_columns, axis='columns')
    parsed_entries_string= cleaned_df.to_json(orient='split') #argument to convert output to json string

    # load that data into a string of dates. 
    loaded_entries = json.loads(parsed_entries_string)
    log_entry_data = loaded_entries["data"]
    log_entry_dates = []

    for item in log_entry_data:
        log_entry_dates.append(item[0])
    print(f"{log_entry_dates}")

    # take the last date entry as the most recent one -- create final output file name:
    latest_entry_date = log_entry_dates[len(log_entry_dates)-1]

    output_filename = f"WeightLog_username_up_to_{latest_entry_date}"
    output_filepath = os.path.join(app.config['LOG_ARCHIVE'], output_filename)

    with open(output_filepath, 'w', encoding="utf-8") as final_json_output:
        final_json_output.write(json.dumps(parsed_entries_string))
    
    # clean up temp file and return:
    os.remove(temp_file_location)

    return "Entered process_csv."


if __name__ == "__main__":
    app.run(debug=True)