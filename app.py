import smtplib
import os
import pyotp
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

app = Flask(__name__)
otp_secrets = {}

def send_otp_email(recipient_email, otp):
    sender_email = os.environ.get('SENDER_EMAIL')  # Replace with your environment variable name for sender email
    sender_password = os.environ.get('SENDER_PASSWORD')
    
    subject = 'One-Time Password (OTP) for Verification'
    message = f'Dear User,\n\nYour One-Time Password (OTP) for verification is: {otp}\n\nPlease enter this OTP on the application to complete the verification process.\n\nThank you for using our service.\n\nBest regards,\nZepp'

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        return jsonify({'Authentication error: Please check your email and password.'})
    except smtplib.SMTPException as e:
        return jsonify({'message':f'An error occurred while sending the email: {e}'})


@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    recipient_email = data.get('email')

    if not recipient_email:
        return jsonify({'error': 'Email is missing'}), 400

    # Check if OTP secret for the email already exists
    if recipient_email not in otp_secrets:
        # Generate the OTP secret for the recipient email if it doesn't exist
        otp_secret = pyotp.random_base32()
        otp_secrets[recipient_email] = otp_secret
    else:
        otp_secret = otp_secrets[recipient_email]

    # Use HOTP for sending OTP via email
    hotp = pyotp.HOTP(otp_secret)
    otp_counter = 0  # Set the initial counter value
    otp = hotp.at(otp_counter)
    send_otp_email(recipient_email, otp)

    # Store the otp_counter in the session
    session['otp_counter'] = otp_counter

    return jsonify({'message': 'OTP sent successfully'}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    recipient_email = data.get('email')
    user_input_otp = data.get('otp')

    if not recipient_email or not user_input_otp:
        return jsonify({'error': 'Email or OTP is missing'}), 400

    # Check if OTP secret for the email exists
    if recipient_email not in otp_secrets:
        return jsonify({'error': 'OTP secret not found. Send OTP first using /send-otp.'}), 400

    otp_secret = otp_secrets[recipient_email]
    hotp = pyotp.HOTP(otp_secret)

    # Retrieve otp_counter from the session
    otp_counter = session.get('otp_counter')

    # For verification, manually check multiple OTPs in the window
    window = 3  # Adjust the window size based on your requirements

    for i in range(otp_counter, otp_counter + window + 1):
        if hotp.verify(user_input_otp, i):
            return jsonify({'message': 'OTP verification successful'}), 200

    return jsonify({'error': 'OTP verification failed'}), 401

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.get_json()
    recipient_email = data.get('email')

    if not recipient_email:
        return jsonify({'error': 'Email is missing'}), 400

    # Check if OTP secret for the email exists
    if recipient_email not in otp_secrets:
        return jsonify({'error': 'OTP secret not found. Send OTP first using /send-otp.'}), 400

    otp_secret = otp_secrets[recipient_email]
    hotp = pyotp.HOTP(otp_secret)
    otp_counter = session.get('otp_counter', 0)  # Get the otp_counter from the session or set to 0 if not present
    otp = hotp.at(otp_counter)
    send_otp_email(recipient_email, otp)

    # Update the otp_counter in the session
    session['otp_counter'] = otp_counter

    return jsonify({'message': 'New OTP sent successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
