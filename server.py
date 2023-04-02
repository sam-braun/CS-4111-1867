
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.73.36.248/project1
#
# For example, if you had username zy2431 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://zy2431:123123@34.73.36.248/project1"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "coman.andrei"
DATABASE_PASSWRD = "7901"
DATABASE_HOST = "34.148.107.47" # change to 34.28.53.86 if you used database 2 for part 2
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/project1"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
with engine.connect() as conn:
	create_table_command = """
	CREATE TABLE IF NOT EXISTS test (
		id serial,
		name text
	)
	"""
	res = conn.execute(text(create_table_command))
	insert_table_command = """INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')"""
	res = conn.execute(text(insert_table_command))
	# you need to commit for create, insert, update queries to reflect
	conn.commit()


@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
	"""
	request is a special object that Flask provides to access web request information:

	request.method:   "GET" or "POST"
	request.form:     if the browser submitted a form, this contains the data in the form
	request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

	See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
	"""

	# DEBUG: this is debugging code to see what request looks like
	print(request.args)


	#
	# example of a database query
	#
	select_query = "SELECT name from test"
	cursor = g.conn.execute(text(select_query))
	names = []
	for result in cursor:
		names.append(result[0])
	cursor.close()

	#
	# Flask uses Jinja templates, which is an extension to HTML where you can
	# pass data to a template and dynamically generate HTML based on the data
	# (you can think of it as simple PHP)
	# documentation: https://realpython.com/primer-on-jinja-templating/
	#
	# You can see an example template in templates/index.html
	#
	# context are the variables that are passed to the template.
	# for example, "data" key in the context variable defined below will be 
	# accessible as a variable in index.html:
	#
	#     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
	#     <div>{{data}}</div>
	#     
	#     # creates a <div> tag for each element in data
	#     # will print: 
	#     #
	#     #   <div>grace hopper</div>
	#     #   <div>alan turing</div>
	#     #   <div>ada lovelace</div>
	#     #
	#     {% for n in data %}
	#     <div>{{n}}</div>
	#     {% endfor %}
	#
	context = dict(data = names)


	#
	# render_template looks in the templates/ folder for files.
	# for example, the below file reads template/index.html
	#
	return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#

# Example of adding new data to the database
@app.route('/book_title_query', methods=['POST'])
def book_title_query():
    # accessing form inputs from user

    query_id = request.form['title']

    params = {}
    params["query_id"] = query_id
    query = text("SELECT B.title, \
                         STRING_AGG(DISTINCT CONCAT(CONCAT(A.first_name, ' '), A.last_name), ', ') AS authors, \
                         B.pub_year, \
                         STRING_AGG(DISTINCT L.name, ', ') AS available_at, \
                         B.isbn \
                  FROM book B, wrote W, author A, library L \
                  WHERE B.copy_id = W.copy_id \
                    AND W.author_id = A.author_id \
                    AND B.owned_by = L.library_id \
                    AND LOWER(B.title) LIKE CONCAT(CONCAT('%', LOWER(:query_id)), '%') \
                  GROUP BY B.isbn, B.title, B.pub_year")

    cursor = g.conn.execute(query, params)

    titles = []
    authors = []
    dates = []
    libraries = []
    isbns = []
    for result in cursor:
        titles.append(result[0])
        authors.append(result[1])
        dates.append(result[2])
        libraries.append(result[3])
        isbns.append(result[4])
    cursor.close()

    context = dict(titles = titles, authors = authors, dates = dates, libraries = libraries, isbns = isbns)
    return render_template("book.html", **context)


