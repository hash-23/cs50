
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, validate_register, success

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///tutoring.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    #list all allocations for current user, whether they are tutee or tutor
    if(session["isTutor"]):
        #get list of names of tutees for current tutor uesr
        people = db.execute("SELECT users.fname, users.sname, users.email, allocations.subject, allocations.tutee_year FROM users INNER JOIN allocations ON users.id = allocations.tutee_id WHERE allocations.tutor_id = ?", session["user_id"])
    else:
        #get list of names of tutors for current tutee user
        people = db.execute("SELECT users.fname, users.sname, users.email, allocations.subject, allocations.id FROM users INNER JOIN allocations ON users.id = allocations.tutor_id WHERE allocations.tutee_id = ?", session["user_id"]) #find list of names of tutors for current tutee user

    #also pass names of people being tutored/tutors as an argument
    return render_template("index.html", people=people)

@app.route("/how-it-works", methods=["GET","POST"])
def description():
    if request.method == "POST":
        return apology("Something went wrong")

    return render_template("description.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    #log user in

    session.clear()
    if request.method == "POST":
        #no username entered
        if not request.form.get("username"):
            return apology("Please provide a username", 403, page="/login")

        #no password entered
        elif not request.form.get("password"):
            return apology("Please provide a password", 403, page="/login")

        #checking if username/password pair exist in database
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403, page="/login")

        session["user_id"] = rows[0]["id"]
        session["isTutor"] = rows[0]["isTutor"]
        session["isAdmin"] = rows[0]["isAdmin"]
        session["name"] = rows[0]["fname"] + " " + rows[0]["sname"]

        return redirect("/")

    #request method is get
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

#registering as a normal user
@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        fname = request.form.get("fname")
        sname = request.form.get("sname")

        #check for errors such as missing user details
        error = validate_register(username, email, password, confirm, fname, sname)
        if error:
            return apology(error, page="/register")

        fname = fname.title()
        sname = sname.title()

        #registration complete
        db.execute("INSERT INTO users (username, email, hash, fname, sname, isTutor) VALUES (?, ?, ?, ?, ?, FALSE)", username, email, generate_password_hash(password), fname, sname)

        #logging user in
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        session["isTutor"] = False
        session["isAdmin"] = False
        return success("Account successfully created")

    return render_template("register.html", isTutor=False) #get

#registering as a tutor
@app.route("/tutor-register", methods=["GET", "POST"])
def tutor_register():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        fname = request.form.get("fname")
        sname = request.form.get("sname")

        #check for errors
        error = validate_register(username, email, password, confirm, fname, sname)
        if error:
            return apology(error, page="/tutor-register")

        #registration complete
        db.execute("INSERT INTO users (username, email, hash, fname, sname, isTutor) VALUES (?, ?, ?, ?, ?, TRUE)", username, email, generate_password_hash(password), fname, sname)

        #logging user in
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        session["isTutor"] = True
        session["isAdmin"] = False
        return success("Tutor account successfully created")

    return render_template("register.html", isTutor=True) #get




