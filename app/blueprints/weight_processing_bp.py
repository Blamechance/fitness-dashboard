import pandas as pd
import json
import os

from ...helpers import select_latest_csv
from flask import session, Blueprint


weight_submissions_folder = 'app/all_user_data/weight_data_submissions'
processed_w_data_folder = 'app/all_user_data/w_log_archive'



# Define blueprint
weight_processing_bp = Blueprint(
    'weight_processing_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@weight_processing_bp.route('/blueprints')
def process_weight_log():
    """
        This function is called when the user prompts a button on the check-in page of website. 
        - All sheets in the related file directories are processed to pull out relevant data into a  {"date":"weight"} JSON list. 
        - These JSON files will be backed up on the file system to operate as a "snapshot" in the archive folder. 
    """
    filename = select_latest_csv("WEIGHT_LOG_FOLDER")
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
    print(f"Output file path in weight is: {output_filepath}")

    with open(output_filepath, 'w', encoding="utf-8") as final_json_output:
        final_json_output.write(parsed_entries_string)
    return "Entered process_csv."