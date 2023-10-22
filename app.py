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
app.config['MAX_CONTENT_PATH'] = 50000 # sample files average 20KB. 

#Define appropriate CSV headers + byte length for validate function: 
TRAINING_HEADERS = "Date,Exercise,Category,Weight (kgs),Reps,Distance,Distance Unit,Time,Comment"
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
        print(f"Attempting to call weight graph...")
        target_json_weight_file = find_most_current_weight_file("Tommy") # find the weight archive to load 
        
        # process most current JSON archive file with axis list to find average points to graph. 
        weight_graph_12m_points = json_string_to_weight_plots(x_axis_12, target_json_weight_file)
        weight_graph_6m_points = json_string_to_weight_plots(x_axis_6, target_json_weight_file)
        weight_graph_3m_points = json_string_to_weight_plots(x_axis_3, target_json_weight_file)
        
        print(f"graph points to plot:\n12m:{weight_graph_12m_points}\n6m:{weight_graph_6m_points}\n3m:{weight_graph_3m_points}")
        
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

# Following date functions should be refactored to decrement only before commiting a transaction -- currently it's not atomic. 

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

    #Check for most recent file, in weight log folder. Use that most recent folder to create JSON string archive file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 
    # TODO: Need to integrate username checking logic. 
    weight_logs_directory = os.listdir(app.config['WEIGHT_LOG_FOLDER'])    

    input_format = "%Y_%m_%d_%H_%M_%S" 
    output_iso_format = "%Y-%m-%d"
    file_prefix = "/FitNotes_BodyTracker_Export_" 
    file_suffix = ".csv"
    date_list = {} 


    for item in weight_logs_directory: 
        sliced_filename = item[item.index("202"):item.index(".csv")] #index between year and csv (inclusive of year but not csv)
        unformatted_date = datetime.strptime(sliced_filename, input_format)
        iso_date = unformatted_date.strftime(output_iso_format)
        date_list[sliced_filename] = iso_date


    latest_fitnotes_file = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable

    # TODO: Include logic to parse

    # drop irrelevant columsn in target file, creating a python dictionary of {date:weight} 
    drop_columns = ["Time", "Measurement", "Unit", "Comment"]

    # build file name using the date of the most recent submitted fitnotes sheet
    filename = f"{file_prefix}{latest_fitnotes_file}{file_suffix}"
    df = pd.read_csv(app.config['WEIGHT_LOG_FOLDER']+filename)

    # use pandas to extract log entry dates and weights
    cleaned_df = df.drop(drop_columns, axis='columns')
    parsed_entries_string = cleaned_df.to_json(orient='split') #argument to convert output to json string

    # load that data into a string of dates. 
    loaded_entries = json.loads(parsed_entries_string)
    print(f"loaded_entries type: {type(loaded_entries)}")
    log_entry_data = loaded_entries["data"]
    log_entry_dates = []

    for item in log_entry_data:
        log_entry_dates.append(item[0])
    print(f"{log_entry_dates}")

    # take the last date entry as the most recent one -- create final output file name:
    latest_entry_date = log_entry_dates[len(log_entry_dates)-1]

    output_filename = f"WeightLog_username_{latest_entry_date}"
    output_filepath = os.path.join(app.config['LOG_ARCHIVE'], output_filename)

    with open(output_filepath, 'w', encoding="utf-8") as final_json_output:
        final_json_output.write(parsed_entries_string)
    
    # clean up temp file and return:
    os.remove(temp_file_location)

    return "Entered process_csv."


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
            #print(f"6m debugging - pair: {pair}")
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

        for key, values in input_weight_data.items(): # update prev valid list var, if valid
            if values:
                previous_list = values.copy()
            
            elif not values: # if empty list detected, take previous valid list as estimate. 
                input_weight_data[key] = previous_list.copy()


        # average lists to find final list of values to return:
        print(f"pre-average data: {input_weight_data}")
        for value in input_weight_data.values():                
            average_for_period = sum(value) / len(value)
            output_data.append(round(average_for_period, 2))
        print(f"min_date: {min_date}\naxis: {axis}")
        print(f"output: {output_data}\n\n")
        return output_data
    

              
    # Convert input axis list into a list of datetime objects. 
    
    # have a new list variable [], that while it's graph_points != len(axis):
        # for each dict entry, if date is within (x) days before it, aggregate it. 
        # else if it has no entries before it, check a further (x) days before it, if something is found, average between that super old point and the next point.
        # otherwise, use the closest one in front of it. 

    
    

def find_most_current_weight_file(username):
    """ Takes username as argument, and returns the filename of the most current respective archive file. 
    """

    # formats to use max(), compare dates
    datetime_format = "%Y-%m-%d" 

    print("Entered fetch weight graph.")
    # TODO: Add string input to function for username.  
    # navigate to folder with logs and search for user's most recent weight log.
    archive_folder = os.listdir(app.config['LOG_ARCHIVE'])
    print(f"archive_folder = {archive_folder}")
    
    # Split file name, taking the name and date to check if it's more current, for relevant user. 
    most_current_file = ""
    for item in archive_folder:
        filename_parts = item.split("_")
        extracted_user = filename_parts[1]
        
        #manual assignment for testing: 
        username  = "Tommy"

        # if there is not yet a most current file and this matches user, take it as most current. 
        if extracted_user == username and not most_current_file:
            most_current_file = datetime.strptime(filename_parts[2], datetime_format)
        
        # Compare most current file with the target file, taking the most current:     
        target_file = datetime.strptime(filename_parts[2], datetime_format)
        if extracted_user == username and most_current_file < target_file: 
            most_current_file = target_file
    
    # TODO: Using the max date, rebuild the filename string. 
    most_current_file = f"WeightLog_{username}_{most_current_file.strftime(datetime_format)}"

    print(f"Most current file found is: {most_current_file}")

    return most_current_file 





if __name__ == "__main__":
    app.run(debug=True)