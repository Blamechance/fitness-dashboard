from functools import wraps
from flask import redirect, url_for, redirect, render_template, request, session, current_app
import os

processed_weight_folder = current_app.config['LOG_ARCHIVE'] 
processed_training_folder = current_app.config['PROCESSED_TRAINING_DATA'] # tabulator table data for heaviest PRs

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def select_latest_csv(data_type):
    """ This function selects the most recent CSV from the training_logs folder. 
        Since it is used instantly, it should always return the CSV the user intends. 
        Though, appending all uploaded files with the userID would be better logic. 
    """
    log_dir = os.listdir(current_app.config[f"{data_type}"])    
    input_format = "%Y_%m_%d_%H_%M_%S" 
    output_iso_format = "%Y-%m-%dT%H:%M:%S"
    file_suffix = ".csv"
    date_list = {} 

    if data_type == "WEIGHT_LOG_FOLDER":
        file_prefix = f"/{session['user_id']}_FitNotes_BodyTracker_Export_" 

    elif data_type == "TRAINING_LOG_FOLDER":
        file_prefix = f"/{session['user_id']}_FitNotes_Export_" 


    #Check for most recent file, in weight log folder. Use that most recent folder to create JSON string archive file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 

    #NOTE: Wrap in a try-except so the except can delete temp file on error.

    for item in log_dir: 
        sliced_filename = item[item.index("202"):item.index(".csv")] #index between year and csv (inclusive of year but not csv)
        unformatted_date = datetime.strptime(sliced_filename, input_format)
        iso_date = unformatted_date.strftime(output_iso_format)
        date_list[sliced_filename] = iso_date


    latest_fitnotes_file = str(max(date_list)) # use value (date in iso) for max, but pass in the key (date in file's format) to variable
    filename = f"{file_prefix}{latest_fitnotes_file}{file_suffix}"
    return filename

def select_latest_JSON(data_type):
    date_list = []

    if data_type == "weight":
        log_dir = os.listdir(processed_weight_folder)
        file_prefix = "WeightLog_" 

    elif data_type == "HeaviestPRs":
        log_dir = os.listdir(processed_training_folder)
        file_prefix = f"HeaviestPRs_" 

    elif data_type == "All_Training_Data":
        log_dir = os.listdir(processed_training_folder)
        file_prefix = f"All_Training_Data_"

    elif data_type == "SI_PRs":
        log_dir = os.listdir(processed_training_folder)
        file_prefix = f"SI_PRs_" 

    if not log_dir:
        return "Folder Empty"

    for item in log_dir: 
        sliced_filename = item[item.index("202"):] #index between year and csv (inclusive of year but not csv)
        date_list.append(sliced_filename)
    
    filename = f"{file_prefix}{session['user_id']}_{str(max(date_list))}"
    return filename