@app.route("/reserve", methods=["POST", "GET"]) #ability to create appointments for tutoring
@login_required
def reserve():
    #only for tutees
    if session["isTutor"]:
            return apology("Page not available for your account type")


    if request.method == "GET":
        #send a list of available subjects to register.html
        subjects = db.execute("SELECT DISTINCT subject FROM subjects")
        return render_template("reserve.html", subjects=subjects)

    #post
    else:
        year = request.form.get("year")
        subject = request.form.get("subject")

        """
        INSERT FEATURE LATER ON
        days = [] #list of preferred days
        for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]:
            current = request.form.get(day)
            if current:
                days.append(day)
        """

        if not year or not subject: #later on add 'or not days'
            return apology("Please fill in all fields", page="/reserve")


        #checking if user already has a tutor for this subject
        already = db.execute("SELECT * FROM allocations WHERE tutee_id = ? AND subject = ?", session["user_id"], subject)
        if len(already) > 0:
            return apology(f"You already have a tutor for {subject}", page="/reserve")


        """ INSERT LATER ON
        #check available days for chosen subject
        available_days = db.execute("SELECT DISTINCT days, INN)
        """

        #pick a tutor for the chosen subject with the least number of tutees, then sorted by order of tutor_id
        tutor_id = db.execute("SELECT tutors.tutor_id FROM tutors INNER JOIN subjects ON tutors.tutor_id = subjects.tutor_id WHERE subjects.subject = ? ORDER BY tutors.numTutees ASC, tutors.tutor_id ASC LIMIT 1", subject)[0]["tutor_id"]
        #get dictionary of number of tutees for chosen tutor
        numTutees = db.execute("SELECT numTutees FROM tutors WHERE tutor_id = ?", tutor_id)[0]["numTutees"]


        #create record in allocations table
        db.execute("INSERT INTO allocations (tutor_id, tutee_id, subject, tutee_year) VALUES (?, ?, ?, ?)", tutor_id, session["user_id"], subject, year)

        #update number of tutees for chosen tutor
        numTutees +=1
        db.execute("UPDATE tutors SET numTutees = ? WHERE tutor_id = ?", numTutees, tutor_id)

        return success("You have now been allocated a tutor", page="/reserve")

@app.route("/admin", methods=["POST", "GET"])
@login_required
def admin():
    #deny access to non-admin
    if not session["isAdmin"]:
        return apology("Page not available for your account type")

    #show admin data
    if request.method == "GET":
        #show any subjects that have been requested by users
        subjectRequests = db.execute("SELECT users.fname, users.sname, users.email, subjectRequests.subject FROM users INNER JOIN subjectRequests ON subjectRequests.user_id = users.id")
        return render_template("admin.html", subjectRequests=subjectRequests)

    else:
        #deleting a subject request
        subject = request.form.get("delete")

        if not subject:
            return apology("Something went wrong", page="/admin")

        db.execute("DELETE FROM subjectRequests WHERE subject = ?", subject)
        return redirect("/admin")


@app.route("/admin/all_users", methods=["GET", "POST"])
@login_required
def allusers():
    #deny access
    if not session["isAdmin"]:
        return apology("Page not available for your account type")


    if request.method == "GET":
        #show all users
        users = db.execute("SELECT * FROM users")
        return render_template("admin/all_users.html", users=users)

    else:
         return apology("Something went wrong")


@app.route("/admin/all_tutors", methods=["GET", "POST"])
@login_required
def alltutors():
    #deny access
    if not session["isAdmin"]:
        return apology("Page not available for your account type")


    if request.method == "GET":
        #showing data of all tutors and their subjects
        tutors = db.execute("SELECT * FROM users WHERE isTutor = 1")
        subjects = db.execute("SELECT * FROM subjects")

        #showing number of tutees for each tutor
        db_numTutees = db.execute("SELECT * FROM tutors")
        #making a dictionary with key as tutor id and value as number of tutees
        numTutees={}
        for tutor in db_numTutees:
            numTutees[tutor['tutor_id']] = tutor['numTutees']

        return render_template("admin/all_tutors.html", tutors=tutors, subjects=subjects, numTutees=numTutees)

    else:
         return apology("Something went wrong")

