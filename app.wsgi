import sys
sys.path.insert(0, '/var/www/fitness-dashboard/')

activate_this = '/home/ec2-user/env/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file.read(), dict(_file_=activate_this))

from app import app as application