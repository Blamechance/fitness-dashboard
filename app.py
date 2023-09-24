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
    

def fetch12mXAxis():
    #set start and end dates, from JS data. 
    last_year = int(current_year) - 1
    
    prev_12_months = []
    counter = 0 
    for month in timeutils.daterange(DATETIME_NOW, None, step=(0, -1, 0), inclusive=True):
        # convert the list item to human readable format, with strptime(): 
        data_point = month.strftime("%d %b, %Y")
        
        # append the date object into a list of reverse order from current date:
        prev_12_months.append(data_point)
        
        counter += 1 # track data points plotted, to stop populating when 6 reached.
        if counter >= 13:
            prev_12_months.reverse()
            return prev_12_months
    return 


def fetch6mXAxis():
    #set start and end dates, from JS data.     
    prev_6_months = []
    counter = 0 
    # use bolton syntax stepping to create a list of months - 6 items, from current month backwards. 
    for month in timeutils.daterange(DATETIME_NOW, None, step=(0, -1, 0), inclusive=True):
        # convert the list item to human readable format, with strptime(): 
        data_point = month.strftime("%d %b, %Y")
        prev_6_months.append(data_point)
        
        counter += 1 # track data points plotted, to stop populating when 6 reached. 
        if counter >= 6:
            prev_6_months.reverse()
            return prev_6_months
    return 

def fetch3mXAxis():
    """
    Automatically fetch x-axis for 3 month graph, working backwards in 15 day intervals. 
    """
    prev_3_months = []
    counter = 0 
    
    for month in timeutils.daterange(DATETIME_NOW, None, step=(0, 0, -15), inclusive=True):
        data_point = month.strftime("%d %b, %Y") # format iso format into human-readable. 
        prev_3_months.append(data_point)
        
        counter += 1 # track data points plotted, to stop populating when 6 reached. 
        if counter >= 6:
            prev_3_months.reverse()
            return prev_3_months
    return 
   

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
    file_name = "weight_history_log.json"
    weight_history = {}
    archive_file_location = os.path.join(app.config['LOG_ARCHIVE'], file_name)

    #create/overwrite the existing json log file. 
    with open(archive_file_location, 'w', encoding="utf-8") as weight_history_log:
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


    most_recent_date = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable

    #Open and parse target file, creating a python dictionary of {date:weight} 
    drop_columns = ["Time", "Measurement", "Unit", "Comment"]

    filename = f"{file_prefix}{most_recent_date}{file_suffix}"
    print(f"file name restored:{filename}")
    df = pd.read_csv(app.config['WEIGHT_LOG_FOLDER']+filename)

    cleaned_df = df.drop(drop_columns, axis='columns')
    print(cleaned_df)
    parsed_json_output= cleaned_df.to_json(orient='split') #argument to convert output to json string

    with open(archive_file_location, 'w', encoding="utf-8") as weight_history_log:
        weight_history_log.write(json.dumps(parsed_json_output))



    
    #use json.dumps() to convert python object into JSON object -- write this to the file. 


    
    return "Entered process_csv."



if __name__ == "__main__":
    app.run(debug=True)