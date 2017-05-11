
import os
import re
from string import letters
import random
import hmac
import hashlib
import webapp2
import jinja2
import time

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(
	loader = jinja2.FileSystemLoader(template_dir),
    autoescape = True)

### User Related Security - - Part I of II
# First - creating a secret text (Usually not kept in the same file)
secret = 'du.Udslkjfd(98273klksdjf_)sdlkfsdf0ksjdfsdf)ssflk99'

# making a secure value out of a given value using HMAC (using hexdigest)
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

# creating a function to compare the secure_value with original val
def check_secure_val(secure_val):
    # first split the string(secure_val) and take the first fragment
    val = secure_val.split('|')[0]
    # compare
    if secure_val == make_secure_val(val):
        return val



# defining global render_str that takes in global params and template
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# Class for Handling page/post write and rendering
class Handler(webapp2.RequestHandler):
    # easy and shorter method to write out.
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
	
	# takes in parameters (dictionary within it) to put it in template
    def render_str(self, template, **params):
        return render_str(template, **params)

    # calls write and render_str to print out the template
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    ### More funcitons for user properties
    # Funtion sets a cookie, name and a value, and stores in a cookie
    # Cookie header name - Set-Cookie
    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        # one can also inclusde expire time [not here]
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    # Reads for the cookie
    # give it a name, if the cookie exists, it returns
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    # Function for Login
    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    # Function for Logout
    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    # Special function [Important]
    # This checks everytime you have a request
    # Checks for user cookie called user-id, if it exists, it stores
    def initialize(self, *a, **kw):
        # Runs on all the request, everytime
        webapp2.RequestHandler.initialize(self, *a, **kw)
        # checks for user cookie - called 'user_id'
        uid = self.read_secure_cookie('user_id')
        # If the cookie is there, store it in self.user as an object
        # Why?
        self.user = uid and User.by_id(int(uid))    

# defining how post is rendered with subject and content
def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

### User Related Security - - Part II of II
# function to make salt (makes a string of five letters)
def make_salt(length = 5):
    return ''.join(random.choice
        (letters) for x in xrange(length))

# takes in username, password, and salt, and returns (salt, hash version of all three)
def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    # Creating Hash version of three parameters
    h = hashlib.sha256(name + pw + salt).hexdigest()
    # This return is what we store in database
    return '%s,%s' % (salt, h)

# Password verification
# Hash from the password on database is matched with user entered password 
def valid_pw(name, password, h):
    # Taking Hash from the Database
    salt = h.split(',')[0]
    # Matching user input
    return h == make_pw_hash(name, password, salt)


