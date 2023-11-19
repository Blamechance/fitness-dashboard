from functools import wraps
from flask import redirect,redirect, session
import os
from datetime import datetime

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



    #Check for most recent file, in weight log folder. Use that most recent folder to create JSON string archive file:
    # 1. Slice date sections of all filenames in directory. 
    # 2. Convert to datetime compatible for comparison with max()
    # Once max file found, save it's name. 

    #NOTE: Wrap in a try-except so the except can delete temp file on error.

    for item in os.listdir(log_dir): 
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
        sliced_filename = item[item.index("202"):] #index between year and csv (inclusive of year but not csv)
        date_list.append(sliced_filename)
    
    filename = f"{file_prefix}{username}_{str(max(date_list))}"
    return filename
