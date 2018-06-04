import datetime

import re
# import logging
from logging.handlers import RotatingFileHandler

import os
from bson import ObjectId
from flask import Flask, redirect, url_for, request, render_template, session, jsonify, json, logging, Response
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from authy.api import AuthyApiClient
from pymongo import MongoClient

# from app import app, api, mongo, bcr
from werkzeug.utils import secure_filename

application = Flask(__name__)
bcr = Bcrypt(application)
# client = MongoClient('localhost', 27017)    #Configure the connection to the database
# db = client.i_Met


application.config['MONGO_DBNAME'] = 'i-met'
application.config['MONGO_URI'] = 'mongodb://Olga:olichka121@ds121289.mlab.com:21289/i-met'
application.config['CONNECT'] = False
application.config['maxPoolsize'] = 1

mongo = PyMongo(application)
application.config.from_object('config')
api = AuthyApiClient(application.config['AUTHY_API_KEY'])
application.secret_key = application.config['SECRET_KEY']

now = datetime.datetime.now()
curr_day = now.day
curr_month = now.month
curr_year = now.year


@application.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', url=url_for('user_cabinet'), name='Кабінет')
    return render_template('index.html', url=url_for('login'), name='Увійти')


@application.route('/login', methods=['POST', 'GET'])
def login():
    if 'user' in session:
        return redirect(url_for('user_cabinet'))
    if request.method == 'POST':
        user = mongo.db.users
        login_user = user.find_one({'email': request.form['email']})
        if login_user:
            if bcr.check_password_hash(login_user['password'], request.form['password']):

                # user.insert({'email': request.form['email'], 'password': hashpass,
                #              'account_num': {'type': {'gas': {'3663434534': {
                #                  'date': {'18': {'04': {'22': '100', '23': '150', '24': '200',
                #                                         '25': '280'}}}}},
                #                  'water': {'3663434534': {
                #                      'date': {'18': {'04': {'22': '150', '23': '100', '24': '180',
                #                                             '25': '140'}}}}}}}})
                session['user'] = request.form['email']
                return redirect(url_for('index'))
            else:
                return "Error"
    return render_template('login-page.html')


@application.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        if request.form['buttons'] == 'sighup':
            users = mongo.db.users
            existing_user = users.find_one({'email': request.form['email']})

            if existing_user is None:
                hashpass = bcr.generate_password_hash(request.form['password']).decode('utf-8')
                users.insert(
                    {'email': request.form['email'], 'password': hashpass,
                     'name': request.form['form-last-name'], 'surname': request.form['form-first-name']})
                return redirect(url_for('index'))

            return 'That email already exists'

    return render_template('signup-page.html')


@application.route('/user', methods=['POST', 'GET'])
def user():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    return render_template('user.html')


@application.route('/user_cabinet', methods=['POST', 'GET'])
def user_cabinet():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    labels = []
    values_gas = []
    # result = []
    data = get_data(session['user'], 'gas', '3663434534', week_par='week')
    for key, value in data.items():
        labels.append(key)
        values_gas.append(value)
    # result.append(values)
    values_water = []
    data = get_data(session['user'], 'water', '3663434534', week_par='week')
    for key, value in data.items():
        values_water.append(value)
    # result.append(values)
    return render_template('user-cabinet.html', values_water=values_water, values_gas=values_gas, labels=labels)


@application.route('/gas', methods=['POST', 'GET'])
def gas():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    labels = []
    values = []
    data = get_data(session['user'], 'gas', '3663434534', week_par='week')
    for key, value in data.items():
        labels.append(key)
        values.append(value)
    return render_template('gas.html', values=values, labels=labels)


@application.route('/water', methods=['POST', 'GET'])
def water():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    labels = []
    values = []
    data = get_data(session['user'], 'water', '3663434534', week_par='week')

    for key, value in data.items():
        labels.append(key)
        values.append(value)
    return render_template('water.html', values=values, labels=labels)


def logout():
    return session.pop('user', None)


@application.route('/meter')
def meter():
    return render_template('meter.html')


