from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect,session,flash
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class InterviewResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_name = db.Column(db.String(100))

    hr_score = db.Column(db.Integer)

    technical_score = db.Column(db.Integer)

    coding_score = db.Column(db.Integer)

    ats_score = db.Column(db.Integer)

    percentage = db.Column(db.Float)

    result = db.Column(db.String(20))    