#!/bin/bash

var='fixtures/'

if [ "$#" -eq 1 ]
  then
    var="$1"
fi

python manage.py loaddata $var/base_teams.json
python manage.py loaddata $var/base_activities.json 
python manage.py loaddata $var/base_quests.json 
python manage.py loaddata $var/base_help.json 
python manage.py loaddata $var/test_users.json
python manage.py loaddata $var/test_energy_data.json
python manage.py loaddata $var/test_energy_power_meter.json
python manage.py loaddata $var/test_energy_goals.json
python manage.py loaddata $var/test_prizes.json 
# python manage.py loaddata $var/test_badges.json
#python manage.py loaddata $var/test_posts.json