@app.route('/book_author_query', methods=['POST'])
def book_author_query():
    # accessing form inputs from user

    query_id = request.form['author_name']

    params = {}
    params["query_id"] = query_id
    query = text("SELECT B.title, \
                         STRING_AGG(DISTINCT CONCAT(CONCAT(A.first_name, ' '), A.last_name), ', ') AS authors, \
                         B.pub_year, \
                         STRING_AGG(DISTINCT L.name, ', ') AS available_at, \
                         B.isbn \
                  FROM book B, wrote W, author A, library L \
                  WHERE B.copy_id = W.copy_id \
                    AND W.author_id = A.author_id \
                    AND B.owned_by = L.library_id \
                    AND EXISTS (SELECT * \
                                FROM book B2, wrote W2, author A2 \
                                WHERE B2.copy_id = W2.copy_id \
                                  AND W2.author_id = A2.author_id \
                                  AND LOWER(CONCAT(CONCAT(A2.first_name, ' '), A2.last_name)) LIKE CONCAT(CONCAT('%', LOWER(:query_id)), '%') \
                                  AND B2.isbn = B.isbn) \
                  GROUP BY B.isbn, B.title, B.pub_year")
    cursor = g.conn.execute(query, params)

    titles = []
    authors = []
    dates = []
    libraries = []
    isbns = []
    for result in cursor:
        titles.append(result[0])
        authors.append(result[1])
        dates.append(result[2])
        libraries.append(result[3])
        isbns.append(result[4])
    cursor.close()

    context = dict(titles = titles, authors = authors, dates = dates, libraries = libraries, isbns = isbns)
    return render_template("book.html", **context)


@app.route('/book_library_query', methods=['POST'])
def book_library_query():
    # accessing form inputs from user

    query_id = request.form['library_name']

    params = {}
    params["query_id"] = query_id
    query = text("SELECT B.title, \
                         STRING_AGG(DISTINCT CONCAT(CONCAT(A.first_name, ' '), A.last_name), ', ') AS authors, \
                         B.pub_year, \
                         STRING_AGG(DISTINCT L.name, ', ') AS available_at, \
                         B.isbn \
                  FROM book B, wrote W, author A, library L \
                  WHERE B.copy_id = W.copy_id \
                    AND W.author_id = A.author_id \
                    AND B.owned_by = L.library_id \
                    AND EXISTS (SELECT * \
                                FROM book B2, library L2 \
                                WHERE B2.owned_by = L2.library_id \
                                  AND LOWER(L2.name) LIKE CONCAT(CONCAT('%', LOWER(:query_id)), '%') \
                                  AND B2.isbn = B.isbn) \
                  GROUP BY B.isbn, B.title, B.pub_year")

    cursor = g.conn.execute(query, params)

    titles = []
    authors = []
    dates = []
    libraries = []
    isbns = []
    for result in cursor:
        titles.append(result[0])
        authors.append(result[1])
        dates.append(result[2])
        libraries.append(result[3])
        isbns.append(result[4])
    cursor.close()

    context = dict(titles = titles, authors = authors, dates = dates, libraries = libraries, isbns = isbns)
    return render_template("book.html", **context)

@app.route('/book.html')
def book():
    titles = []
    authors = []
    dates = []
    libraries = []
    isbns = []

    context = dict(titles = titles, authors = authors, dates = dates, libraries = libraries, isbns = isbns)
    return render_template("book.html", **context)

@app.route('/review_add_add', methods=['POST'])
def review_add_add():
    params = {}
    params["copy_id" ] = request.form['copy']
    params["username"] = request.form['username']
    params["text"] = request.form['review']
    params["stars"] = int(request.form['stars'])
    g.conn.execute(text('INSERT INTO review VALUES (:copy_id, :username, current_timestamp, :text, :stars)'), params)
    g.conn.commit()

    return redirect('/review_all')

@app.route('/invalid.html', methods=['GET'])
def invalid():
    context = dict()
    return render_template("invalid.html", **context)

@app.route('/review_add', methods=['POST'])
def review_add():
    username = request.form['username']
    params = {}
    params['username'] = username

    query = text("SELECT COUNT(*) \
                  FROM client \
                  WHERE username = :username")
    cursor = g.conn.execute(query, params)
    if cursor.fetchone()[0] == 0:
        return redirect('/invalid.html')

    query = text("SELECT B.title, B.copy_id \
                  FROM book B, borrows W, client C \
                  WHERE B.copy_id = W.copy_id \
                    AND W.username = C.username \
                    AND C.username = :username")
    cursor = g.conn.execute(query, params)

    titles = []
    ids = []
    for result in cursor:
        titles.append(result[0])
        ids.append(result[1])
    cursor.close()
    context = dict(titles = titles, ids = ids, username = username)
    return render_template("review_add.html", **context)

@app.route('/review_login', methods=['GET'])
def review_login():
    context = dict()
    return render_template("review_login.html", **context)

