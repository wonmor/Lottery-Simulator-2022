from email.policy import default
from random import Random
from flask import Blueprint, render_template, request, session, jsonify, current_app
from sqlalchemy import func

import configparser

import logging

import functools

import json

from website.extensions import db

from .models import PlayerCurrency, RandomSet

async_mode = None

# Import the config.cfg file and read the default value (starting point) of the game currency
config = configparser.ConfigParser()

# Get the absolute path of the CFG file by doing os.getcwd() and joining it to config.cfg
cfg_path = 'website/config.cfg'

bp = Blueprint('main', __name__)

# Whether user cookies will be collected or not
cookiesAvail = True

# Read the CFG file
config.read(cfg_path)

# Fix the 'failed to load' error!
try:
    default_count = config.getint("default", "NUM_OF_NUMS")
    default_coins = config.getint("default", "MONEY")
except:
    current_app.logger.debug('CFG file failed to load twice!')


@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        allow_cookies = request.form["allow-cookies"]
        decline_cookies = request.form.get["decline-cookies"]

        session.clear()

        if allow_cookies == 'allow' and decline_cookies != 'decline':
            cookiesAvail = True

        if decline_cookies == 'decline' and allow_cookies != 'allow':
            cookiesAvail = False

    return render_template("home.html")


@bp.route('/about')
def about():
    session.clear()
    return render_template("about.html")


@bp.route('/game', methods=['GET', 'POST'])
def game():
    global player_name
    if request.method == 'POST':
        current_app.logger.debug('trying to get json form...')

        # Get all the user input values from game.js => APP STOPS HERE FOR SOME REASON, FIX IT!
        player_name = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('nickname'))
        # player_range[0] => min value, player_range[1] => max value
        player_range = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('range')).split(' ')
        player_draws = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('draws'))

        current_app.logger.debug('got the json form!')

        current_app.logger.debug('player_name: %s', player_name)
        current_app.logger.debug('player_range: %s', player_range)
        current_app.logger.debug('player_draws: %s', player_draws)

        # Define a random list object (instantiating a class located in models.py)
        random_set = RandomSet(player_range[0], player_range[1], player_draws)

        current_app.logger.debug(random_set)

        # Create a random list by generating arbitrary values
        random_set.generate()
        # Convert the generated random list (Python) into JSON-compatible string, so we can hand it over to game.js
        random_set_result = random_set.current_set
        chances = random_set.chances

        return_value = {'random_set_json': random_set_result,
                        'chances': chances, 'success': True}

        # Return the values in the return_value dictionary to game.js by converting the dict. to JSON
        return jsonify(return_value)

        # INTERACTION BETWEEN JAVASCRIPT AND PYTHON (FLASK) USING AJAX AND JSONIFY: https://ayumitanaka13.medium.com/how-to-use-ajax-with-python-flask-729c0a8e5346
        # HOW PYTHON-JSON CONVERSION WORKS USING THE JSON MODULE: https://www.w3schools.com/python/python_json.asp
    # Clear the session
    # session.clear()

    return render_template("game.html")


@bp.route('/game/guess', methods=['POST'])
def guess():
    global num_of_successes
    if request.method == 'POST':
        guesses = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('guesses'))
        random_set = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('random_set'))

        num_of_successes = 0

        current_app.logger.debug(guesses)
        current_app.logger.debug(random_set)

        for i in range(len(random_set) - 1):
            if guesses[i] == random_set[i]:
                num_of_successes += 1

        # Check if the list that stores user input data matches the computer-generated counterpart... return True if yes, False if not!
        return jsonify({'final_result': True, 'num_of_successes': num_of_successes}) if (functools.reduce(lambda x, y: x and y, map(lambda p, q: p == q, guesses, random_set), True)) and (len(guesses) is len(random_set)) else jsonify({'final_result': False})


@bp.route('/game/leaderboard', methods=['POST'])
def leaderboard():
    global max_coins_list
    if request.method == 'POST':
        # Define lists and variables
        max_coins_list = []
        top_players_list = []
        max_coins_index = 0

        # Store the user's new record in the database
        whether_user_is_correct = json.loads(request.get_json(
            force=False, silent=False, cache=True).get('whether_user_is_correct'))
        if whether_user_is_correct == True:
            player = PlayerCurrency.query.filter_by(name=player_name).first()
            if player is None:
                player = PlayerCurrency(player_name, num_of_successes)
                db.session.add(player)
                db.session.commit()
            else:
                player.successes = num_of_successes
                db.session.commit()
            player.coins = player.add_coin()
            db.session.commit()

        # Rank the leaderboard highest to lowest game currency and print them out
        max_coins = PlayerCurrency.query.order_by(
            PlayerCurrency.coins.desc()).limit(10).all()

        # Deserialize the max_coins
        for max_coin in max_coins:
            max_coins_list.append(max_coin.coins)
            # When there're e.g. two players who have the same amount of coin, the program will append both results into one entry of the list
            top_players_list.append(db.session.query(PlayerCurrency).filter(
                PlayerCurrency.coins == max_coins_list[max_coins_index]).all())
            max_coins_index += 1

        # Return a list of the top ten players who have the most coins...
        return jsonify({'max_coins_list': max_coins_list, 'top_players_list': top_players_list})


# AJAX METHOD: https://ayumitanaka13.medium.com/how-to-use-ajax-with-python-flask-729c0a8e5346

# WHAT IS CURRENT_APP? LINK: https://flask.palletsprojects.com/en/2.0.x/appcontext/
# cd .. // go to the upper directory

# requirements.txt => # pip3 install -r requirements.txt to install the files

# COOKIES => WILL BE USED TO SKIP ENTER THE NAME STAGE IN SETUP!
# ADD DIFFICULY INDICATOR DEPENDING ON THE SCALE OF THE RANGE, AND SEPERATE THE LEADERBOARD BY DIFFICULTY LEVEL (EASY, MODERATE, HARD)

# Comparing two python lists: https://www.journaldev.com/37089/how-to-compare-two-lists-in-python
