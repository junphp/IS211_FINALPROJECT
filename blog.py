from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from flask import flash
from flask import g
from time import gmtime, strftime
import hashlib
import sqlite3 as sql
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Flask initialize
app = Flask(__name__)
app.secret_key = 'app secret key'
DATABASE = "blogdb.db"
# --------------------------------
# ---- database config
# --------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sql.connect(DATABASE)
    return db


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_first_request
def init_database_config():
    init_db()

# -----------------------------------
# ----- display multi user posting
# -----------------------------------
@app.route('/')
def index():

    cur = get_db().execute("SELECT * FROM post WHERE stat_post = 'p' ORDER BY postid DESC")
    rows = cur.fetchall()
    return render_template('index.html', rows=rows)


# -----------------------------------
# ----- create user in database
# -----------------------------------
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if len(username)>0 and re.search('@', email) and len(password)>0:
            obj = hashlib.md5(password.encode())
            hash_password = obj.hexdigest()

            cur = get_db().execute("SELECT * FROM blog_user WHERE email='%s'"% email)
            rows = cur.fetchall()
            if rows:
                return render_template('signup.html', error='e')
            else:
                get_db().execute("INSERT INTO blog_user (username, email, password, logged_in) VALUES (?,?,?,?)", (username, email, hash_password, 0))
                get_db().commit()
            return redirect(url_for('login'))
        else:
            return render_template('signup.html', error='t')
    else:
        return render_template('signup.html', error='f')

# -----------------------------------
# ----- login in order to read, edit, delete and create new post
# -----------------------------------
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if re.search('@', email) and len(password) > 0:
            obj = hashlib.md5(password.encode())
            hash_password = obj.hexdigest()

            cur = get_db().execute("SELECT * FROM blog_user WHERE email=? AND password=?", (email, hash_password))
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    session['logged_in'] = True
                    session['userid'] = row[0]
                    session['name'] = row[1]
                    session['email'] = row[2]
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='t')
    else:
        return render_template('login.html', error='f')


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    cur = get_db().execute("select * from post")

    rows = cur.fetchall()
    return render_template('index.html', rows=rows)

# -----------------------------------
# ----- display each user own posting
# -----------------------------------
@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():

    cur = get_db().execute("SELECT * FROM post WHERE auth_id='%s' ORDER BY postid DESC" % session['userid'])
    rows = cur.fetchall()

    return render_template('dashboard.html', rows=rows)

# -----------------------------------
# ----- create new post
# -----------------------------------
@app.route('/create_post', methods=['POST', 'GET'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        auth_id = request.form['auth_id']
        auth_name = request.form['auth_name']
        date_posted = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        cat = request.form['custom_cat']

        get_db().execute("INSERT INTO post (title, content, date_posted, auth_id, auth_name, cat) VALUES (?,?,?,?,?,?)",
                        (title, content, date_posted, auth_id, auth_name, cat))
        get_db().commit()

        if cat != "":
            cur = get_db().execute("SELECT SUM(cat) FROM category WHERE cat='%s'" % cat)

            rs = cur.fetchone()[0]

            if rs <= 0:
                get_db().execute("INSERT INTO category (cat) VALUES (?)", (cat,))
                get_db().commit()

        return redirect(url_for('index'))
    else:
        cur = get_db().execute("SELECT cat FROM post GROUP BY cat")
        rows = cur.fetchall()
        return render_template('create_post.html', rows=rows)


@app.route('/read_post', methods=['GET'])
def read_post():
    postid = request.args.get('postid')

    cur = get_db().execute("SELECT * FROM post WHERE postid='%s'" % postid)
    rows = cur.fetchall()
    return render_template('read_post.html', rows=rows)


@app.route('/edit_post', methods=['GET', 'POST'])
def edit_post():
    if request.method == 'POST':

        get_db().execute("UPDATE post SET title=?, content=?, cat=? WHERE postid=?", (request.form['title'], request.form['content'], request.form['cat'], request.form['postid']))
        get_db().commit()
        cur = get_db().execute("SELECT SUM(cat) FROM category WHERE cat='%s'" % request.form['cat'])
        rs = cur.fetchone()[0]

        if rs <= 0:
            get_db().execute("INSERT INTO category (cat) VALUES (?)", (request.form['cat'],))
            get_db().commit()

        cur = get_db().execute("SELECT * FROM post WHERE auth_id='%s' ORDER BY postid DESC" % session['userid'])
        rows = cur.fetchall()

        return render_template('dashboard.html', rows=rows)

    elif request.method == 'GET':
        postid = request.args.get('postid')

        cur = get_db().execute("SELECT * FROM post WHERE postid='%s'" % postid)
        rows = cur.fetchall()
        cur = get_db().execute("SELECT cat FROM category GROUP BY cat")
        cats = cur.fetchall()
        return render_template('edit_post.html', rows=rows, cats=cats)


# -----------------------------------
# ----- delete post
# -----------------------------------
@app.route('/delete_post', methods=['GET'])
def delete_post():
    postid = request.args.get('postid')

    get_db().execute("DELETE FROM post WHERE postid='%s'" % postid)
    get_db().commit()
    cur = get_db().execute("SELECT * FROM post WHERE auth_id='%s' ORDER BY postid DESC" % session['userid'])
    rows = cur.fetchall()

    return render_template('dashboard.html', rows=rows)


# -----------------------------------
# ----- Unpublish or Publish
# -----------------------------------
@app.route('/change_status', methods=['GET'])
def change_status():
    postid = request.args.get('postid')
    status_action = request.args.get('status_action')

    get_db().execute("UPDATE post SET stat_post=? WHERE postid=?", (status_action, postid))
    get_db().commit()
    cur = get_db().execute("SELECT * FROM post WHERE auth_id='%s' ORDER BY postid DESC" % session['userid'])
    rows = cur.fetchall()

    return render_template('dashboard.html', rows=rows)

@app.route('/category', methods=['GET', 'POST'])
def category():
    if request.method == 'POST':
        get_db().execute("INSERT INTO category (cat) VALUES (?)", (request.form['cat'],))
        get_db().commit()
        cur = get_db().execute("SELECT cat FROM category GROUP BY cat ORDER BY cat DESC")
        rows = cur.fetchall()

        return render_template('category.html', rows=rows)
    else:
        cur = get_db().execute("SELECT cat FROM category GROUP BY cat ORDER BY cat DESC")
        rows = cur.fetchall()

    return render_template('category.html', rows=rows)

@app.route('/category_view', methods=['GET', 'POST'])
def category_view():
    cat = request.args.get('cat')
    cur = get_db().execute("SELECT * FROM post WHERE stat_post = 'p' AND cat = '%s' ORDER BY postid DESC" % cat)
    rows = cur.fetchall()

    return render_template('index.html', rows=rows)

if __name__ == '__main__':
    app.run()