@app.route('/review_all', methods=['GET'])
def review_all():
    query = text("SELECT B.title, R.pub_date, R.text, R.stars, R.username \
                  FROM review R LEFT JOIN book B on B.copy_id = R.copy_id")
    cursor = g.conn.execute(query)

    titles = []
    dates = []
    reviews = []
    stars = []
    usernames = []
    for result in cursor:
        titles.append(result[0])
        dates.append(result[1].strftime("%B %d %Y"))
        reviews.append(result[2])
        stars.append(result[3])
        usernames.append(result[4])
    cursor.close()

    context = dict(titles = titles, dates = dates, reviews = reviews, stars = stars, usernames = usernames)
    return render_template("review.html", **context)


# Example of adding new data to the database
@app.route('/review_query', methods=['POST'])
def review_query():
    # accessing form inputs from user
    query_id = request.form['title']
    
    params = {}
    params["query_id"] = query_id
    query = text("SELECT B.title, R.pub_date, R.text, R.stars, R.username \
                  FROM review R LEFT JOIN book B on B.copy_id = R.copy_id \
                  WHERE LOWER(B.title) LIKE " + "CONCAT(CONCAT('%', LOWER(:query_id)), '%')")
    cursor = g.conn.execute(query, params)

    titles = []
    dates = []
    reviews = []
    stars = []
    usernames = []
    for result in cursor:
        titles.append(result[0])
        dates.append(result[1].strftime("%B %d %Y"))
        reviews.append(result[2])
        stars.append(result[3])
        usernames.append(result[4])
    cursor.close()

    context = dict(titles = titles, dates = dates, reviews = reviews, stars = stars, usernames = usernames)
    return render_template("review.html", **context)


@app.route('/review.html')
def review():
    titles = []
    dates = []
    reviews = []
    stars = []
    usernames = []

    context = dict(titles = titles, dates = dates, reviews = reviews, stars = stars, usernames = usernames)
    return render_template("review.html", **context)
 

@app.route('/library_all', methods=['POST'])
def library_all():
    query = text("SELECT L.name, L.address, L.hours, L.specialization, U.name \
                  FROM library L LEFT JOIN university U on L.affiliated_with = U.university_id")
    cursor = g.conn.execute(query)

    names = []
    addresses = []
    hoursss = []
    specializations = []
    affiliations = []
    for result in cursor:
        names.append(result[0])
        addresses.append(result[1])
        hoursss.append(result[2])
        specializations.append(result[3])
        affiliations.append(result[4])
    cursor.close()

    context = dict(names = names, addresses  = addresses, hoursss = hoursss, specializations = specializations, affiliations = affiliations)
    return render_template("library.html", **context)


# Example of adding new data to the database
@app.route('/library_query', methods=['POST'])
def library_query():
    # accessing form inputs from user
    query_id = request.form['name']
    
    params = {}
    params["query_id"] = query_id
    query = text("SELECT L.name, L.address, L.hours, L.specialization, U.name \
                  FROM library L LEFT JOIN university U on L.affiliated_with = U.university_id \
                  WHERE LOWER(L.name) LIKE " + "CONCAT(CONCAT('%', LOWER(:query_id)), '%')")
    cursor = g.conn.execute(query, params)

    names = []
    addresses = []
    hoursss = []
    specializations = []
    affiliations = []
    for result in cursor:
        names.append(result[0])
        addresses.append(result[1])
        hoursss.append(result[2])
        specializations.append(result[3])
        affiliations.append(result[4])
    cursor.close()

    context = dict(names = names, addresses  = addresses, hoursss = hoursss, specializations = specializations, affiliations = affiliations)
    return render_template("library.html", **context)

@app.route('/library.html')
def library():
    names = []
    addresses = []
    hoursss = []
    specializations = []
    affiliations = []

    context = dict(names = names, addresses  = addresses, hoursss = hoursss, specializations = specializations, affiliations = affiliations)
    return render_template("library.html", **context)



# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
	# accessing form inputs from user
	name = request.form['name']
	
	# passing params in for each variable into query
	params = {}
	params["new_name"] = name
	g.conn.execute(text('INSERT INTO test(name) VALUES (:new_name)'), params)
	g.conn.commit()
	return redirect('/')


@app.route('/login')
def login():
	abort(401)
	this_is_never_executed()


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
