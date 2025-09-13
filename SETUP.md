# OTP Project Setup Guide

This guide will help you set up and run the OTP (One-Time Password) project on your local machine.

We are using pyotp ONLY for generating random Base32 secrets, NOT for the actual OTP algorithm!

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Installation Steps

### 1. Clone the Repository
```bash
git clone <your-github-repo-url>
cd OTP-project
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Navigate to backend directory
cd backend

# Install all required packages
pip install -r requirements.txt
```

### 4. Set Up Database
The database will be created automatically when you first run the application. No manual setup required!

### 5. Run the Application
```bash
# Make sure you're in the backend directory
cd backend

# Start the Flask server
python app.py
```

### 6. Access the Application
Open your web browser and go to:
- **Main page**: http://127.0.0.1:5000
- **Registration**: http://127.0.0.1:5000/Register.html
- **Login**: http://127.0.0.1:5000/Login.html

## Project Structure

```
OTP-project/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── api_v2.py           # API endpoints (multi-user)
│   ├── routes.py           # API endpoints (single-user)
│   ├── models.py           # Database models
│   ├── requirements.txt    # Python dependencies
│   └── README.md
├── frontend/
│   ├── Login.html          # Login page
│   ├── Register.html       # Registration page
│   ├── input_otp.html      # OTP verification page
│   ├── input_otp.css       # Styling
│   ├── input_otp.js        # JavaScript functionality
│   └── ...                 # Other frontend files
├── database/
│   ├── db_manager.py       # Database operations
│   ├── setup_database.py  # Database initialization
│   └── database/           # Database files (auto-created)
├── core/
│   ├── otp_core.py         # OTP generation logic
│   └── ...                 # Other core modules
├── .gitignore              # Files to ignore in Git
└── SETUP.md               # This file
```

## How to Use

### 1. Register a New User
1. Go to http://127.0.0.1:5000/Register.html
2. Fill in username, password, email, and phone
3. Click "Register"
4. **Save the OTP secret** that appears in the alert!

### 2. Login
1. Go to http://127.0.0.1:5000/Login.html
2. Enter your username and password
3. Click "Submit"

### 3. Set Up Authenticator App
1. After login, you'll see a QR code
2. Open Google Authenticator (or any TOTP app) on your phone
3. Tap "Add Account" → "Scan QR Code"
4. Point your camera at the QR code on the screen
5. Your account will be added to the authenticator app

### 4. Verify OTP
1. Open your authenticator app
2. Get the 6-digit code for your account
3. Enter the code in the input fields on the webpage
4. Click "Verify account"

## Troubleshooting

### Common Issues

**Port 5000 already in use:**
```bash
# Kill any process using port 5000
# On Windows:
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# On macOS/Linux:
lsof -ti:5000 | xargs kill -9
```

**Database errors:**
- Delete the `database/database/` folder and restart the application
- The database will be recreated automatically

**Import errors:**
- Make sure you're in the correct directory (`backend/`)
- Ensure all dependencies are installed: `pip install -r requirements.txt`

**QR code not showing:**
- Check browser console for errors (F12)
- Ensure you're logged in with a valid user

## API Endpoints

### Registration
- **POST** `/api/v2/register`
- Body: `{"username": "user", "password": "pass", "email": "email", "phone": "phone"}`

### Login
- **POST** `/api/v2/login`
- Body: `{"username": "user", "password": "pass"}`

### Get QR Code
- **GET** `/api/v2/qr_code/{username}`

### Verify OTP
- **POST** `/api/v2/verify_totp/{username}`
- Body: `{"code": "123456"}`

## Security Notes

- Never commit the `database/` folder to Git
- The `.gitignore` file protects sensitive data
- OTP secrets are stored securely in the database
- Passwords are hashed using Werkzeug

## Need Help?

If you encounter any issues:
1. Check this setup guide
2. Look at the console output for error messages
3. Ensure all dependencies are installed
4. Try deleting the database folder and restarting

Happy coding! 🚀
