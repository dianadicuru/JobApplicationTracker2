from flask import Flask, render_template, request, redirect, url_for, flash
import os
from dotenv import load_dotenv
from database import fetch_all, fetch_one, execute_query

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallbackkey")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/companies")
def companies():
    companies_list = fetch_all("SELECT * FROM companies ORDER BY company_id DESC")
    return render_template("companies.html", companies=companies_list)


@app.route("/companies/add", methods=["GET", "POST"])
def add_company():
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        website = request.form["website"]

        execute_query(
            "INSERT INTO companies (name, location, website) VALUES (%s, %s, %s)",
            (name, location, website)
        )
        flash("Company added successfully.")
        return redirect(url_for("companies"))

    return render_template("company_form.html", company=None)


@app.route("/companies/edit/<int:company_id>", methods=["GET", "POST"])
def edit_company(company_id):
    company = fetch_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))

    if request.method == "POST":
        execute_query(
            "UPDATE companies SET name=%s, location=%s, website=%s WHERE company_id=%s",
            (
                request.form["name"],
                request.form["location"],
                request.form["website"],
                company_id
            )
        )
        flash("Company updated successfully.")
        return redirect(url_for("companies"))

    return render_template("company_form.html", company=company)


@app.route("/companies/delete/<int:company_id>")
def delete_company(company_id):
    execute_query("DELETE FROM companies WHERE company_id = %s", (company_id,))
    flash("Company deleted successfully.")
    return redirect(url_for("companies"))

@app.route("/jobs")
def jobs():
    jobs_list = fetch_all("""
        SELECT jobs.*, companies.name AS company_name
        FROM jobs
        JOIN companies ON jobs.company_id = companies.company_id
        ORDER BY jobs.job_id DESC
    """)
    return render_template("jobs.html", jobs=jobs_list)


@app.route("/jobs/add", methods=["GET", "POST"])
def add_job():
    companies_list = fetch_all("SELECT * FROM companies ORDER BY name")

    if request.method == "POST":
        company_id = request.form["company_id"]
        title = request.form["title"]
        salary = request.form["salary"] or None
        status = request.form["status"]
        required_skills = request.form["required_skills"]
        description = request.form["description"]

        execute_query("""
            INSERT INTO jobs (company_id, title, salary, status, required_skills, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (company_id, title, salary, status, required_skills, description))

        flash("Job added successfully.")
        return redirect(url_for("jobs"))

    return render_template("job_form.html", job=None, companies=companies_list)


@app.route("/jobs/edit/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):
    job = fetch_one("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    companies_list = fetch_all("SELECT * FROM companies ORDER BY name")

    if request.method == "POST":
        company_id = request.form["company_id"]
        title = request.form["title"]
        salary = request.form["salary"] or None
        status = request.form["status"]
        required_skills = request.form["required_skills"]
        description = request.form["description"]

        execute_query("""
            UPDATE jobs
            SET company_id=%s, title=%s, salary=%s, status=%s, required_skills=%s, description=%s
            WHERE job_id=%s
        """, (company_id, title, salary, status, required_skills, description, job_id))

        flash("Job updated successfully.")
        return redirect(url_for("jobs"))

    return render_template("job_form.html", job=job, companies=companies_list)


@app.route("/jobs/delete/<int:job_id>")
def delete_job(job_id):
    execute_query("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    flash("Job deleted successfully.")
    return redirect(url_for("jobs"))

@app.route("/skills")
def skills():
    skills_list = fetch_all("SELECT * FROM skills ORDER BY skill_id DESC")
    return render_template("skills.html", skills=skills_list)


@app.route("/skills/add", methods=["GET", "POST"])
def add_skill():
    if request.method == "POST":
        skill_name = request.form["skill_name"]
        category = request.form["category"]

        execute_query(
            "INSERT INTO skills (skill_name, category) VALUES (%s, %s)",
            (skill_name, category)
        )
        flash("Skill added successfully.")
        return redirect(url_for("skills"))

    return render_template("skill_form.html", skill=None)


@app.route("/skills/edit/<int:skill_id>", methods=["GET", "POST"])
def edit_skill(skill_id):
    skill = fetch_one("SELECT * FROM skills WHERE skill_id = %s", (skill_id,))

    if request.method == "POST":
        skill_name = request.form["skill_name"]
        category = request.form["category"]

        execute_query(
            "UPDATE skills SET skill_name=%s, category=%s WHERE skill_id=%s",
            (skill_name, category, skill_id)
        )
        flash("Skill updated successfully.")
        return redirect(url_for("skills"))

    return render_template("skill_form.html", skill=skill)


@app.route("/skills/delete/<int:skill_id>")
def delete_skill(skill_id):
    execute_query("DELETE FROM skills WHERE skill_id = %s", (skill_id,))
    flash("Skill deleted successfully.")
    return redirect(url_for("skills"))


@app.route("/applications")
def applications():
    applications_list = fetch_all("""
        SELECT applications.*, jobs.title AS job_title
        FROM applications
        JOIN jobs ON applications.job_id = jobs.job_id
        ORDER BY applications.application_id DESC
    """)
    return render_template("applications.html", applications=applications_list)


@app.route("/applications/add", methods=["GET", "POST"])
def add_application():
    jobs_list = fetch_all("SELECT * FROM jobs ORDER BY title")

    if request.method == "POST":
        job_id = request.form["job_id"]
        application_date = request.form["application_date"]
        status = request.form["status"]
        user_skills = request.form["user_skills"]
        notes = request.form["notes"]

        execute_query("""
            INSERT INTO applications (job_id, application_date, status, user_skills, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (job_id, application_date, status, user_skills, notes))

        flash("Application added successfully.")
        return redirect(url_for("applications"))

    return render_template("application_form.html", application=None, jobs=jobs_list)


@app.route("/applications/edit/<int:application_id>", methods=["GET", "POST"])
def edit_application(application_id):
    application = fetch_one("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    jobs_list = fetch_all("SELECT * FROM jobs ORDER BY title")

    if request.method == "POST":
        job_id = request.form["job_id"]
        application_date = request.form["application_date"]
        status = request.form["status"]
        user_skills = request.form["user_skills"]
        notes = request.form["notes"]

        execute_query("""
            UPDATE applications
            SET job_id=%s, application_date=%s, status=%s, user_skills=%s, notes=%s
            WHERE application_id=%s
        """, (job_id, application_date, status, user_skills, notes, application_id))

        flash("Application updated successfully.")
        return redirect(url_for("applications"))

    return render_template("application_form.html", application=application, jobs=jobs_list)


@app.route("/applications/delete/<int:application_id>")
def delete_application(application_id):
    execute_query("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted successfully.")
    return redirect(url_for("applications"))


def normalize_skills(skills_text):
    if not skills_text:
        return set()
    return {skill.strip().lower() for skill in skills_text.split(",") if skill.strip()}


@app.route("/match/<int:application_id>")
def match(application_id):
    result = fetch_one("""
        SELECT a.application_id, a.user_skills, j.title, j.required_skills
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.application_id = %s
    """, (application_id,))

    if not result:
        flash("Application not found.")
        return redirect(url_for("applications"))

    user_skills = normalize_skills(result["user_skills"])
    required_skills = normalize_skills(result["required_skills"])
    matched = user_skills.intersection(required_skills)

    percentage = round((len(matched) / len(required_skills)) * 100, 2) if required_skills else 0

    return render_template(
        "match.html",
        job_title=result["title"],
        user_skills=sorted(user_skills),
        required_skills=sorted(required_skills),
        matched_skills=sorted(matched),
        percentage=percentage
    )

if __name__ == "__main__":
    app.run(debug=True)