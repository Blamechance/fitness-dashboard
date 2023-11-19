import pandas as pd
import os
from helpers import select_latest_csv, select_latest_JSON
from datetime import date, datetime, timedelta
import json

training_submissions_folder = "app_core/all_user_data/training_data_submissions"
weight_submissions_folder = "app_core/all_user_data/weight_data_submissions"
processed_w_data_folder = "app_core/all_user_data/w_log_archive"
processed_t_data_folder = "app_core/all_user_data/training_log_archive"

def process_training_log(username):
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
    
    latest_training_csv = select_latest_csv("TRAINING_LOG_FOLDER", username)
    latest_weight_json = select_latest_JSON("weight", username) 
    latest_weight_archive_location = os.path.join(processed_w_data_folder, latest_weight_json)
    df_format_archive = "%Y-%m-%d"
    drop_columns = ["Distance", "Distance Unit", "Time"]
    
    # Drop all unrelated columns in dataframe + drop any sets of same details within same day + add columns for BW/SI
    df = pd.read_csv(training_submissions_folder+latest_training_csv)
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

    # Save each to /training_tabulator_data
    
    return heaviest_weight_prs, strength_index_prs, all_training_data
    

def fetch_training_table_data(username): 
    """
        Fetchs the training table data and returns it as a JSON object. 
    """
    # empty initialisation in case no data: 
    heaviest_PR_file = []
    all_training_file = []
    SI_PR_file = []

    if not select_latest_JSON("HeaviestPRs", username) == "Folder Empty":
        heaviest_PR_file = select_latest_JSON("HeaviestPRs", username) 
    
    if not select_latest_JSON("All_Training_Data", username) == "Folder Empty":
        all_training_file = select_latest_JSON("All_Training_Data", username) 

    if not select_latest_JSON("SI_PRs", username) == "Folder Empty":
        SI_PR_file = select_latest_JSON("SI_PRs", username)

    file_list = [heaviest_PR_file, all_training_file, SI_PR_file]
    output_lists = []
    
    for file in file_list:
        if file:
            filepath = os.path.join(processed_t_data_folder, file)
    
            with open(filepath, 'r') as open_file:
                output_lists.append(json.load(open_file))
        else:
            output_lists.append([]) # to render an empty list if no training data/respective file was not found
    return output_lists