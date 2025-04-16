from flask import Blueprint, render_template, request
import requests
from bs4 import BeautifulSoup
import datetime

views = Blueprint('views', __name__)

@views.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"].strip().upper()
        password = request.form["password"]

        # Unpack now four return values
        attendance_data, student_name, hall_ticket, today_classes = get_attendance(username, password)
        return render_template(
            "index.html",
            attendance=attendance_data,
            name=student_name,
            hall_ticket=hall_ticket,
            today_classes=today_classes
        )
    return render_template("index.html")


def get_attendance(username, password):
    login_url = 'https://ams.veltech.edu.in/'
    secure_url = 'https://ams.veltech.edu.in/Default.aspx'
    attendance_url = 'https://ams.veltech.edu.in/Attendance.aspx'

    session = requests.Session()
    login_page = session.get(login_url)
    if login_page.status_code != 200:
        return [], "", "", []

    soup = BeautifulSoup(login_page.text, 'html.parser')
    viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
    viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
    eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

    payload = {
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        '__EVENTVALIDATION': eventvalidation,
        'txtUserName': username,
        'txtPassword': password,
        'Button1': "LET'S GO"
    }

    response = session.post(login_url, data=payload)
    secure_response = session.get(secure_url)
    if secure_response.url != secure_url:
        return [], "Login failed", "", []

    secure_soup = BeautifulSoup(secure_response.text, 'html.parser')
    name_element = secure_soup.find('span', id='MainContent_lblStuname')
    roll_number_element = secure_soup.find('span', id='MainContent_lblRollNo')

    student_name = name_element.text.strip() if name_element else "Name not found"
    hall_ticket = roll_number_element.text.strip() if roll_number_element else "Hall Ticket not found"

    attendance_response = session.get(attendance_url)
    if attendance_response.status_code != 200:
        return [], student_name, hall_ticket, []

    attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')
    summary_table = attendance_soup.find('table', {'id': 'MainContent_GridView2'})

    attendance_info = []
    # Parse summary if available
    if summary_table:
        rows = summary_table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 1:
                try:
                    total_sessions = int(cols[4].text.strip())
                    attended_sessions = int(cols[6].text.strip())
                    present_percentage = float(cols[8].text.strip().replace('%', ''))
                except ValueError:
                    total_sessions = attended_sessions = 0
                    present_percentage = 0.0
                try:
                    overall_pct = float(cols[9].text.strip().replace('%', ''))
                except (IndexError, ValueError):
                    overall_pct = None
                remaining_sessions = max(0, (75 / 100) * total_sessions - attended_sessions)

                attendance_info.append({
                    'course_code': cols[1].text.strip(),
                    'course_name': cols[2].text.strip(),
                    'total_sessions': total_sessions,
                    'attended_sessions': attended_sessions,
                    'present_percentage': present_percentage,
                    'Overall_percentage': overall_pct,
                    'remaining_sessions': remaining_sessions
                })

    # Compute today's classes from detailed table
    today_classes = []
    detail_table = attendance_soup.find('table', {'id': 'MainContent_GridView1'})
    if detail_table:
        today = datetime.datetime.now().date()
        detail_rows = detail_table.find_all('tr')[1:]
        for tr in detail_rows:
            cols = tr.find_all('td')
            if len(cols) < 7:
                continue
            date_str = cols[4].text.strip()
            try:
                class_date = datetime.datetime.strptime(date_str, "%d-%m-%Y %H:%M:%S").date()
            except ValueError:
                continue
            if class_date == today:
                today_classes.append({
                    'course_code': cols[1].text.strip(),
                    'course_name': cols[2].text.strip(),
                    'slot': cols[3].text.strip(),
                    'timeslot': cols[5].text.strip(),
                    'status': cols[6].text.strip()
                })

    return attendance_info, student_name, hall_ticket, today_classes
