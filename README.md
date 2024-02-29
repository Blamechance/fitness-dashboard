# Fitness Dashboard
## Video Demo:
https://youtu.be/Np4lORlm-Y0

## Concept: 
My friends and I have been using the [FitNotes mobile app](https://play.google.com/store/apps/details?id=com.github.jamesgay.fitnotes&hl=en_US) to recording our weightlifting training data for years now, but the app is mostly for personal use, and so the information is not easily shared or visible to each other.

Features include:
- Line graph visualisations of weight data trends over 3, 6 and 12 months. 
- Transforms Training Data to include weight data, and custom *Strength Index* scores. 
- Fully-featured tables that include sorting filters, to summarise the user's heaviest weight PRs, and highest *strength index* PRs as well as instant record searching. 
- Server-side saving of processed data and raw CSV submissions, as FitNotes has no fleshed out back-up function beyond exports. 

In future, I plan to add more functions to supplement our fitness journeys, such as a TDEE calculator and a Bulk/Cut Diet Planning Calculator. 

## Directories:
The significant items in the root directory of the project are:
##### app_core:
This folder contains blueprints and `.py` helper files that make up the majority of the processing logic of the project. 

`all_user_data`:
ser file submissions, and the subsequent processed file results are saved in separate folders here, split as per:
- **training_data_submissions** (raw csv). 
- **weight_data_submissions** (raw csv). 
- **w_log_archive** (JSON strings).
- **training_log_archive** (JSON strings).
	- Each raw CSV submission creates 3 different products of processed data, appended by the user's name. 
	- These files are formatted to be expected input formats to utilised libraries  such as `tabulator` and `chart.js`. The functions will  search the directories for the most up-to-date file for that user, before loading it to the page. 
		- e.g `All-Training-Data_Tommy_2024-02-06` 

`blueprints`:
This folder contains the 2 main submission processing logic `.py` files. The logic flow will be explained further down below. 
- `training_processing_bp.py`
- `weight_processing_bp.py`

##### flask_session: 
This is from a flask module to enable the facilitating of user sessions, through client-side cookie interaction. 

##### static:
This directory contains the main `styles.css` file, as well as favicons for the site. 

##### templates:
Here is contained all the HTML pages for the website, as accessible through the navbar. `layout.html` is the template which is used by the other pages, to extend the consistent elements to (navbar, JavaScript code linking etc). 

##### requirements.txt:
This is where all the modules were captured to, with `pip freeze`. 



## Logic/Implementation Explanation: 
### User Accounts Database: 
- User account/sign in data is stored within the `users.db` file, interacted with through an implementation of `SQLite` and `SQLAlchemy`.
	- Initially, the simplistic design of DB cursors was considered, but coding the literal string queries was not intuitive to read or maintain. 
	- `SQLAlchemy` was implemented instead, which provides DB engine functionality, which improves efficiency by creating a single "session" for which the app can programatically engage when requiring database interaction, as opposed to create a cursor each time. 
	- This is significantly more efficient, as the overhead to constantly creating and destroying cursor connections is eliminated. 
- Username strings's will be converted with `.lower()`, before being saved to `users.db`. 
- Passwords are **hashed**, before storing them in the DB -- this is done through the `werkzeug` module. 

### Shared Submission Functions:
`validateCSV()`: 
- This is client-side functionality written as a HTML script. Data is validated to catch:
	- Empty CSV files/no file attached to form. 
	- CSV files that do not adhere to the expected headers, as per the FitNotes app's export files. 
	- Checking if the correct data field was selected, for the file type submitted (i.e not clicking weight data submission, with a weight data file). 

`/upload`:
- This function is server-side, accessed through Flask's app routing mechanic (mapping URLs to functions), saving the file to the server to run validation functions it . 
- This function validates whether: 
	- The submitted file is a `.csv`,`plaintext` or`.txt` file. 
	- The filename is appended with the user's username. 
	- Whether the column headers are within expected format, consistent with the FitNotes Export function. This is done through the `validate_CSV()` function in `helpers.py`. 
- If these conditions pass, then  `process_weight_log()` is called, and a success code/message is returned to the client on completion.
- Otherwise, the file is cleaned up from the system with `os.remove()` and an error message is returned to the client, leaving no trace of the failed submission. 

### Weight Data Submission:

#### Basic Logic Flow
1. When the form in`checkin.html` is submitted with the `weight log` field, the `onsubmit=""` function will first be called, to validate whether the user indeed attached a CSV file, and that it is not empty. 

2. If these conditions are present, then the form proceeds to make an asynchronous ajax call to the  `/upload` flask route, which runs further file validation functionality server-side.
	- If the file is as expected, then `process_weight_log()` will be called to produce the processed JSON data for site functions, using the input file. 

3. The client window will then wait to receive either a **success** or **error/failed** screen, to represent whether the submission is valid, uploaded and ready for viewing on the site; or whether it was invalid and subsequently disposed of. 

#### Functions: 
`/process_weight_log`: 
- First, the `select_latest_csv` helper function is called to parse the relevant directory to select the most recent submission (as per the timestamp included in filename, as FitNotes provides it), belonging to that user. 
	- This avoids updating the user's statistics with older data, even if it's uploaded out of order. 
- The `pandas` module is then used to load the CSV file into a `dataframe`.
	- Irrelevant columns such as "Time" and "Unit" is dropped .
	- Each row's date and weight data is extracted as `key-value` pairs, saved as a `JSON string` data structure.
	- The filename is taken from the most recent weight entry, e.g `WeightLog_Tommy_2023-11-15`. 
- If this entire process succeeds without failure due to invalid fields, then a success code is returned, which then triggers the `upload` function to pass a success alert message to the client's browser. 



### Training Data Submissions:
#### Basic Logic Flow:
Similar to weight submissions, the `process_training_log()` function is called as part of the submission form's `action`, after passing the basic `onsubmit()` empty file check. 

1. Each row is iterated over using  `panda`'s `.iterrows()` to first:
	- **Produce a dict containing all the training data** -- this is eventually saved as it's own `All-Training-Data-user-timestamp` JSON file.
	- All `NaN` datatypes due to empty fields are applied with the `N/A` string instead, for compatible representation with `tabulator`. 

2. If a **processed weight JSON** file is available for the user (found for user within `.../w_log_archive`) , it will also make use of that data to create *strength index values* (calling `calculate_SI()`) and append it to the dataframe.
	- This is a custom formula which takes into account the user's weight, and the rep range of the exercises set to develop a relative strength index score.
	- Weight records recorded within +/- 3 days of the date the exercises was executed are averaged to a single value, and then utilised for formula purposes. 
	- The intention, is to allow users to compare strength feats, even if the context of data contains varying *reps*, *bodyweight* and *exercise weight*. 
	- If no weight data is available, the `strength index` field for that row will be left blank. 
	- The algorithim is a basic `O(n)`, `if x in y` test between all weight entries and all exercise entries. 

3. A second iteration is made over the `dict` created in step 1, now filtering/copying relevant records into two other `dicts`:
	- These are used to preload different table data on the dashboard. 
	- Algorithm is also `O(n)`, though a single pass will be used to produce the required 2 output results. 
	- Highest Weight PR dict:
		- Tracks the highest weight lifted, for each exercise. Substitutes heavier records during iterations to come to a single dict containing only the heaviest lifts of each exercise (Personal bests). 
	- Strength Index PR dict:
		- Similar implementation as above, but instead tracks strength index scores. 

4. Each of these 3 data structures are then output and saved as JSON files, to be used by the dashboard elements:
	Namely:
	- `All-Training-Data_user_2024-02-06`
	- `Heaviest-PRs_user_2024-02-06`
	- `SI-PRs_user_2024-02-06`

#### Functions: 
`calculate_SI`
The Strength Index (SI) is a custom formula designed to measure the strength feat of an exercise set, reagardless of fluctuating context (bodyweight, reps executed etc). 
* This weight value is the average of all available weight data, within a 7 day proximity window (3 days on either side + the date).
* **Formula:** 
```py
[ Reps x weight ] / [ bodyweight(kg) x RR Factor* ]
```
- RR factors:

| Reps Range | Scaling Factor                                |
| ---------- | --------------------------------------------- |
| 1-2 reps   | 3.3                                           |
| 3-6 reps   | 1.4                                           |
| 7-10 reps  | 1 (normal)                                    |
| 11-15 reps | 0.8                                           |
| 16+ reps   | None (don't calculate due to obvious skewing) |

## Dashboard Explanation: 
### Modules: 
- **Chart.js:** JavaScript library used to create the line graph.
- **Tabulator:** JavaScript library used to create interactive tables, storing the training data.
### Data Flow: 
1. From the submission/processing functions, JSON files are ready on the server. 
2. This data is passed to the HTML template using `Jinja` templating.
3. JavaScript is then used to substitute this data into the options for `tabulator` and `chart.js`
	- This allows for the client to load and switch between datasets dynamically without making server requests, after they fully load page the first time. 

### Elements: 
- **Weight Graph:** 
	- Displays a line graph of the user's weight over different time periods (3 months, 6 months, 12 months).
	- Users can switch between these periods using buttons.  
- **Sorted Training Data Tables:**
	- Shows the all the user's exercise records in an interactive table. Views can be switched to show:
		- User's heaviest weight PRs for each exercise;
		- User's highest *Strength Index* scoring lifts.
	- Users can switch between these two datasets using buttons.
	- Each row includes information including exercise name, reps, date achieved, body weight, and comments.
- **All Training Data Table**:
	- Includes similar context information as mentioned above, but displays ALL their training data. 
	- Still enjoys benefit of cross-referenced and appended weight data, to each lift record. 



## Other Design notes: 
### Metric System Measurement Support Only: 
- This decision to forgot Imperial measurements is heavily reliant on the target user being local friends who all use the **Metric System**. 
	- With that said, in the fringe event someone is using the imperial system, they can change the setting in their app and upload again with records in metric system. 