import pandas as pd
import json
import os
from datetime import date, datetime, timedelta

from helpers import select_latest_csv
from flask import session, Blueprint


weight_submissions_folder = 'app_core/all_user_data/weight_data_submissions'
processed_w_data_folder = 'app_core/all_user_data/w_log_archive'



# Define blueprint
weight_processing_bp = Blueprint('weight_processing_bp', __name__)


@weight_processing_bp.route('/blueprints')
def process_weight_log(username):
    """
        This function is called when the user prompts a button on the check-in page of website. 
        - All sheets in the related file directories are processed to pull out relevant data into a  {"date":"weight"} JSON list. 
        - These JSON files will be backed up on the file system to operate as a "snapshot" in the archive folder. 
    """
    filename = select_latest_csv("WEIGHT_LOG_FOLDER", username)
    df = pd.read_csv(weight_submissions_folder+filename)
    drop_columns = ["Time", "Measurement", "Unit", "Comment"]

    # use pandas to extract log entry dates and weights, but only if it's bodyweight data
    df = df.loc[df["Measurement"] == "Bodyweight" ]
    cleaned_df = df.drop(drop_columns, axis='columns')
    parsed_entries_string = cleaned_df.to_json(orient='split') #argument to convert output to json string

    # load that data into a string of dates. 
    log_entry_dates = []
    loaded_entries = json.loads(parsed_entries_string)
    log_entry_data = loaded_entries["data"]

    for item in log_entry_data:
        log_entry_dates.append(item[0])


    # take the last date entry as the most recent one -- create final output file name:
    latest_entry_date = log_entry_dates[len(log_entry_dates)-1]

    output_filename = f"WeightLog_{session['user_id']}_{latest_entry_date}"
    output_filepath = os.path.join(processed_w_data_folder, output_filename)

    with open(output_filepath, 'w', encoding="utf-8") as final_json_output:
        final_json_output.write(parsed_entries_string)
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
    file_location = os.path.join(processed_w_data_folder, filename)  
    
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