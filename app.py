from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
from dotenv import load_dotenv
from database import fetch_all, fetch_one, execute_query

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallbackkey")


def parse_json_field(raw_text):
    """
    Converts textarea JSON input into a JSON string for MySQL JSON columns.
    Returns None if blank.
    """
    if not raw_text or not raw_text.strip():
        return None

    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
        return json.dumps(parsed)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format.")


def normalize_skills(skills_data):
    """
    Accepts:
    - comma-separated string
    - JSON list
    - JSON object with required_skills
    Returns a normalized lowercase set.
    """
    if not skills_data:
        return set()

    if isinstance(skills_data, str):
        skills_data = skills_data.strip()

        # Try JSON first
        try:
            parsed = json.loads(skills_data)
            skills_data = parsed
        except json.JSONDecodeError:
            # Fallback: comma-separated text
            return {s.strip().lower() for s in skills_data.split(",") if s.strip()}

    if isinstance(skills_data, list):
        return {str(s).strip().lower() for s in skills_data if str(s).strip()}

    if isinstance(skills_data, dict):
        required = skills_data.get("required_skills", [])
        if isinstance(required, list):
            return {str(s).strip().lower() for s in required if str(s).strip()}

    return set()


@app.route("/")
@app.route("/")
def dashboard():
    company_count = fetch_one("SELECT COUNT(*) AS total FROM companies")
    job_count = fetch_one("SELECT COUNT(*) AS total FROM jobs")
    application_count = fetch_one("SELECT COUNT(*) AS total FROM applications")
    contact_count = fetch_one("SELECT COUNT(*) AS total FROM contacts")
    avg_match = fetch_one("SELECT AVG(match_score) AS avg_score FROM job_matches")

    stats = {
        "companies": company_count["total"] if company_count else 0,
        "jobs": job_count["total"] if job_count else 0,
        "applications": application_count["total"] if application_count else 0,
        "contacts": contact_count["total"] if contact_count else 0,
        "avg_match": round(avg_match["avg_score"], 2) if avg_match and avg_match["avg_score"] else 0
    }

    recent_applications = fetch_all("""
        SELECT a.application_id, a.application_date, a.status, j.job_title, c.company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_id DESC
        LIMIT 5
    """)

    return render_template("dashboard.html", stats=stats, recent_applications=recent_applications)



# COMPANIES

@app.route("/companies")
def companies():
    companies_list = fetch_all("""
        SELECT *
        FROM companies
        ORDER BY company_id DESC
    """)
    return render_template("companies.html", companies=companies_list)


@app.route("/companies/add", methods=["GET", "POST"])
def add_company():
    if request.method == "POST":
        execute_query("""
            INSERT INTO companies (company_name, industry, website, city, state, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            request.form["company_name"],
            request.form.get("industry") or None,
            request.form.get("website") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("notes") or None
        ))

        flash("Company added successfully.")
        return redirect(url_for("companies"))

    return render_template("company_form.html", company=None)


@app.route("/companies/edit/<int:company_id>", methods=["GET", "POST"])
def edit_company(company_id):
    company = fetch_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))

    if not company:
        flash("Company not found.")
        return redirect(url_for("companies"))

    if request.method == "POST":
        execute_query("""
            UPDATE companies
            SET company_name = %s,
                industry = %s,
                website = %s,
                city = %s,
                state = %s,
                notes = %s
            WHERE company_id = %s
        """, (
            request.form["company_name"],
            request.form.get("industry") or None,
            request.form.get("website") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("notes") or None,
            company_id
        ))

        flash("Company updated successfully.")
        return redirect(url_for("companies"))

    return render_template("company_form.html", company=company)


@app.route("/companies/delete/<int:company_id>")
def delete_company(company_id):
    execute_query("DELETE FROM companies WHERE company_id = %s", (company_id,))
    flash("Company deleted successfully.")
    return redirect(url_for("companies"))


# -------------------------
# JOBS
# -------------------------
@app.route("/jobs")
def jobs():
    jobs_list = fetch_all("""
        SELECT j.*, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.job_id DESC
    """)
    return render_template("jobs.html", jobs=jobs_list)


@app.route("/jobs/add", methods=["GET", "POST"])
def add_job():
    companies_list = fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")

    if request.method == "POST":
        try:
            requirements_value = parse_json_field(request.form.get("requirements"))

            execute_query("""
                INSERT INTO jobs (
                    company_id, job_title, job_type, salary_min, salary_max,
                    job_url, date_posted, requirements
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                request.form["company_id"],
                request.form["job_title"],
                request.form.get("job_type") or None,
                request.form.get("salary_min") or None,
                request.form.get("salary_max") or None,
                request.form.get("job_url") or None,
                request.form.get("date_posted") or None,
                requirements_value
            ))

            flash("Job added successfully.")
            return redirect(url_for("jobs"))

        except ValueError as e:
            flash(str(e))

    return render_template("job_form.html", job=None, companies=companies_list)


