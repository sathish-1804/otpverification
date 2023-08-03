import smtplib
import os
import pyotp
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

app = Flask(__name__)

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

    # Generate the OTP using pyotp with counter-based HOTP
    otp_secret = pyotp.random_base32()
    hotp = pyotp.HOTP(otp_secret)
    otp_counter = 0  # Set the initial counter value

    # Send the OTP via email
    otp = hotp.at(otp_counter)
    send_otp_email(recipient_email, otp)

    return jsonify({'message': 'OTP sent successfully'}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    recipient_email = data.get('email')
    user_input_otp = data.get('otp')

    if not recipient_email or not user_input_otp:
        return jsonify({'error': 'Email or OTP is missing'}), 400

    # Generate the OTP using pyotp with counter-based HOTP
    otp_secret = pyotp.random_base32()
    hotp = pyotp.HOTP(otp_secret)
    otp_counter = 0  # Set the initial counter value

    # For verification, manually check multiple OTPs in the window
    window = 3  # Adjust the window size based on your requirements

    for i in range(otp_counter, otp_counter + window + 1):
        if hotp.verify(user_input_otp, i):
            return jsonify({'message': 'OTP verification successful'}), 200

    return jsonify({'error': 'OTP verification failed'}), 401

if __name__ == '__main__':
    app.run(debug=True)
