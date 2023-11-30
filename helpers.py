from functools import wraps
from flask import redirect,redirect, session
import os
from datetime import datetime, date

CURRENT_TIME_DATE = datetime.now()
current_month = int(CURRENT_TIME_DATE.strftime("%m")) # %m prints month as digit
current_year = int(CURRENT_TIME_DATE.strftime("%Y")) #e.g 2013, 2019 etc.
current_day = int(CURRENT_TIME_DATE.strftime("%-d")) #e.g 1, 17, 31 etc. 
last_year = int(current_year) - 1

DATETIME_NOW = date(current_year, current_month, current_day) 


training_submissions_folder = "app_core/all_user_data/training_data_submissions"
weight_submissions_folder = "app_core/all_user_data/weight_data_submissions"
processed_w_data_folder = "app_core/all_user_data/w_log_archive"
processed_t_data_folder = "app_core/all_user_data/training_log_archive"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def select_latest_csv(data_type, username):
    """ This function selects the most recent CSV from the training_logs folder. 
        Since it is used instantly, it should always return the CSV the user intends. 
        Though, appending all uploaded files with the userID would be better logic. 
    """
    if data_type == "WEIGHT_LOG_FOLDER":
        file_prefix = f"/{username}_FitNotes_BodyTracker_Export_" 
        log_dir = weight_submissions_folder


    elif data_type == "TRAINING_LOG_FOLDER":
        file_prefix = f"/{username}_FitNotes_Export_" 
        log_dir = training_submissions_folder 


    input_format = "%Y_%m_%d_%H_%M_%S" 
    output_iso_format = "%Y-%m-%dT%H:%M:%S"
    file_suffix = ".csv"
    date_list = {} 

    #Check for most recent file, in weight log folder, for that user. Use that most recent folder to create JSON string archive file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 

    #NOTE: Wrap in a try-except so the except can delete temp file on error.

    for item in os.listdir(log_dir): 

        # split by underscore, check first element is username: 
        if item.split("_")[0] == username:
            sliced_filename = item[item.index("202"):item.index(".csv")] #index between year and csv (inclusive of year but not csv)
            unformatted_date = datetime.strptime(sliced_filename, input_format)
            iso_date = unformatted_date.strftime(output_iso_format)
            date_list[sliced_filename] = iso_date


    latest_fitnotes_file = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable
    filename = f"{file_prefix}{latest_fitnotes_file}{file_suffix}"
    return filename

def select_latest_JSON(data_type, username):
    date_list = []

    if data_type == "weight":
        log_dir = processed_w_data_folder
        file_prefix = "WeightLog_" 

    elif data_type == "HeaviestPRs":
        log_dir = processed_t_data_folder
        file_prefix = f"HeaviestPRs_" 

    elif data_type == "All_Training_Data":
        log_dir = processed_t_data_folder
        file_prefix = f"All_Training_Data_"

    elif data_type == "SI_PRs":
        log_dir = processed_t_data_folder
        file_prefix = f"SI_PRs_" 

    if not log_dir:
        return "Folder Empty"

    for item in os.listdir(log_dir): 
        file = item.split("_")
        if file[1] == username:
            sliced_filename = item[item.index("202"):] #index between year and csv (inclusive of year but not csv)
            date_list.append(sliced_filename)
    
    if date_list:
        filename = f"{file_prefix}{username}_{str(max(date_list))}"
        return filename
    return False

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







def validate_CSV(file_name, type):
    #Define appropriate CSV headers + byte length for validate function: 
    TRAINING_HEADERS = "Date,Exercise,Category,Weight,Weight Unit,Reps,Distance,Distance Unit,Time,Comment"

    WEIGHT_HEADERS = "Date,Time,Measurement,Value,Unit,Comment"
    T_HEADER_LENGTH = len(TRAINING_HEADERS) #works on logic that chars are one byte
    W_HEADER_LENGTH = len(WEIGHT_HEADERS)
    VALID_EXTENSIONS = ('.csv', '.txt', '.CSV', '.TXT')

    """
    This function checks that the uploaded file is:
     - A text/CSV file
     - of correct header format and length, for the respective chosen file type
     
    """   
    if type == "training": 
        #set location of file: 
        file_location = os.path.join(training_submissions_folder, file_name)
        
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
        file_location = os.path.join(weight_submissions_folder, file_name)
        
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
       