@app.route("/admin/all_allocations", methods=["GET", "POST"])
@login_required
def all_allocations():


    if request.method == "GET":

        #deny access
        if not session["isAdmin"]:
                return apology("Page not available for your account type")

        #make list of dictionaries where each item in list is a dictionary corresponds to a single allocation and its details
        allocations = []
        db_allocations = db.execute("SELECT * FROM allocations")

        #going through each allocation
        for allocation in db_allocations:
            current = {} #current allocation/dictionary

            tutor_id = allocation["tutor_id"]
            tutee_id = allocation["tutee_id"]
            current["id"] = allocation["id"]

            #tutor details
            current["tutor_id"] = tutor_id
            tutor = db.execute("SELECT * FROM users WHERE id = ?", tutor_id)[0]
            current["tutor_name"] = tutor["fname"] + " " + tutor["sname"]
            current["tutor_email"] = tutor["email"]

            #tutee details
            current["tutee_id"] = tutee_id
            tutee = db.execute("SELECT * FROM users WHERE id = ?", tutee_id)[0]
            current["tutee_name"] = tutee["fname"] + " " + tutee["sname"]
            current["tutee_email"] = tutee["email"]

            #other allocation details
            current["year"] = allocation["tutee_year"]
            current["subject"] = allocation["subject"]

            #adding current dictionary to list
            allocations.append(current)

        return render_template("/admin/all_allocations.html", allocations=allocations)

    #available for any user to delete an allocation
    else:
        #getting the id of the allocation to be deleted
        delete = int(request.form.get("delete"))

        if not delete:
            if session["isAdmin"]:
                return apology("Something went wrong", page="/admin/all_allocations")
            else:
                return apology("Something went wrong", page="/")

        #getting details of allocation
        allocation = db.execute("SELECT * FROM allocations WHERE id = ?", delete)[0]

        #updating number of tutees for tutor
        numTutees = int(db.execute("SELECT numTutees FROM tutors WHERE tutor_id = ?", allocation['tutor_id'])[0]['numTutees']) - 1

        #updating databases
        db.execute("DELETE FROM allocations WHERE id = ?", delete)
        db.execute("UPDATE tutors SET numTutees = ? WHERE tutor_id = ?", numTutees, allocation['tutor_id'])

        if session["isAdmin"]:
            return success("Allocation successfully deleted", page="/admin/all_allocations")
        else:
            return redirect("/")



""" Edit user"""
@app.route("/edit", methods=["POST", "GET"])
@login_required
def edit():

    if request.method == "GET":
        id = request.args.get("id", type=int)

        #preventing non-admin from editing another user's account
        if (not session["isAdmin"]) and id != session["user_id"]:
            return apology("Page not available for your account type")

        #details of account to be edited
        details = db.execute("SELECT * FROM users WHERE id = ?", id)[0]
        return render_template("edit_account.html", details=details)

    #post

    #getting new edited account details
    fname = request.form.get("fname")
    sname = request.form.get("sname")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    confirm = request.form.get("confirm")
    tutor = False
    if (request.form.get("makeTutor")):
        tutor = True

    id = int(request.form.get("id"))

    already_tutor = db.execute("SELECT isTutor FROM users WHERE id = ?", id)[0]['isTutor']

    #checking if form was submitted with no changes to account
    if not (fname or sname or email or username or password) and tutor == already_tutor:
        return apology("No changes were submitted", page=f"/edit?id={id}")


    if password and confirm and password != confirm:
        return apology("Password and confirmation do not match", page=f"/edit?id={id}")
    else:
        #change password
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(password), id)

    #updating username
    if username:
        #checking if username is already in use
        exists = db.execute("SELECT username FROM users WHERE username = ? AND NOT id = ?", username, id)
        if len(exists) > 0:
            return apology(f"The username '{username}' is already in use", page=f"/edit?id={id}")

        #updating database
        db.execute(f"UPDATE users SET username = {username} WHERE id = {id}")


    #updating email
    if email:
        #checking if email is already in use
        exists = db.execute("SELECT email FROM users WHERE email = ? AND NOT id = ?", email, id)
        if len(exists) > 0:
            return apology(f"The email '{email}' is already in use", page=f"/edit?id={id}")

        #updating database
        db.execute("UPDATE users SET email = ? WHERE id = ?", email, id)

    #updating names
    if fname:
        fname = fname.title()
        db.execute("UPDATE users SET fname = ? WHERE id = ?", fname, id)

    if sname:
        sname = sname.title()
        db.execute("UPDATE users SET sname = ? WHERE id = ?", sname, id)

    #tutor
    db.execute("UPDATE users SET isTutor = ? WHERE id = ?", tutor, id)

    #updating session details if edits made to own account
    if id == session["user_id"]:
        session["isTutor"] = tutor

    #removing user from tutor databases
    if not tutor:
        db.execute("DELETE FROM allocations WHERE tutor_id = ?", id)
        db.execute("DELETE FROM subjects WHERE tutor_id = ?", id)
        db.execute("DELETE FROM tutors WHERE tutor_id = ?", id)

    #adding user to tutor databases
    else:
        db.execute("INSERT INTO tutors (tutor_id, numTutees) VALUES (?, 0)", id)
        tutors = db.execute("SELECT tutor_id FROM allocations WHERE tutee_id = ?", id)

        #updating numTutees for all old tutors of user
        for tutor in tutors:
            numTutees = db.execute("SELECT numTutees FROM tutors WHERE tutor_id = ?", tutor['tutor_id'])[0]['numTutees']
            numTutees -= 1
            db.execute(f"UPDATE tutors SET numTutees = {numTutees} WHERE tutor_id = ?", tutor['tutor_id'])

        #removing user from allocations where user is tutee
        db.execute("DELETE FROM allocations WHERE tutee_id = ?", id)


    #returning user to previous page
    page=""
    if session["isAdmin"]:
        page="/admin/all_users"
    else:
        page=f"/edit?id={id}"
    return success("Changes were successfully submitted", page=page)