@app.route("/jobs/edit/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):
    job = fetch_one("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    companies_list = fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")

    if not job:
        flash("Job not found.")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        try:
            requirements_value = parse_json_field(request.form.get("requirements"))

            execute_query("""
                UPDATE jobs
                SET company_id = %s,
                    job_title = %s,
                    job_type = %s,
                    salary_min = %s,
                    salary_max = %s,
                    job_url = %s,
                    date_posted = %s,
                    requirements = %s
                WHERE job_id = %s
            """, (
                request.form["company_id"],
                request.form["job_title"],
                request.form.get("job_type") or None,
                request.form.get("salary_min") or None,
                request.form.get("salary_max") or None,
                request.form.get("job_url") or None,
                request.form.get("date_posted") or None,
                requirements_value,
                job_id
            ))

            flash("Job updated successfully.")
            return redirect(url_for("jobs"))

        except ValueError as e:
            flash(str(e))

    return render_template("job_form.html", job=job, companies=companies_list)


@app.route("/jobs/delete/<int:job_id>")
def delete_job(job_id):
    execute_query("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    flash("Job deleted successfully.")
    return redirect(url_for("jobs"))


# -------------------------
# APPLICATIONS
# -------------------------
@app.route("/applications")
def applications():
    applications_list = fetch_all("""
        SELECT a.*, j.job_title, c.company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_id DESC
    """)
    return render_template("applications.html", applications=applications_list)


@app.route("/applications/add", methods=["GET", "POST"])
def add_application():
    jobs_list = fetch_all("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.job_title
    """)

    if request.method == "POST":
        try:
            interview_data_value = parse_json_field(request.form.get("interview_data"))
            cover_letter_sent = 1 if request.form.get("cover_letter_sent") == "on" else 0

            execute_query("""
                INSERT INTO applications (
                    job_id, application_date, status, resume_version,
                    cover_letter_sent, interview_data
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                request.form["job_id"],
                request.form["application_date"],
                request.form.get("status") or "Applied",
                request.form.get("resume_version") or None,
                cover_letter_sent,
                interview_data_value
            ))

            flash("Application added successfully.")
            return redirect(url_for("applications"))

        except ValueError as e:
            flash(str(e))

    return render_template("application_form.html", application=None, jobs=jobs_list)


@app.route("/applications/edit/<int:application_id>", methods=["GET", "POST"])
def edit_application(application_id):
    application = fetch_one("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    jobs_list = fetch_all("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.job_title
    """)

    if not application:
        flash("Application not found.")
        return redirect(url_for("applications"))

    if request.method == "POST":
        try:
            interview_data_value = parse_json_field(request.form.get("interview_data"))
            cover_letter_sent = 1 if request.form.get("cover_letter_sent") == "on" else 0

            execute_query("""
                UPDATE applications
                SET job_id = %s,
                    application_date = %s,
                    status = %s,
                    resume_version = %s,
                    cover_letter_sent = %s,
                    interview_data = %s
                WHERE application_id = %s
            """, (
                request.form["job_id"],
                request.form["application_date"],
                request.form.get("status") or "Applied",
                request.form.get("resume_version") or None,
                cover_letter_sent,
                interview_data_value,
                application_id
            ))

            flash("Application updated successfully.")
            return redirect(url_for("applications"))

        except ValueError as e:
            flash(str(e))

    return render_template("application_form.html", application=application, jobs=jobs_list)


@app.route("/applications/delete/<int:application_id>")
def delete_application(application_id):
    execute_query("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted successfully.")
    return redirect(url_for("applications"))


# -------------------------
# CONTACTS
# -------------------------
@app.route("/contacts")
def contacts():
    contacts_list = fetch_all("""
        SELECT ct.*, c.company_name
        FROM contacts ct
        JOIN companies c ON ct.company_id = c.company_id
        ORDER BY ct.contact_id DESC
    """)
    return render_template("contacts.html", contacts=contacts_list)


@app.route("/contacts/add", methods=["GET", "POST"])
def add_contact():
    companies_list = fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")

    if request.method == "POST":
        execute_query("""
            INSERT INTO contacts (
                company_id, contact_name, title, email, phone, linkedin_url, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form["company_id"],
            request.form["contact_name"],
            request.form.get("title") or None,
            request.form.get("email") or None,
            request.form.get("phone") or None,
            request.form.get("linkedin_url") or None,
            request.form.get("notes") or None
        ))

        flash("Contact added successfully.")
        return redirect(url_for("contacts"))

    return render_template("contact_form.html", contact=None, companies=companies_list)


@app.route("/contacts/edit/<int:contact_id>", methods=["GET", "POST"])
def edit_contact(contact_id):
    contact = fetch_one("SELECT * FROM contacts WHERE contact_id = %s", (contact_id,))
    companies_list = fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")

    if not contact:
        flash("Contact not found.")
        return redirect(url_for("contacts"))

    if request.method == "POST":
        execute_query("""
            UPDATE contacts
            SET company_id = %s,
                contact_name = %s,
                title = %s,
                email = %s,
                phone = %s,
                linkedin_url = %s,
                notes = %s
            WHERE contact_id = %s
        """, (
            request.form["company_id"],
            request.form["contact_name"],
            request.form.get("title") or None,
            request.form.get("email") or None,
            request.form.get("phone") or None,
            request.form.get("linkedin_url") or None,
            request.form.get("notes") or None,
            contact_id
        ))

        flash("Contact updated successfully.")
        return redirect(url_for("contacts"))

    return render_template("contact_form.html", contact=contact, companies=companies_list)


@app.route("/contacts/delete/<int:contact_id>")
def delete_contact(contact_id):
    execute_query("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    flash("Contact deleted successfully.")
    return redirect(url_for("contacts"))


# -------------------------
# JOB MATCH
# -------------------------
@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    jobs_list = fetch_all("""
        SELECT j.job_id, j.job_title, c.company_name, j.requirements
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.job_title
    """)

    if request.method == "POST":
        job_id = request.form["job_id"]
        candidate_skills_text = request.form.get("candidate_skills", "")

        selected_job = fetch_one("""
            SELECT j.job_id, j.job_title, c.company_name, j.requirements
            FROM jobs j
            JOIN companies c ON j.company_id = c.company_id
            WHERE j.job_id = %s
        """, (job_id,))

        if not selected_job:
            flash("Job not found.")
            return redirect(url_for("job_match"))

        candidate_skills = normalize_skills(candidate_skills_text)
        required_skills = normalize_skills(selected_job["requirements"])
        matched_skills = sorted(candidate_skills.intersection(required_skills))
        missing_skills = sorted(required_skills - candidate_skills)

        percentage = 0
        if required_skills:
            percentage = round((len(matched_skills) / len(required_skills)) * 100, 2)

        return render_template(
            "job_match.html",
            jobs=jobs_list,
            selected_job=selected_job,
            candidate_skills=sorted(candidate_skills),
            required_skills=sorted(required_skills),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            percentage=percentage
        )

    return render_template("job_match.html", jobs=jobs_list)

@app.route("/save_match/<int:job_id>", methods=["POST"])
def save_match(job_id):
    candidate_skills_text = request.form.get("candidate_skills", "")

    selected_job = fetch_one("""
        SELECT j.job_id, j.job_title, c.company_name, j.requirements
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.job_id = %s
    """, (job_id,))

    if not selected_job:
        flash("Job not found.")
        return redirect(url_for("job_match"))

    candidate_skills = normalize_skills(candidate_skills_text)
    required_skills = normalize_skills(selected_job["requirements"])
    matched_skills = sorted(candidate_skills.intersection(required_skills))
    missing_skills = sorted(required_skills - candidate_skills)

    match_score = 0.00
    if required_skills:
        match_score = round((len(matched_skills) / len(required_skills)) * 100, 2)

    if match_score >= 80:
        match_status = "Strong Match"
    elif match_score >= 50:
        match_status = "Moderate Match"
    else:
        match_status = "Weak Match"

    execute_query("""
        INSERT INTO job_matches (
            job_id, match_score, matched_skills, missing_skills, match_status
        )
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            match_score = VALUES(match_score),
            matched_skills = VALUES(matched_skills),
            missing_skills = VALUES(missing_skills),
            match_status = VALUES(match_status),
            saved_at = CURRENT_TIMESTAMP
    """, (
        job_id,
        match_score,
        json.dumps(matched_skills),
        json.dumps(missing_skills),
        match_status
    ))

    flash("Job match saved successfully.")
    return redirect(url_for("job_match"))


if __name__ == "__main__":
    app.run(debug=True)