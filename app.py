from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from gemini_ai import ask_ai
from PyPDF2 import PdfReader
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
if not os.path.exists("uploads"):
    os.makedirs("upoads")

app.secret_key = "ashmita123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user"] = user.fullname
            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("login.html")


# ---------------- SIGNUP ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already exists")
            return redirect("/login")

        user = User(
            fullname=fullname,
            email=email,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        user=session["user"],
        hr_progress=session.get("hr_question_no",1)-1,
        tech_progress=session.get("tech_question_no",1)-1,
        coding_progress=session.get("coding_question_no",1)-1
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/")


# ---------------- HR INTERVIEW ----------------

@app.route("/hr")
def hr():

    if "question_no" not in session:
        session["question_no"] = 1
    else:
        session["question_no"] += 1

    prompt = """
Generate ONLY ONE HR interview question for a Computer Science student.
Return only the question.
"""

    question = ask_ai(prompt)

    return render_template(
        "hr.html",
        question=question,
        question_no=session["question_no"]
    )

# ---------------- EVALUATE HR ----------------

@app.route("/evaluate_hr", methods=["POST"])
def evaluate_hr():

    question = request.form["question"]
    answer = request.form["answer"]

    prompt = f"""
You are an HR interviewer.

Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer.

Give:

1. Score out of 10
2. Strengths
3. Weaknesses
4. Improvements
5. Ideal Answer
"""

    feedback = ask_ai(prompt)

    return render_template(
        "feedback.html",
        feedback=feedback
    )


# ---------------- TECHNICAL ----------------

@app.route("/technical")
def technical():

    question_no = session.get("tech_question_no", 1)

    prompt = f"""
Generate ONLY ONE Technical Interview Question for a Computer Science student.

This is Question Number {question_no}.

Return only the question.
"""

    question = ask_ai(prompt)

    return render_template(
        "technical.html",
        question=question,
        question_no=question_no
    )


#------------Evaluate Technical ------------

@app.route("/evaluate_technical", methods=["POST"])
def evaluate_technical():

    question = request.form["question"]
    answer = request.form["answer"]

    prompt = f"""
You are a Technical Interviewer.

Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer.

Give:
1. Score out of 10
2. Strengths
3. Weaknesses
4. Improvements
5. Ideal Answer
"""

    feedback = ask_ai(prompt)

    session["tech_question_no"] = session.get("tech_question_no", 1) + 1

    return render_template(
        "feedback.html",
        feedback=feedback
    )

# ---------------- CODING ----------------

@app.route("/coding")
def coding():

    question_no = session.get("coding_question_no", 1)

    prompt = f"""
Generate ONLY ONE Coding Interview Question for a Computer Science student.

Question Number: {question_no}

For the question provide:

- Problem Statement
- Difficulty
- Topics Tested

Do NOT provide the solution.
"""

    question = ask_ai(prompt)

    return render_template(
        "coding.html",
        question=question,
        question_no=question_no
    )



#-----------evaluate coding------------

@app.route("/evaluate_coding", methods=["POST"])
def evaluate_coding():

    question = request.form["question"]
    answer = request.form["answer"]

    prompt = f"""
You are a Coding Interviewer.

Coding Question:

{question}

Candidate Code:

{answer}

Evaluate it.

Give:

1. Score out of 10
2. Correctness
3. Time Complexity
4. Space Complexity
5. Strengths
6. Weaknesses
7. Improvements
8. Better Approach
"""

    feedback = ask_ai(prompt)

    session["coding_question_no"] = session.get("coding_question_no",1)+1

    return render_template(
        "feedback.html",
        feedback=feedback
    )



#---------Restart session----------

@app.route("/restart_hr")
def restart_hr():

    session["hr_question_no"] = 1
    return redirect("/hr")


@app.route("/restart_technical")
def restart_technical():

    session["tech_question_no"] = 1
    return redirect("/technical")


@app.route("/restart_coding")
def restart_coding():

    session["coding_question_no"] = 1
    return redirect("/coding")



#------------RESUME---------------  


@app.route("/resume", methods=["GET", "POST"])
def resume():

    if request.method == "POST":

        if "resume" not in request.files:
            return "No file selected"

        file = request.files["resume"]

        if file.filename == "":
            return "Please select a PDF"

        filename = secure_filename(file.filename)   

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(filepath)

        try:
            reader = PdfReader(filepath)

            resume_text = ""



            job_description = request.form["job_description"]

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    resume_text += text


            prompt = f"""
You are an ATS Resume Analyzer.

Analyze the resume using a FIXED scoring method.

Scoring Rules:
- Skills: 30 marks
- Education: 15 marks
- Projects: 20 marks
- Experience/Internship: 15 marks
- Resume Formatting: 10 marks
- Certifications: 10 marks

Total = 100

Return the result in exactly this format:

ATS Score: __/100

Skills Found:
...

Missing Skills:
...

Strengths:
...

Weaknesses:
...

Suggestions:
...

IMPORTANT:
If the same resume is analyzed again, return the same score unless the resume content changes.

Resume:
{resume_text}
"""


            result = ask_ai(prompt)

            return render_template(
                "resume_result.html",
                result=result
            )

        except Exception as e:
            return f"Error reading PDF: {e}"

    return render_template("resume.html")

# ---------------- MAIN ----------------

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)