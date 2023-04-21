import os
import datetime
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
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

#current time/date: 
currentTimeDate = datetime.datetime.now()

#return the current month as a digit
currentMonth = int(currentTimeDate.strftime("%m")) #%m prints month as digit


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
    #12 months is default graph.     
    x_axis = fetch3mXAxis()
    
    minDate = min(x_axis)
    maxDate = max(x_axis)
    #TODO: event listener functionality to return different datasets based on interaction. 
    
    return render_template("tommy.html", x_axis = x_axis, minDate = minDate, maxDate = maxDate) 
        
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
        monthListDigits	= ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    elif currentMonth < 12:
        lastYrMonths = (12 - currentMonth)

        #create a list counting backwards from current month
        for i in range(currentMonth):
            monthListDigits.insert(0, (currentMonth-i))
            
        #Adding months from last year: 
        for j in range(12, (12- lastYrMonths), -1):
            monthListDigits.insert(0, j)
        
        #Convert the list of digits into their month abbrev. forms
        for k in range(12):
            targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%b')
            last12Months.append(str(targetMonthText))
            
    print("Final month list to pass back for chart rendering: ", last12Months)
    return last12Months

def fetch3mXAxis():
    last3Months = [] #final list of months to pass to Tommy's chart
    monthListDigits = [] #temp buffer to create list of months. 

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
        targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%x')
        last3Months.append(str(targetMonthText))
    
    print("Final month list to pass back for chart rendering: ", last3Months)
    return last3Months
    
    
    
#TODO: Function to average the dataset. Make it universal, so it can average no matter the size of the dataset. 
