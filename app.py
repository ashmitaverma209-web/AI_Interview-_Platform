from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User,InterviewResult
from gemini_ai import ask_ai
from PyPDF2 import PdfReader
import os
from werkzeug.utils import secure_filename
from sqlalchemy import inspect
import re

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from flask import send_file
from datetime import datetime

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.secret_key = "ashmita123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


with app.app_context():
    db.create_all()
    print(inspect(db.engine).get_table_names())
   

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

Give exactly in this format:

Score: X/10

Strengths:
...

Weaknesses:
...

Improvements:
...

Ideal Answer:
...
"""

    feedback = ask_ai(prompt)

    # Default score
    score = 0

    try:
        import re

        match = re.search(r"Score\s*:\s*(\d+)", feedback)

        if match:
            score = int(match.group(1))

    except:
        score = 0

    # Session me score save karo
    session["hr_score"] = score

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

    import re
    score =0

    match = re.search(r"Score\s*:\s*(\d+)",feedback)
    if match:
        score = int(match.group(1))

    session["technical_score"]= score


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

Give exactly in this format:

Score: X/10

Correctness:
...

Time Complexity:
...

Space Complexity:
...

Strengths:
...

Weaknesses:
...

Improvements:
...

Better Approach:
...
"""

    feedback = ask_ai(prompt)

    

    score = 0

    match = re.search(r"Score\s*:\s*(\d+)", feedback)

    if match:
        score = int(match.group(1))

    # Coding Score Save
    session["coding_score"] = score

    # Next Question
    session["coding_question_no"] = session.get("coding_question_no", 1) + 1

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


            # ATS Score Extract
            ats_score = 0

            match = re.search(r"ATS Score\s*:\s*(\d+)", result)

            if match:
              ats_score = int(match.group(1))

# Session me save
            session["ats_score"] = ats_score

            return render_template(
                "resume_result.html",
                result=result
            )

        except Exception as e:
            return f"Error reading PDF: {e}"

    return render_template("resume.html")



#------------------result----------------

@app.route("/final_result")
def final_result():

    hr = session.get("hr_score", 0)

    technical = session.get("technical_score", 0)

    coding = session.get("coding_score", 0)

    ats = session.get("ats_score", 0)

    total = hr + technical + coding

    percentage = round((total / 30) * 100, 2)

    if percentage >= 60:
        status = "PASS ✅"
    else:
        status = "FAIL ❌"



    prompt = f"""
You are an AI Career Coach.

Candidate Performance:

HR Score: {hr}/10
Technical Score: {technical}/10
Coding Score: {coding}/10
ATS Score: {ats}/100

Return ONLY HTML.

Use this exact structure:

<div class="section">
<h3>📊 Overall Performance</h3>
<p>...</p>
</div>

<div class="section">
<h3>💪 Strong Areas</h3>
<ul>
<li>...</li>
</ul>
</div>

<div class="section">
<h3>⚠️ Weak Areas</h3>
<ul>
<li>...</li>
</ul>
</div>

<div class="section">
<h3>💼 Recommended Job Roles</h3>
<ul>
<li>...</li>
</ul>
</div>

<div class="section">
<h3>📚 Skills to Improve</h3>
<ul>
<li>...</li>
</ul>
</div>

<div class="section">
<h3>🎯 Final Recommendation</h3>
<p>...</p>
</div>

Do not use markdown.
Do not use ```html.
Return only valid HTML.
"""

    ai_report =ask_ai(prompt)

    result = InterviewResult(
        user_name=session["user"],
        hr_score=hr,
        technical_score=technical,
        coding_score=coding,
        ats_score=ats,
        percentage=percentage,
        result=status
    )

    db.session.add(result)
    db.session.commit()


    session["final_percentage"] = percentage
    session["final_status"] = status
    session["ai_report"] = ai_report


    return render_template(
        "final_result.html",
        hr=hr,
        technical=technical,
        coding=coding,
        ats=ats,
        percentage=percentage,
        status=status,
        ai_report = ai_report
    )


#----Test result----------
@app.route("/test_result")
def test_result():

    return render_template(
        "final_result.html",
        hr=8,
        technical=7,
        coding=9,
        ats=80,
        percentage=80,
        status="PASS 🎉"
    )    


#-----Download pdf--------------

@app.route("/download_report")
def download_report():

    filename = "Interview_Report.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER
    title.textColor = colors.darkblue

    heading = styles["Heading2"]
    heading.textColor = colors.darkblue

    normal = styles["BodyText"]

    story = []

    story.append(Paragraph("🤖 AI Interview Platform", title))
    story.append(Paragraph("Final Interview Report", heading))
    story.append(Spacer(1,20))

    story.append(
        Paragraph(
            f"<b>Date :</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            normal
        )
    )

    story.append(Spacer(1,15))

    story.append(
        Paragraph(
            f"<b>Overall Percentage :</b> {session.get('final_percentage',0)}%",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Result :</b> {session.get('final_status','N/A')}",
            heading
        )
    )

    story.append(Spacer(1,20))

    data = [
        ["Interview","Score"],

        ["HR",
         session.get("hr_score","-")],

        ["Technical",
         session.get("tech_score","-")],

        ["Coding",
         session.get("coding_score","-")],

        ["ATS Resume",
         session.get("ats_score","-")]
    ]

    table = Table(data,colWidths=[250,120])

    table.setStyle(TableStyle([

        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),

        ('GRID',(0,0),(-1,-1),1,colors.black),

        ('BACKGROUND',(0,1),(-1,-1),colors.beige),

        ('ALIGN',(0,0),(-1,-1),'CENTER'),

        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),

        ('BOTTOMPADDING',(0,0),(-1,0),10)

    ]))

    story.append(table)

    story.append(Spacer(1,25))

    story.append(
        Paragraph("🤖 AI Career Recommendation",heading)
    )

    report = session.get("ai_report","")

    report = report.replace("\n","<br/>")

    story.append(
        Paragraph(report,normal)
    )

    story.append(Spacer(1,30))


    doc.build(story)

    return send_file(filename,as_attachment=True)

# ---------------- MAIN ----------------

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)