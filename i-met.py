import datetime
import boto3, botocore

import re
import logging
from logging.handlers import RotatingFileHandler

from bson import ObjectId
from flask import Flask, redirect, url_for, request, render_template, session, jsonify, json, Response
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from authy.api import AuthyApiClient
from pymongo import MongoClient

# from app import app, api, mongo, bcr

app = Flask(__name__)
bcr = Bcrypt(app)
# client = MongoClient('localhost', 27017)    #Configure the connection to the database
# db = client.i_Met

app.config['JSON_SORT_KEYS'] = False

app.config['MONGO_DBNAME'] = 'i-met'
app.config['MONGO_URI'] = 'mongodb://Olga:olichka121@ds121289.mlab.com:21289/i-met'
app.config['CONNECT'] = False
app.config['maxPoolsize'] = 1

mongo = PyMongo(app)
app.config.from_object('config')
api = AuthyApiClient(app.config['AUTHY_API_KEY'])
app.secret_key = app.config['SECRET_KEY']

now = datetime.datetime.now()
curr_day = now.day
curr_month = now.month
curr_year = now.year


@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', url=url_for('user_cabinet'), name='Кабінет')
    return render_template('index.html', url=url_for('login'), name='Увійти')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'user' in session:
        return redirect(url_for('user_cabinet'))
    if request.method == 'POST':
        user = mongo.db.users
        login_user = user.find_one({'email': request.form['email']})
        if login_user:
            if bcr.check_password_hash(login_user['password'], request.form['password']):
                session['user'] = request.form['email']
                return redirect(url_for('index'))
            else:
                return "Error"
    return render_template('login-page.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'email': request.form['email']})

        if existing_user is None:
            hashpass = bcr.generate_password_hash(request.form['password'])
            users.insert(
                {'email': request.form['email'], 'password': hashpass, 'name': request.form['first-name'],
                 'surname': request.form['last-name'], 'phone': request.form['phone'], 'account_num':
                     {'type': {request.form['type']: {request.form['counter-name']: {'date': {str(curr_year):
                      {str(curr_month): {'month': '', str(curr_day): {}}}}}}}}})
            return redirect(url_for('index'))

        return 'That email already exists'

    return render_template('signup-page.html')


@app.route('/user', methods=['POST', 'GET'])
def user():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    return render_template('user.html')


@app.route('/user_cabinet', methods=['POST', 'GET'])
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


@app.route('/gas', methods=['POST', 'GET'])
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


@app.route('/water', methods=['POST', 'GET'])
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


@app.route('/check_user', methods=['GET'])
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


@app.route('/get_data', methods=['GET'])
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
            return jsonify(month)
    elif query_parameters.get('year') or year_par:
        year = user['account_num']['type'][type][counter]['date'][str(curr_year)]
        month = {month: year[str(month)]['month'] for month in year}
        if (email_par and type_par and counter_par) is not None:
            return dict(month)
        else:
            return jsonify(month)
    return jsonify('Error')


@app.route('/send_photo', methods=['POST'])
def send_photo():
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email')
    type = query_parameters.get('type')
    counter = query_parameters.get('counter')

    user = users.find_one({'email': email})
    month = 'account_num.type.' + type + '.' + counter + '.date.' + str(curr_year) + '.' + str(curr_month)
    value = '270'

    from config import S3_KEY, S3_SECRET, S3_BUCKET

    S3_LOCATION = str(email) + '/' + str(type) + '/' + str(counter) + '/'
    s3 = boto3.resource('s3', aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
    s3.Object(S3_BUCKET, S3_LOCATION + str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '.bmp').put(Body=request.data, ACL="public-read")

    id = user['_id']
    users.update({
            '_id': ObjectId(id)
        }, {
            '$set': {
                month + '.' + str(curr_day): {
                    str(value): 'https://' + S3_BUCKET + '.s3.amazonaws.com/' + S3_LOCATION + str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '.bmp'
                }
            }
        })
    return Response('Uploaded file successfully', status=200)


@app.route('/get_photo', methods=['GET'])
def get_photo():
    # sum_month = int(
    #     user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]['month'] or 0) + int(value)
    # id = user['_id']
    # if query_parameters.get('photo'):
    #     users.update({
    #         '_id': ObjectId(id)
    #     }, {
    #         '$set': {
    #             month + ".month": str(sum_month),
    #             month + '.' + str(curr_day): {
    #                 str(value): request.data
    #             }
    #         }
    #     })

        import io
        import requests
        from PIL import Image

        response = requests.get('https://i-met.s3.amazonaws.com/alex@gmail.com/gas/3663434534/2018-9-29.bmp')
        image = Image.open(io.BytesIO(response.content))
        image.save("image.bmp")

        return jsonify('Success')

	
@app.route('/meter')
def meter():
    return render_template('meter.html')


@app.route('/update_data', methods=['PUT'])
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
    app.logger.setLevel(logging.DEBUG)

    app.logger.addHandler(logHandler)
    app.run(debug=True)
