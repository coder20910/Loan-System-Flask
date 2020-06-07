import json
import os
from datetime import datetime
from flask import Flask, render_template, flash, session, request, redirect
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

with open('confing.json', 'r') as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail = Mail(app)
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params["local_uri"]
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params["prod_uri"]

db = SQLAlchemy(app)
Bootstrap(app)
app.config['SECRET_KEY'] = os.urandom(24)


class User(db.Model):
    Account = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(80), nullable=False)
    Mobile = db.Column(db.String(13), nullable=False)
    Name = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(120), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    paid = db.Column(db.Integer, nullable=False)
    remaining = db.Column(db.Integer, nullable=False)


class Send_email(db.Model):
    email = db.Column(db.String(50), primary_key=True)
    sub = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(120), nullable=False)


class Transaction(db.Model):
    Sno = db.Column(db.Integer, primary_key=True, nullable=True)
    Account = db.Column(db.Integer, nullable=False)
    credit = db.Column(db.Integer, nullable=False)
    debit = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(12), nullable=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            session['id'] = request.form.get('account')
            return redirect('/user_account')
    else:
        return redirect('/dashboard')
    return render_template('index.html')


@app.route('/dashboard/', methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_user']:
        posts = User.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if username == params['admin_user'] and userpass == params['admin_pass']:
            session['user'] = username
            return render_template('dashboard.html')
    return render_template('admin_login.html')


@app.route('/add_user/', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        account = request.form.get('account')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Please try again! .', 'danger')
            return render_template('add_user.html')
        ''' Assigning values to the Contact class'''
        entry = User(Account=account, Name=name, Mobile=phone, Email=email,
                     Password=password, paid=0, remaining=0, total=0)
        db.session.add(entry)
        db.session.commit()
        entry1 = Transaction(Account=account, credit=0, debit=0, date=datetime.now())
        db.session.add(entry1)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect('/')
    return render_template('add_user.html')


@app.route('/user_account/', methods=['GET', 'POST'])
def user_account():
    account = session['id']
    exist = db.session.query(db.exists().where(User.Account == account)).scalar()
    if exist:
        user_details = User.query.filter_by(Account=account)

        transactions = Transaction.query.filter_by(Account=int(account)).all()
        return render_template('user_account.html', user_details=user_details, transactions=transactions)
    else:
        flash('User not found. Sorry!', 'danger')
        return render_template('flash.html', message='User not found!')


@app.route('/manipulation/', methods=['GET', 'POST'])
def manipulation():
    if request.method == 'POST':
        account = session['id']
        amount = request.form.get('amount')
        user_details = User.query.filter_by(Account=account).first()

        sender = params['gmail-user']
        if request.form['btn'] == 'credit':
            user_details.total = user_details.total + int(amount)
            user_details.remaining = user_details.total - int(user_details.paid)
            db.session.commit()
            transaction = Transaction(Account=account, credit=amount, debit=0, date=datetime.now())
            db.session.add(transaction)
            db.session.commit()

            mail.send_message(sender=sender,
                              recipients=[user_details.Email],
                              body='Dear '+str(user_details.Name)+' '+amount + ' has been credit to your loan amount!'
                                                                               '\n' + 'Total Loan amount = '
                                   + str(user_details.total) + '\n' + 'Total paid amount = ' + str(user_details.paid) +
                                   '\nRemaining Loan amount = ' + str(user_details.remaining)
                              )
        else:
            user_details.paid = user_details.paid + int(amount)
            user_details.remaining = user_details.total - user_details.paid
            db.session.commit()
            transaction = Transaction(Account=account, credit=0, debit=amount, date=datetime.now())
            db.session.add(transaction)
            db.session.commit()
            mail.send_message(sender=sender,
                              recipients=[user_details.Email],
                              body='Dear '+str(user_details.Name)+' '+amount + ' has been debit from your loan amount!'
                                                                               '\n' + 'Total Loan amount = '
                                   + str(user_details.total) + '\n' + 'Total paid amount = ' + str(user_details.paid) +
                                   '\nRemaining Loan amoutnt = ' + str(user_details.remaining)
                              )
        return redirect('/user_account')
    return render_template('user_account.html')


@app.route('/send_email/', methods=['GET', 'POST'])
def send_email():
    if request.method == 'POST':
        email = request.form.get('email')
        sub = request.form.get('subject')
        message = request.form.get('message')
        ''' Assigning values to the Contact class'''
        print(email, sub, message)
        entry = Send_email(email=email, sub=sub, message=message)
        db.session.add(entry)
        db.session.commit()
        sender = params['gmail-user']
        mail.send_message(sender=sender,
                          recipients=[email],
                          body=message + "\n" + sub
                          )
        flash('Registration successful! Please login.', 'success')
        return redirect('/')
    else:
        flash('Please try again!', 'danger')
    return render_template('send_email.html')


@app.route('/user_list/', methods=['GET', 'POST'])
def user_list():
    posts = User.query.all()
    if posts:
        return render_template('user_list.html', params=params, posts=posts)
    else:
        return render_template('flash.html', message='No user found! Add some user.')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user')
    return redirect('/dashboard')


app.run(debug=True)