### MainPage Handler
class MainPage(Handler):
    def get(self):
      self.render("front.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            msg = 'Invalid Login'
            self.render('login.html', error = msg)  

### Extra Page - Instruction Page Handler
class About(Handler):
	def get(self):
         if self.user:
            x = "ogout"
            self.render('about.html', userstatus = x)
         else:
            x = "ogin"
            self.render('about.html', userstatus = x)

### Solution for multiple blog groups, or multiple user group
# First - Multiple User Group
# Creates the Ancestral element of the database to store user in groups
# If multiple users are grouped, this function helps
def users_key(group = 'default'):
    return db.Key.from_path('users', group)

# Second - Multiple Blog Groups
# function to store data within a parent (for multiple blog function)
def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

### defining different database entities and its property
### Database Related Stuff
# [Database I] for Blog Post 
class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created_time = db.DateTimeProperty(auto_now_add = True)
    modified_time = db.DateTimeProperty(auto_now = True)
    ## Extra Entities
    author = db.StringProperty()
    like_count = db.IntegerProperty(default=0)
    # Array containing all users who have liked a post
    user_like = db.StringListProperty()

    def render(self):
        # automated creation of new lines on content
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

# [Database II] for Comments
class Comment(db.Model):
    author = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    postid = db.StringProperty(required=True)
    created_time = db.DateTimeProperty(auto_now_add=True)
    modified_time = db.DateTimeProperty(auto_now=True)

    def render(self):
        self.__render_text = self.content.replace('\n', '<br>')
        return render_str("comment.html", c=self)

# [Database III] for User
class User(db.Model):
    firstname = db.StringProperty(required=True)
    lastname=db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    # decorator funciton to call user via user_id key
    def by_id(cls, user_id):
        # Alternate method is to make a key and then call it
        ## user_key = db.Key.from_path('User', int(user_id), parent=users_key())
        ## post = db.get(user_key)
        return User.get_by_id(user_id, parent=users_key())

    @classmethod #THIS MAKES THE MEDTHOD STATIC
    # decorator funciton - to call user via user_name key
    # This is the third method to access the database
    def by_name(cls, name):
        # return User.get_by_id(name, parent=users_key())
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    # Takes in multiple object and creates a user object
    # Doesn't actually stores in the Database, just creates it 
    def register(cls, firstname, lastname, name, pw, email=None):
        # Creates a password Hash first
        pw_hash = make_pw_hash(name, pw)
        return User(parent=users_key(),
                    firstname=firstname,
                    lastname=lastname,
                    name=name,
                    pw_hash=pw_hash,
                    email=email)

    @classmethod 
    # For Login Funciton 
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


### Blog Pages, Post and NewPost
# Class for Blog Front Page which shows given number of blog entry
class BlogFront(Handler):
    def get(self):
        # Checks if Self.User is present, send it to front page
        if self.user:
            posts = db.GqlQuery(
            "select * from Post order by created_time desc limit 10")
            self.render('blog.html', posts = posts, username = self.user.firstname)
        else:
            # Else, send it to signup
            self.redirect('/login')

# Class for Posting a Blog Entry (Handler for rendering post)
class PostPage(Handler):
    def get(self, post_id):
        """ First make a key to the specific post
        	 @post_id - passed in from the URL as a string
        	 @parent=blog_key - since we created a parent structure
        	 Second - we look up a particular item through db.get and store it in "post"
        """
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        if post:
        	self.render("permalink.html", post = post)
        else:
            self.error(404)
            return

        

# Handler Class for Handling New Post
class NewPost(Handler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):

        author = self.user.name
        subject = self.request.get('subject')
        content = self.request.get('content')
        user_like = []

        if subject and content:
            p = Post(
            	parent = blog_key(), 
            	subject = subject, 
            	content = content,
                author = author)
            p.put()

            #making a string that identifies each post
            post_link_store = str(p.key().id())
            self.redirect('/blog/%s' % post_link_store)
        else:
            error = "Subject and Content, please!"
            self.render(
            	"newpost.html", 
            	subject=subject, 
            	content=content, 
            	error=error)

# Handler Class for Editing Specific Post
class EditPost(Handler):
    def get(self, post_id):
        if self.user:
            ### Something similar to def(get) from PostPage 
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            if self.user.name == post.author:
                if post:
                    self.render("editpost.html", post = post)
                else:
                    self.error(404)
                    return
            else:
                self.write("You cannot Edit other User's posts!")
        else:
            return self.redirect('/login')

    def post(self, post_id):
        if not self.user:
            return self.redirect('/blog')

        subject = self.request.get('subject')
        content = self.request.get('content')
    
        if "update" in self.request.POST:
            if subject and content:
                # make key that retreives the entity/row from the Database
                update_value = Post.get_by_id(int(post_id), parent=blog_key())
                if update_value:
                    # modifying the properties of the entity
                    update_value.subject = subject
                    update_value.content = content
                    # storing it back
                    update_value.put()
                    # redirecting to the newly updated page
                    self.redirect('/blog/%s' % str(update_value.key().id()))
                else:
                    return self.error(404)
            else:
                error = "Update your subject and content, please"
                key = db.Key.from_path('Post', int(post_id), parent=blog_key())
                post = db.get(key)
                self.render("editpost.html", post = post)
        if "cancel" in self.request.POST:
            update_value = Post.get_by_id(int(post_id), parent=blog_key())   
            self.redirect('/blog/%s' % str(update_value.key().id()))


# Handler Class for Deleting Specific Post
class DeletePost(Handler):
    def get(self, post_id):
        if self.user:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            if self.user.name == post.author:
                if post:
                    self.render("deletepost.html", post = post)
                else:
                    self.error(404)
                    return
            else:
                self.write("You cannot Delete other User's posts!")
        else:
            return self.redirect('/login')


    def post(self, post_id):
        if not self.user:
            return self.redirect('/blog')

        if "delete-post" in self.request.POST:
            delete_value = Post.get_by_id(int(post_id), parent=blog_key())
            if delete_value:
                delete_value.delete()
                time.sleep(0.2)
                return self.redirect("/blog")
            else:
                return self.error(404)

        if "cancel-delete" in self.request.POST:
            return self.redirect("/blog")

### Like Handler
class LikePost(Handler):
    def post(self, post_id):
        if self.user:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)

            if not post:
                self.error(404)
                return

            if self.user.name != post.author:
                if self.user.name in post.user_like:
                    # self.write("you can only like a post once")
                    post.user_like.remove(self.user.name)
                    post.like_count -= 1
                    post.put()
                    time.sleep(0.2)
                    self.redirect('/blog/postcomment/%s' % post_id)
                else:
                    post.user_like.append(self.user.name)
                    post.like_count += 1
                    post.put()
                    # Putting a Time Delay in Python Script
                    time.sleep(0.2)
                    self.redirect('/blog/postcomment/%s' % post_id)
            if self.user.name == post.author:
                message = "You cannot like your own post."
                ## self.redirect('/blog', error_like = message)
                ## self.render('blog.html', error_like = message)
                ## self.redirect('/blog')
                self.write("You cannot like your own post.")

        else:
            self.redirect("/login")

