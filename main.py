import datetime
from flask import Flask, redirect, url_for, request, render_template, session, jsonify, json
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from authy.api import AuthyApiClient
from pymongo import MongoClient

# from app import app, api, mongo, bcr

application = Flask(__name__)
bcr = Bcrypt(application)
# client = MongoClient('localhost', 27017)    #Configure the connection to the database
# db = client.i_Met


application.config['MONGO_DBNAME'] = 'i-met'
application.config['MONGO_URI'] = 'mongodb://Olga:olichka121@ds121289.mlab.com:21289/i-met'

mongo = PyMongo(application)
application.config.from_object('config')
api = AuthyApiClient(application.config['AUTHY_API_KEY'])
application.secret_key = application.config['SECRET_KEY']

now = datetime.datetime.now()
curr_day = now.day
curr_month = now.month
curr_year = now.year


@application.route('/check', methods=["GET", "POST"])
def check():
    if request.method == "POST":
        # country_code = request.form.get("country_code")
        phone_number = request.form['phone-number']

        # session['country_code'] = country_code
        session['phone_number'] = phone_number

        api.phones.verification_start(phone_number, '+380', via='sms')

        return redirect(url_for("verify"))
    return render_template('before registration.html')


@application.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        token = request.form.get("form-username")

        phone_number = session.get("phone_number")
        # country_code = session.get("country_code")

        verification = api.phones.verification_check(phone_number, '+380', token)

        if verification.ok():
            return redirect(url_for('register'))

    return render_template('afterregistration.html')


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
        if request.form['buttons'] == 'start':
            return render_template('signup-page.html')

        elif request.form['buttons'] == 'sigh_up':
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
    values = []
    result = []
    data = get_data(session['user'], 'gas', '3663434534', month_par='month')
    for key, value in data.items():
        labels.append(key)
        values.append(value)
    result.append(values)
    values = []
    data = get_data(session['user'], 'water', '3663434534', month_par='month')
    for key, value in data.items():
        values.append(value)
    result.append(values)
    return render_template('user-cabinet.html', values=result, labels=labels)


@application.route('/gas', methods=['POST', 'GET'])
def gas():
    if request.method == 'POST':
        if request.form['exit'] == 'exit':
            logout()
            return redirect(url_for('index'))
    labels = []
    values = []
    data = get_data(session['user'], 'gas', '3663434534', month_par='month')
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
    data = get_data(session['user'], 'water', '3663434534', month_par='month')

    for key, value in data.items():
        labels.append(key)
        values.append(value)
    return render_template('water.html', values=values, labels=labels)


def logout():
    return session.pop('user', None)


@application.route('/chart')
def chart():
    if 'user' in session:
        users = mongo.db.users
        user = users.find_one({'email': 'user'})
        labels = user['days']
        values = user['days']
        return render_template('chart.html', values=values, labels=labels)


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
        month = user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]
        if curr_day < 7:
            last_month = user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month - 1)]
            month = user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)]
            week = [(day, last_month[str(day)]) for day in range(len(last_month) - 7 + curr_day, len(last_month))]
            for day in range(1, curr_day + 1):
                week.append((day, month[str(day)]))

            if (email_par and type_par and counter_par) is not None:
                return dict(week)
            else:
                return json.dumps(dict(week), sort_keys=False)
        else:
            week = {day: month[str(day)] for day in range(curr_day - 6, curr_day + 1)}
            if (email_par and type_par and counter_par) is not None:
                return week
            else:
                return jsonify(week)
    elif query_parameters.get('month') or month_par:
        month = {day: user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)][str(day)] for
                 day in user['account_num']['type'][type][counter]['date'][str(curr_year)][str(curr_month)] if
                 str(day) != 'month'}
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


@application.route('/update_data', methods=['PUT'])
def update_data():
    users = mongo.db.users
    query_parameters = request.args

    email = query_parameters.get('email')
    user = users.find_one({'email': email})
    return True

@application.route('/devices', methods=['GET'])
def get_all_devices():
  users = mongo.db.users
  output = []
  for s in users.find():
    output.append({'email' : s['email'], 'account_num' : s['account_num']})
  return jsonify({'user devices' : output})

@application.route('/devices/<email>', methods=['GET'])
def get_one_device(email):
  users = mongo.db.users
  s = users.find_one({'email' : email})
  if s:
    output = {'email' : s['email'], 'account_num' : s['account_num']}
  else:
    output = "No such email"
  return jsonify({'user devices' : output})


if __name__ == '__main__':
    application.run(debug=True)