@app.route("/subjects", methods=["POST", "GET"])
@login_required
def subjects():
    #deny access
    if not session["isTutor"]:
        return apology("Page not available for your account type")


    if request.method == "GET":
        #getting all of current tutor's subjects
        subjects = db.execute("SELECT subject FROM subjects WHERE tutor_id = ?", session["user_id"])

        #getting all of the subjects being offered
        existing = db.execute("SELECT DISTINCT subject FROM subjects")
        return render_template("subjects.html", subjects=subjects, existing=existing)

    #post
    #getting the subject to be removed from tutor's list
    remove = request.form.get("remove")
    if remove:
        #removing a subject
        db.execute("DELETE FROM subjects WHERE tutor_id = ? AND subject = ?", session["user_id"], remove)
        db.execute("DELETE FROM allocations WHERE tutor_id = ? AND subject = ?", session["user_id"], remove)

        #update numTutees
        numTutees = len((db.execute("SELECT * FROM allocations WHERE tutor_id = ?", session["user_id"])))
        db.execute(f"UPDATE tutors SET numTutees = ? WHERE tutor_id = ?", numTutees, session["user_id"])

        return redirect("/subjects")

    #adding a new subject to the tutor's list
    newSubject = request.form.get("addSubject")
    if newSubject:
        #formatting the user input
        newSubject = newSubject.upper()
        if newSubject not in ["PE", "ICT"]:
            newSubject = newSubject.title()

        #check if newSubject is already in subjects for current tutor
        current_subjects = db.execute("SELECT * FROM subjects WHERE tutor_id = ? AND subject LIKE ?", session["user_id"], newSubject)
        if len(current_subjects) != 0:
            return apology(f"You are already tutoring for {newSubject}", page="/subjects")

        #adding newSubject
        db.execute("INSERT INTO subjects (tutor_id, subject) VALUES (?, ?)", session["user_id"], newSubject)
        return redirect("/subjects")

    #a form was submitted with no values
    return apology("Something went wrong", page="/subjects")

@app.route("/requestSubject", methods=["POST", "GET"])
@login_required
def requestSubject():
    #should only be accessed by a submitted form
    if request.method == "GET":
        return apology("Something went wrong")

    #getting subject being requested by user
    subject = request.form.get("newSubject")

    #making sure text was entered
    if not subject:
        return apology("Please enter a subject to request", page="/reserve")


    #formatting the user input
    subject = subject.upper()
    if subject not in ["PE", "ICT"]:
        subject = subject.title()

    #checking if subject is already available
    exists = len(db.execute("SELECT subject FROM subjects WHERE subject = ?", subject))
    if exists != 0:
        return apology(f"{subject} is already available", page="/reserve")

    #adding requested subject to database for admin review
    db.execute("INSERT INTO subjectRequests (user_id, subject) VALUES (?, ?)", session["user_id"], subject)
    return success(f"Successfully requested {subject} to be added", page="/reserve")