### Comment Handler
class PostComment(Handler):
    def get(self, post_id):
        if self.user:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)

            if not post:
                return self.error(404)

            comments = db.GqlQuery(
                "SELECT * FROM Comment WHERE postid =:1", str(post_id)
                )
            self.render(
                "postcomment.html",
                post=post,
                comments=comments
                )
        else:
            self.redirect('/login')

    def post(self, post_id):
        if not self.user:
            return self.redirect('/blog')

        if "submit" in self.request.POST:
            content = self.request.get('content')
            author = self.user.name

            if content:
                c = Comment(
                    postid=post_id,
                    content=content,
                    author=author
                    )
                c.put()
                time.sleep(0.1)
                return self.redirect('/blog/postcomment/%s' % post_id)
        if "cancel" in self.request.POST:
            return self.redirect("/blog/%s" % str(post_id))

### Comment Edit and Deleted Handler
class EditComment(Handler):
    def get(self, comment_id):
        if self.user:
            key = db.Key.from_path('Comment', int(comment_id))
            comment = db.get(key)
            if not comment:
                return self.error(404)

            if self.user.name == comment.author:
                self.render("editcomment.html", comment=comment)
            else:
                self.write("You can't edit other User's comments!")
        else:
            self.redirect("/login")

    def post(self, comment_id):
        if not self.user:
            return self.redirect("/blog")

        content = self.request.get('content')
        commentVal = Comment.get_by_id(int(comment_id))

        if "update" in self.request.POST:
            if content:
                commentVal.content = content
                commentVal.put()
                time.sleep(0.1)
                return self.redirect(
                    "/blog/postcomment/%s" % str(commentVal.postid)
                    )


### User Validation
# Valid Firstname
FIRST_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_firstname(firstname):
    return firstname and FIRST_RE.match(firstname)
# Valid Lastname
LAST_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_lastname(lastname):
    return lastname and LAST_RE.match(lastname)
# Valid Username
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)
# Valid Password
PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)
# Valid Email
EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)


### User Related - signup, login, and welcome screen
# Signup Handler
class Signup(Handler):

    def get(self):
        # Render Signup FORM
        self.render("signup.html")

    def post(self):
        have_error = False
        firstname = self.request.get('firstname')
        lastname = self.request.get('lastname')
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        params = dict(username = username,
                      email = email)

        ## Check to see if the input is valid or not, and present error 
        if not valid_firstname(firstname):
            params['error_firstname'] = "That's not a valid Name."
            have_error = True

        if not valid_lastname(lastname):
            params['error_lastname'] = "That's not a valid Last Name."
            have_error = True       

        if not valid_username(username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup.html', **params)
        else:
            # look up if the username already exists
            ## alternate code??## = User.get_by_id(user, parent=users_key())
            u = User.by_name(username)            
            if u:
                message = 'Username already exists, Please choose a different username'
                self.render('signup.html', error_username = message)
            else:
                # Resister the User
                u = User.register(
                    firstname,
                    lastname,
                    username, 
                    password, 
                    email)
                # Put the user Object
                u.put()
                # Call the Login Function - - Sets the Cookie function
                self.login(u)
                self.redirect('/welcome')

            
# Login Handler
class Login(Handler):
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            msg = 'Invalid Login'
            self.render('login.html', error = msg)

# Logout Handler 
class Logout(Handler):
    def get(self):
        self.logout()
        self.redirect('/')

class Welcome(Handler):
    def get(self):
        # Checks if Self.User is present, send it to front page
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            # Else, send it to signup
            self.redirect('/signup')

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/about', About),
                               # User Login and Signup
                               ('/signup', Signup),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               # Blog Related
                               ('/blog/?', BlogFront),
                               ('/blog/editpost/([0-9]+)', EditPost),
                               ('/blog/deletepost/([0-9]+)', DeletePost),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/newpost', NewPost),
                               # Blog Related Extra Features
                                ('/blog/([0-9]+)/like', LikePost),
                                ('/blog/postcomment/([0-9]+)', PostComment),
                                ('/blog/editcomment/([0-9]+)', EditComment),
                               ],debug=True)