@application.route('/check_user', methods=['GET'])
def check_user():
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email')
    password = query_parameters.get('password')

    user = users.find_one({'email': email})
    if user:
        if bcr.check_password_hash(user['password'], password):
            return True
        else:
            return False
    return 'Cannot find this email'


@application.route('/get_data', methods=['GET'])
def get_data(email_par=None, type_par=None, counter_par=None, year_par=None, month_par=None, week_par=None):
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email') or email_par
    type = query_parameters.get('type') or type_par
    counter = query_parameters.get('counter') or counter_par
    user = users.find_one({'email': email})
    if query_parameters.get('week') or week_par:
        # month = user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]
        week = dict()
        if curr_day < 7:
            last_month = user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month - 1)]
            for day in range(len(last_month) - 7 + curr_day, len(last_month)):
                found = re.search("{'(.+)':", str(
                    user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month - 1)][str(day)]))
                if found:
                    week[day] = found.group(1)
            for day in range(1, curr_day + 1):
                found = re.search("{'(.+)':", str(
                    user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)][str(day)]))
                if found:
                    week[day] = found.group(1)

            if (email_par and type_par and counter_par) is not None:
                return dict(week)
            else:
                return json.dumps(dict(week), sort_keys=False)
        else:
            for day in range(curr_day - 6, curr_day + 1):
                found = re.search("{'(.+)':", str(
                    user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)][str(day)]))
                if found:
                    week[day] = found.group(1)

            if (email_par and type_par and counter_par) is not None:
                return week
            else:
                return jsonify(week)
    elif query_parameters.get('month') or month_par:
        month = dict()
        for day in user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]:
            if str(day) != 'month':
                found = re.search("{'(.+)':", str(
                    user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)][str(day)]))
                if found:
                    month[day] = found.group(1)
        if (email_par and type_par and counter_par) is not None:
            return month
        else:
            return json.dumps(month)
    elif query_parameters.get('year') or year_par:
        year = user['account_num']['type'][type][counter]['date'][str(curr_year)]
        month = {month: year[str(month)]['month'] for month in year}
        if (email_par and type_par and counter_par) is not None:
            return dict(month)
        else:
            return jsonify(month)
    return jsonify('Error')


@application.route('/send_photo', methods=['POST'])
def send_photo():
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email')
    type = query_parameters.get('type')
    counter = query_parameters.get('counter')
    photo = query_parameters.get('photo')

    user = users.find_one({'email': email})
    month = 'account_num.type.' + type + '.' + counter + '.date.' + str(curr_year) + '.' + str(curr_month)
    value = '300'
    sum_month = int(
        user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]['month'] or 0) + int(value)
    id = user['_id']
    if query_parameters.get('photo'):
        users.update({
            '_id': ObjectId(id)
        }, {
            '$set': {
                month + ".month": str(sum_month),
                month + '.' + str(curr_day): {
                    str(value): photo
                }
            }
        })
        return jsonify('Success')
    else:
        return jsonify("Error via sending photo")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1]

UPLOAD_FOLDER = 'public-uploads'


@application.route('/photo', methods=['GET', 'POST', 'DELETE'])
def photo():
    f = request.files['image.bmp']
    if f and allowed_file(f.filename):
        absolute_file = os.path.abspath('static' + f.filename)
        filename = secure_filename(absolute_file)
        f.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
        # return Response('Uploaded file successfully', status=200)
    return redirect(url_for('meter'))


@application.route('/get_photo', methods=['POST'])
def get_photo():
    f = request.get_data()
    logging.ERROR(f)
    return Response(status=200)


@application.route('/update_data', methods=['PUT'])
def update_data():
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email')
    user = users.find_one({'email': email})
    return True


if __name__ == '__main__':
    logHandler = RotatingFileHandler('info.log', maxBytes=1000, backupCount=1)

    # set the log handler level
    logHandler.setLevel(logging.DEBUG)

    # set the app logger level
    application.logger.setLevel(logging.DEBUG)

    application.logger.addHandler(logHandler)
    application.run(debug=True)

