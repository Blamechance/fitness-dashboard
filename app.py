import os
import datetime
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application - this lets flask know to use the "app.py" file
app = Flask(__name__)

# Disable caching + enable debug/auto reload of page:
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.debug = True

#current time/date: 
currentTimeDate = datetime.datetime.now()

#return the current month as a digit
currentMonth = int(currentTimeDate.strftime("%m"))


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
    tommy_12_month_x = [] #final list of months to pass to Tommy's chart
    monthListDigits = [] #temp buffer to create list of months. 

    #create a list of months in digit form: 
    if currentMonth == 12:
        monthListDigits	= ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

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
            targetMonthText = datetime.date(1, int(monthListDigits[k]), 1).strftime('%B')
            tommy_12_month_x.append(str(targetMonthText))
            
    print("Final month list to pass back for chart rendering: ", tommy_12_month_x)
    return render_template("tommy.html", tommy_12_month_x = tommy_12_month_x) 
        
@app.route('/nathan', methods=["GET", "POST"])
def nathan():
    return render_template("nathan.html") 

@app.route('/raymond', methods=["GET", "POST"])
def raymond():
    return render_template("raymond.html") 


if __name__ == "__main":
    app.run(debug=True)