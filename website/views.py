from flask import Blueprint, render_template, request
import requests
from bs4 import BeautifulSoup

views = Blueprint('views', __name__)

@views.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"].strip().upper()  # Convert to uppercase and remove extra spaces
        password = request.form["password"]

        attendance_data, student_name, hall_ticket = get_attendance(username, password)
        return render_template("index.html", attendance=attendance_data, name=student_name, hall_ticket=hall_ticket)

    return render_template("index.html")


def get_attendance(username, password):
    login_url = 'https://ams.veltech.edu.in/'
    secure_url = 'https://ams.veltech.edu.in/Default.aspx'
    attendance_url = 'https://ams.veltech.edu.in/Attendance.aspx'

    session = requests.Session()

    login_page = session.get(login_url)
    if login_page.status_code != 200:
        return "Failed to load login page.", "", ""

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
        return "Login failed.", "", ""

    secure_soup = BeautifulSoup(secure_response.text, 'html.parser')
    name_element = secure_soup.find('span', id='MainContent_lblStuname')
    roll_number_element = secure_soup.find('span', id='MainContent_lblRollNo') 

    student_name = name_element.text.strip() if name_element else "Name not found"
    hall_ticket = roll_number_element.text.strip() if roll_number_element else "Hall Ticket Number not found"

    attendance_response = session.get(attendance_url)
    if attendance_response.status_code != 200:
        return "Failed to load the attendance page.", student_name, hall_ticket

    attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')
    attendance_table = attendance_soup.find('table', {'id': 'MainContent_GridView2'})

    if not attendance_table:
        return "Attendance table not found.", student_name, hall_ticket

    attendance_info = []
    rows = attendance_table.find_all('tr')[1:] 

    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 1:
            course_code = cols[1].text.strip()
            course_name = cols[2].text.strip()
            total_sessions = int(cols[4].text.strip())
            attended_sessions = int(cols[6].text.strip())
            present_percentage = float(cols[8].text.strip().replace('%', ''))

            required_percentage = 75
            required_sessions = (required_percentage / 100) * total_sessions
            remaining_sessions = max(0, required_sessions - attended_sessions)

            attendance_info.append({
                'course_code': course_code,
                'course_name': course_name,
                'total_sessions': total_sessions,
                'attended_sessions': attended_sessions,
                'present_percentage': present_percentage,
                'remaining_sessions': remaining_sessions
            })

    return attendance_info, student_name, hall_ticket
