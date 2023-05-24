import os
import datetime
import calendar
import sqlite3
import json

from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash


# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

if __name__ == "__main__":
    app.run(debug=True)

# Disable caching + enable debug/auto reload of page:
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Define path to upload folders
app.config['weight_log_folder'] = 'files/weight_logs'
app.config['training_log_folder'] = 'files/training_logs'

app.config['MAX_CONTENT_PATH'] = 50000 #sample files average 20KB. 



#current time/date: 
currentTimeDate = datetime.datetime.now()

#return the current month as a digit
currentMonth = int(currentTimeDate.strftime("%m")) #%m prints month as digit
currentYear = int(currentTimeDate.strftime("%Y")) #e.g 2013, 2019 etc.
lastYear = currentYear - 1


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
    last12Months = [] #final list of months to pass to Tommy's chart
    monthListDigits = [] #temp buffer to create list of months. 

    #create a list of months in digit form: 
    if currentMonth == 12:
        monthListDigits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    
    elif currentMonth < 12:
        lastYrMonths = (12 - currentMonth)

        #create a list counting backwards from current month
        for i in range(currentMonth):
            monthListDigits.insert(0, (currentMonth - i))
            
        #Adding months from last year: 
        for j in range(12, (12 - lastYrMonths), -1):
            monthListDigits.insert(0, j)
        
        #Convert the list of digits into their month abbrev. forms
    for k in range(lastYrMonths):
        targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%b')
        last12Months.append(str(targetMonthText) + " " + str(lastYear))
                
    for m in range(currentMonth):
        targetMonthText = datetime.date(currentYear, int(monthListDigits[lastYrMonths+m]), 1).strftime('%b')
        last12Months.append(str(targetMonthText) + " " + str(currentYear))
            
    return last12Months

def fetch6mXAxis():
    last6Months = [] #final list of months to pass to Tommy's chart
    monthListDigits = [] #temp buffer to create list of months.     
    
    if currentMonth < 6:
        lastYrMonths = (6 - currentMonth)

    #create a list of months in digit form: 
    if currentMonth >= 6:
        for i in range(7):
            monthListDigits.insert(0, (currentMonth-i))
            
    elif currentMonth < 6:
        lastYrMonths = (6 - currentMonth)

        #create a list counting backwards from current month
        for i in range(currentMonth):
            monthListDigits.insert(0, (currentMonth-i))
                
        #Adding months from last year:
        for j in range(12, (12 - lastYrMonths), -1):
            monthListDigits.insert(0, j)
            
    #Convert the list of digits into their month abbrev. forms
    #prev months first: 
    for k in range(lastYrMonths):
        targetMonthText = datetime.date(lastYear, int(monthListDigits[k]), 1).strftime("%d %b, %Y")
        last6Months.append(str(targetMonthText))

        targetMonthText = datetime.date(lastYear, int(monthListDigits[k]), 15).strftime("%d %b, %Y")
        last6Months.append(str(targetMonthText))

                
    for m in range(lastYrMonths, 6, 1):
        targetMonthText = datetime.date(1, int(monthListDigits[m]), 1).strftime('%b')
        
        targetMonthText = datetime.date(currentYear, int(monthListDigits[m]), 1).strftime("%d %b, %Y")
        last6Months.append(str(targetMonthText))

        targetMonthText = datetime.date(currentYear, int(monthListDigits[m]), 15).strftime("%d %b, %Y")
        last6Months.append(str(targetMonthText))
            
    return last6Months
    
def fetch3mXAxis():
    last3Months = [] #final list of months to pass to Tommy's chart
    monthListDigits = [] #temp buffer to create list of months.     
    
    if currentMonth < 3:
        lastYrMonths = (3 - currentMonth)

    #create a list of months in digit form: 
    if currentMonth >= 3:
        for i in range(4):
            monthListDigits.insert(0, (currentMonth-i))
            
    elif currentMonth < 3:
        lastYrMonths = (3 - currentMonth)

        #create a list counting backwards from current month
        for i in range(currentMonth):
            monthListDigits.insert(0, (currentMonth-i))
            
        #Adding months from last year: 
        for j in range(12, (12 - lastYrMonths), -1):
            monthListDigits.insert(0, j)
        
    #Convert the list of digits into their month abbrev. forms
    for k in range(3):
        #code to change montListDigits to have the full correct date incl. year:
        #if month is Dec or Nov, it's from last year: 
        if monthListDigits[k] >= 11: 
            targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%b')
            last3Months.append(str(targetMonthText) + " 01, " + str(lastYear))
            last3Months.append(str(targetMonthText) + " 15, " + str(lastYear))

        else: 
            targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%b')
            last3Months.append(str(targetMonthText) + " 01, " + str(currentYear))
            last3Months.append(str(targetMonthText) + " 15, " + str(currentYear))
            
    return last3Months

@app.route('/volume_analysis', methods=["POST"])
def volume_analysis():
    print("Entered volume_analysis.")
    target_period = request.get_json("userPeriod") #this is not fetching the option properly.... 
    print("volume_analysis print of target_period: ", target_period)
    return jsonify(target_period)

@app.route('/upload', methods=['POST'])
def upload():
    print("Entered upload function. ") 
    #file = request.files[]
    return render_template("upload-success.html") #have return statement to a "success" page. 
    

@app.route('/validate_csv_format', methods=["POST"])
def validate_csv_format():
    print("Entered validate_csv_format. ")

    #Received object with form data is a list-like structure (immutable dict): 
    submission_type = request.form.getlist("uploadType")[0]
    print("File type: ", submission_type)
    
    if submission_type is None : # null check -- using string literal as JSON "none" was received
        print("Error: Form submission type not selected.")
        return False
    
    if submission_type == "training":
        print("Detected Training file")
        
    
    # Detect weight file and call processing function
    if submission_type == "weight":
        print("Detected Weight file... uploading.")
        
        uploaded_file = request.files['userUpload']
        filename = uploaded_file.filename
        print("File name: ", filename)
        
        #save to files folder -- extend this logic to ensure no duplicates: 
        uploaded_file.save(os.path.join(app.config['weight_log_folder'], filename))
        return "Success"

    
    #python/dictionary -> JS/JSON
    dummyData = {
        "log":"Training Log",
        "Excercise":"Flat Barbell Bench",
         "Sets": 4,
         "reps": 8        
    } 
    return json.dumps(dummyData) #JSON format 



def process_weight_log():
    """
        This function takes in the submitted weight excel sheet, processes and formats it to {"date":"weight"} JSON list. 
        This data will then be checked against the SQL database - any data points that do not exist as entries in the DB will be created.        
    """
    
    
    return "Entered process_csv."