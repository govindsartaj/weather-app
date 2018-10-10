# -*- coding: utf-8 -*-
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import requests


api_url = "https://api.openweathermap.org/data/2.5/weather?appid=711ceca9441156a76f8b3cd74924f2f3&units=metric&q="

app = Flask(__name__)

# Config MySQL

app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER'] ='root'
app.config['MYSQL_PASSWORD'] ='*hidden*'
app.config['MYSQL_DB'] ='weatherapp'
app.config['MYSQL_CURSORCLASS'] ='DictCursor'

# Init MySQL
mysql = MySQL(app)


#check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please log in.')
			return redirect(url_for('login'))
	return wrap


@app.route('/')
def index():
	return render_template('home.html')

class registerForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])	
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm',message='Passwords do not match'),
		])

	confirm = PasswordField('Confirm Password')


@app.route('/sign-up', methods=['GET','POST'])
def signup():
	form = registerForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		# Create cursor
		cur = mysql.connection.cursor()

		cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)", (name, email, username, password))

		# Commit to DB
		mysql.connection.commit()
		# Close connection
		cur.close

		flash('Registered! You can now log in.')

		return redirect(url_for('login'))		


	return render_template('sign-up.html', form=form)

@app.route('/sign-in', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password_candidate = request.form['password']

		# Create cursor
		cur = mysql.connection.cursor()

		# Get user by username
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		if result > 0:
			# get hash
			data = cur.fetchone()
			password = data['password']
			city = data['city']
			#compare passwords
			if sha256_crypt.verify(password_candidate,password):
				# Passed
				session['logged_in'] = True
				session['username'] = username
				session['city'] = city
				msg = 'Logged in!'
				flash(msg)
				if city == None:
					return redirect(url_for('choose_city'))
				else:
					return redirect(url_for('dashboard'))
			else: 
				error = 'Login details incorrect/User not found'
				return render_template('/sign-in.html',error=error)
			#close connection
			cur.close()

		else: 
			error = 'Login details incorrect/User not found'
			return render_template('/sign-in.html',error=error)

	return render_template('/sign-in.html')



@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('Logged out')
	return redirect(url_for('index'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
	city = session['city']
	get_weather(city)
	return render_template('dashboard.html', city=city)


class cityForm(Form):
	city = StringField('City', [validators.Length(min=1, max=50)])


@app.route('/choose-city', methods=['GET', 'POST'])
@is_logged_in
def choose_city():
	form = cityForm(request.form)
	if request.method == 'POST' and form.validate():
		city = form.city.data
		username = session['username']
		#create cursor
		cur = mysql.connection.cursor()
		cur.execute("UPDATE users SET city=%s WHERE username=%s",(city,username))
		session['city'] = city
		# Commit to DB
		mysql.connection.commit()
		flash("City updated to "+ city+"!")
		session.modified = True
		return redirect(url_for('dashboard'))

	return render_template('choose-city.html', form=form)



def get_weather(city):
	final_url = api_url + city 
	json_data = requests.get(final_url).json()
	session['description'] = json_data['weather'][0]['main']
	session['weatherTemp'] = str(int(round(json_data['main']['temp'])))
	session['cityFormatted'] = json_data['name']
	session['country'] = json_data['sys']['country']
	session['weatherTempSymb'] = session['weatherTemp'] + "°C"
	session['temp_max'] = str(int(round(json_data['main']['temp_max'])))
	session['temp_min'] = str(int(round(json_data['main']['temp_min'])))
	session['iconURL'] = "http://openweathermap.org/img/w/"+json_data['weather'][0]['icon']+".png"
	session.modified = True  


if __name__ == '__main__':
	app.secret_key='secret123'
	app.run(host='192.168.2.179')
