"""
Replacement for RUSA ACP brevet time calculator
(see https://rusa.org/octime_acp.html)

"""

import flask
from flask import request
import arrow  # Replacement for datetime, based on moment.js
import acp_times  # Brevet time calculations
import config
import logging
from pymongo import MongoClient
import os
import json

###
# Globals
###
app = flask.Flask(__name__)
CONFIG = config.configuration()
# set up database
client = MongoClient('mongodb://' + os.environ['MONGODB_HOSTNAME'], 27017)
db = client.brevetdb

# a very extraneous helper function to make testing simple
def insert_to_db(proc):
    return db.brevetdb.insert_one(proc)

# helper function
def insert_items(items, num_items):
    # initialize a dictionary, set brev_distance once
    to_insert = {}
    to_insert["brev_distance"] = items['data[dist]']
    to_insert["open_times"] = []
    to_insert["close_times"] = []
    to_insert["kms"] = []
    # setting these to -inf as a placeholder
    currentKm = float('-inf')
    km_test = float('-inf')
    # go through all items, adding them to the arrays in the dictionaries
    for i in range(num_items):
        # if km is blank, don't add the entry
        if items['data[data][' + str(i) + '][km]'] != '':
            to_insert["open_times"].append(items['data[data][' + str(i) + '][open_time]'])
            to_insert["close_times"].append(items['data[data][' + str(i) + '][close_time]'])
            km_test = float(items['data[data][' + str(i) + '][km]'])
            if km_test < 0:
                raise ValueError("Negative distances are not accepted!")
            if km_test <= currentKm:
                raise ValueError("Control checkpoints are not ordered!")
            currentKm = km_test
            to_insert["kms"].append(items['data[data][' + str(i) + '][km]'])

    app.logger.debug(to_insert)
    insert_to_db(to_insert)

###
# Pages
###


@app.route("/")
@app.route("/index")
def index():
    app.logger.debug("Main page entry")
    return flask.render_template('calc.html')

@app.route("/display_db")
def display():
    app.logger.debug("Display page")
    # get the database, process it into a list
    saved = list(db.brevetdb.find())
    app.logger.debug(saved)
    return flask.render_template('display_db.html', saved = saved)


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('404.html'), 404


###############
#
# AJAX request handlers
#   These return JSON, rather than rendering pages.
#
###############
@app.route("/_calc_times")
def _calc_times():
    """
    Calculates open/close times from miles, using rules
    described at https://rusa.org/octime_alg.html.
    Expects one URL-encoded argument, the number of miles.
    """
    app.logger.debug("Got a JSON request")
    km = request.args.get('km', 999, type=float)

    # Get start time and distance
    time = request.args.get('start_time', type=str)
    app.logger.debug("time={}".format(time))
    start_time = arrow.get(time, 'YYYY-MM-DDTHH:mm')
    distance = request.args.get('dist', type=int)
    app.logger.debug(distance)

    app.logger.debug("km={}".format(km))
    app.logger.debug("request.args: {}".format(request.args))

    # Use gathered information to pass to JS
    open_time = acp_times.open_time(km, distance, start_time).format('YYYY-MM-DDTHH:mm')
    close_time = acp_times.close_time(km, distance, start_time).format('YYYY-MM-DDTHH:mm')
    app.logger.debug("open_time = {}".format(open_time))
    app.logger.debug("close_time= {}".format(close_time))
    result = {"open": open_time, "close": close_time}
    return flask.jsonify(result=result)

@app.route("/submit/", methods=["POST"])
def _submit():
    app.logger.debug("In submit function")
    # get the controls from the form
    items = request.form.to_dict()
    app.logger.debug("Length of items to loop = " + str(len(items) // 3))
    # there are 3 variables (open time, close time, km) per control
    # insert items into the database
    num_controls = len(items) // 3
    if num_controls <= 0:
        raise ValueError("No controls were given!")
    insert_items(items, num_controls)
    return flask.jsonify(result=str(items))

#############

app.debug = CONFIG.DEBUG
if app.debug:
    app.logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    print("Opening for global access on port {}".format(CONFIG.PORT))
    app.run(port=CONFIG.PORT, host="0.0.0.0")
