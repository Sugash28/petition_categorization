from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_mail import Mail, Message
from groq import Groq
from config import db_config, groq_api_key, ADMIN_EMAIL, ADMIN_PASSWORD
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  


app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "sugashsugu@gmail.com"
app.config["MAIL_PASSWORD"] = "lnzo ipkz ewty lyie"
app.config["MAIL_DEFAULT_SENDER"] = "sugashsugu@gmail.com"

mail = Mail(app)

# Groq AI client setup
client = Groq(api_key=groq_api_key)

# Default email for admin notifications
default_email = "sugashsugu028@gmail.com"



# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/help')
def help():
    return render_template('help.html')
# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

from config import db_config, groq_api_key, ADMIN_EMAIL, ADMIN_PASSWORD

# Update login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # Changed from email to username
        password = request.form['password']
        
        # Validate input
        if not username or not password:
            return render_template('login.html', 
                                 message='Username and password are required', 
                                 message_type='error')
        
        # Check for admin login
        if username == 'admin' and password == ADMIN_PASSWORD:
            session['user_id'] = 0
            session['user_role'] = 'admin'
            session['user_name'] = 'Administrator'
            return redirect(url_for('admin_panel'))
        
        # Regular user login
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM users 
                WHERE name = %s AND password = %s 
                AND role = 'user'
            """, (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['user_id'] = user['id']
                session['user_role'] = 'user'
                session['user_name'] = user['name']
                flash(f'Welcome back, {user["name"]}!', 'success')
                return redirect(url_for('home'))
            
            return render_template('login.html', 
                                 message='Invalid username or password', 
                                 message_type='error')
        
        return render_template('login.html', 
                             message='Database connection error', 
                             message_type='error')
    
    return render_template('login.html')

# Update signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form['name']
            designation = request.form['designation']
            password = request.form['password']
            
            # Basic validation
            if not all([name, designation, password]):
                return render_template('signup.html', 
                                     message='All fields are required', 
                                     message_type='error')
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                
                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
                if cursor.fetchone():
                    return render_template('signup.html', 
                                         message='User already exists', 
                                         message_type='error')
                
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (name, designation, password, role) 
                    VALUES (%s, %s, %s, 'user')
                """, (name, designation, password))
                
                conn.commit()
                conn.close()
                
                flash('Account created successfully! Please login.')
                return redirect(url_for('login'))
                
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return render_template('signup.html', 
                                 message='Database error occurred', 
                                 message_type='error')
        except Exception as e:
            print(f"Error during signup: {e}")
            return render_template('signup.html', 
                                 message='An error occurred', 
                                 message_type='error')
            
    return render_template('signup.html')
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        if not conn.is_connected():
            raise mysql.connector.Error("Failed to connect to database")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    return render_template('index.html', user_name=session.get('user_name'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/submit_petition', methods=['POST'])
@login_required
def submit_petition():
    name = request.form['name']
    email = request.form['email']
    phone_number = request.form['phone_number']
    address = request.form['address']
    grievance = request.form['grievance']

    try:
        # Use Groq AI to classify, prioritize, and get a solution
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Please classify, prioritize, and provide a solution and contact number or helpline number of government official for the grievance, provide grievance within 255 characters. Return the response in this format:\nCategory: <category>\nPriority: <priority>\nSolution: <solution>"},
                {"role": "user", "content": grievance}
            ]
        )

        response_content = response.choices[0].message.content
        lines = response_content.split("\n")

        category = next((line.split(":")[1].strip() for line in lines if line.startswith("Category:")), "Uncategorized")
        priority = next((line.split(":")[1].strip() for line in lines if line.startswith("Priority:")), "Normal")
        solution = next((line.split(":")[1].strip() for line in lines if line.startswith("Solution:")), "No solution provided")

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO petitions (name, email, phone_number, address, grievance, category, priority, solution) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (name, email, phone_number, address, grievance, category, priority, solution)
            )
            conn.commit()
            conn.close()
        else:
            return "Error connecting to the database", 500

        # Send email to user
        user_msg = Message(
            "Your Grievance Solution",
            recipients=[email]
        )
        user_msg.body = f"Hello {name},\n\nYour grievance has been processed. Here is the solution:\n\nCategory: {category}\nPriority: {priority}\nSolution: {solution}\n\nThank you."
        mail.send(user_msg)

        # Send email to admin
        admin_msg = Message(
            "New Grievance Submitted",
            recipients=[default_email]
        )
        admin_msg.body = f"New grievance submitted:\n\nName: {name}\nEmail: {email}\nPhone: {phone_number}\nAddress: {address}\n\nGrievance: {grievance}\n\nCategory: {category}\nPriority: {priority}\nSolution: {solution}"
        mail.send(admin_msg)

        flash('Grievance submitted successfully!')
        return redirect(url_for('home'))

    except Exception as e:
        print(f"Error during petition submission: {e}")
        flash('Error processing the grievance. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM petitions ORDER BY created_at DESC")
        petitions = cursor.fetchall()
        conn.close()
        return render_template('admin.html', petitions=petitions)
    return "Error fetching petitions", 500

@app.route('/notify/<int:petition_id>', methods=['POST'])
@login_required
@admin_required
def notify_user(petition_id):
    message = request.form['message']
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM petitions WHERE id = %s", (petition_id,))
        petition = cursor.fetchone()

        if petition:
            msg = Message(
                "Update on Your Grievance",
                recipients=[petition['email']]
            )
            msg.body = f"Update regarding your grievance:\n\n{message}"
            mail.send(msg)
            
            cursor.execute("INSERT INTO notifications (petition_id, message) VALUES (%s, %s)", 
                         (petition_id, message))
            conn.commit()
            conn.close()
            flash('Notification sent successfully!')
            return redirect(url_for('admin_panel'))

    flash('Error sending notification', 'error')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)