#Importing flask, os and sqlite.
from flask import Flask, session, render_template, request, url_for, flash, redirect, abort
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) #Random key will prevent user login data to be kept every restart.



#------------------------------
# Setting up the Database
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_post(post_id,): #Single post retrieval
    conn = get_db_connection()
    post = conn.execute('''
                        SELECT posts.id, parent_id, posts.created, posts.title, posts.content, posts.userid, users.username
                        FROM posts
                        JOIN users ON posts.userid = users.id
                        WHERE posts.id = ?''',
                        (post_id, )).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


def get_reply(parentid): #All reply retreival
    conn = get_db_connection()
    reply = conn.execute('''
                        SELECT posts.*, users.username FROM posts
                        JOIN users ON posts.userid = users.id
                        WHERE parent_id = ? ''',
                        (parentid,)).fetchall()
    conn.close()
    return reply

def get_posts(): # All post retrival
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT posts.id, parent_id, posts.created, posts.title, posts.content, posts.userid, users.username
        FROM posts
        JOIN users ON posts.userid = users.id
        WHERE parent_id IS NULL
        ORDER BY posts.created DESC
    ''').fetchall()
    conn.close()
    return posts
#------------------------------



#------------------------------
# Homepage routing
@app.route('/')
def index():
    posts = get_posts()
    return render_template('index.html', posts=posts)
#------------------------------


#------------------------------
# The main tasks of the user. Main heading routings.
@app.route('/signup/', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username:
            flash('Username is needed!')
        elif not password:
            flash('Password is needed!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, password)) #Create new user into users table
            conn.commit()
            conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('signup.html')


@app.route('/signin/', methods=('GET', 'POST'))
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username:
            flash('Username is needed!')
        elif not password:
            flash('Password is needed!')
        else:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?',
                                (username,)).fetchone() #Read data from users table
            conn.close()

            if user and user['password'] == password:
                session.clear()
                session['user_id'] = user['id'] #User is verified and will be logged in now
                session['username'] = user['username']
                return redirect(url_for('index'))
            else: 
                flash('Invalid username or password')
            
    return render_template('signin.html')

@app.context_processor
def inject_user():
    username = session.get('username') 
    return dict(logged_in_user_name=username) #Saves username to be used in a function (line 16 in base.html)


@app.route('/create/', methods=('GET', 'POST'))
def create():

    if 'user_id' not in session: #User must be logged in first to create a post
        return redirect(url_for('signin'))
    
    else:
        if request.method == 'POST': #Linking the form with the route
            title = request.form['title']
            content = request.form['content']
            userid = session['user_id']

            if not title:
                flash('Title is required!')
            elif not content:
                flash('Content is required!')
            else:
                conn = get_db_connection()
                conn.execute('''INSERT INTO posts (title, content, userid)
                            VALUES (?, ?, ?)''',
                            (title, content, userid)) #Create a new post into posts table
                conn.commit()
                conn.close()

                return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/logout')
def logout():
    session.clear() #Clears the session / current user login
    return redirect(url_for('index'))


#------------------------------
# Extra tasks the user can do
@app.route('/<int:id>/view/', methods=('GET', ))
def view(id):
    post = get_post(id)
    reply = get_reply(id) #Gets the replies associated with the post_id

    return render_template('view.html', post=post, reply=reply)


@app.route('/<int:id>/edit/', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if session.get('user_id') != post['userid']:
        flash("Can't edit this post!") #User verification check
        return redirect(url_for('index'))
    
    if request.method == 'POST':
    
        new_title = request.form['title']
        new_content = request.form['content']

        if not new_title:
            flash('Title is required!')

        elif not new_content:
            flash('Content is required!')

        else:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                        ' WHERE id = ?',
                        (new_title, new_content, id)) #Update post in the posts database
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/reply/', methods=('GET', 'POST'))
def reply(id):
    post = get_post(id)

    if 'user_id' not in session: #User verification, can't be guest to reply
        flash('Need an account to reply!')
        return redirect(url_for('signin'))

    else:
        if request.method == 'POST':
            content = request.form['reply_text']
            userid = session['user_id']
            parentid = id

            if not content:
                flash('1 character minimum is needed!')
            else:
                conn = get_db_connection()
                conn.execute('''INSERT INTO posts
                             (content, userid, parent_id)
                             VALUES (?, ?, ?)''',
                             (content, userid, parentid)) #Create reply of a post in the posts table
                conn.commit()
                conn.close()

                return redirect(url_for('view', id=post['id']))
              
    return render_template('reply.html', post=post)

#------------------------------
# The routing within the selected post 
@app.route('/<int:id>/delete/', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,)) #Delete the post for the post table
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))
#------------------------------

if __name__ == '__main__':
    app.run(debug=False)
