# ----------------------------------------
# facebook authentication
# ----------------------------------------

from flask import url_for, request, session, redirect, Flask
from flask_oauth import OAuth

app = Flask(__name__)

FACEBOOK_APP_ID = '922347824609466'
FACEBOOK_APP_SECRET = '0e5011c419fbf62d851dd33eac477a68'

oauth = OAuth()

facebook = oauth.remote_app('facebook',
                            base_url='https://graph.facebook.com/',
                            request_token_url=None,
                            access_token_url='/oauth/access_token',
                            authorize_url='https://www.facebook.com/dialog/oauth',
                            consumer_key=FACEBOOK_APP_ID,
                            consumer_secret=FACEBOOK_APP_SECRET,
                            request_token_params={'scope': ('email, ')}
                            )


@facebook.tokengetter
def get_facebook_token():
    return session.get('facebook_token')


def pop_login_session():
    session.pop('logged_in', None)
    session.pop('facebook_token', None)


@app.route("/facebook_login")
def facebook_login():
    return facebook.authorize(callback=url_for('facebook_authorized',
                                               next=request.args.get('next'), _external=True))


@app.route("/facebook_authorized")
@facebook.authorized_handler
def facebook_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None or 'access_token' not in resp:
        return redirect(next_url)

    session['logged_in'] = True
    session['facebook_token'] = (resp['access_token'], '')

    return redirect(next_url)


@app.route("/logout")
def logout2():
    pop_login_session()
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.config.from_object('config')
    app.secret_key = app.config['SECRET_KEY']
    app.run(debug=True)
