# 🚀 Smart Referral Hub - Backend Server

A robust Flask-based backend server that powers the Smart Referral Hub platform, providing secure API endpoints for user management, referral tracking, and reward distribution.

## 🛠 Tech Stack

- **Framework**: Flask 3.1.0
- **Authentication**: JWT (PyJWT)
- **Database**: AWS DynamoDB
- **Storage**: AWS S3
- **Security**: 
  - Password Hashing (Werkzeug)
  - CORS Protection
  - reCAPTCHA Integration
- **Deployment**: Gunicorn 23.0.0

## 🏗 Project Structure

```
backend/
├── application.py        # Main application file with all route handlers
├── init_links.py        # Initial setup for referral links
├── requirements.txt     # Project dependencies
├── models/             # Data models
│   ├── user.py         # User model definition
│   └── referral_link.py # Referral link model
├── services/           # External service integrations
│   └── aws_service.py  # AWS (DynamoDB, S3) interactions
└── utils/             # Utility functions
    └── auth.py        # Authentication helpers
```

## 🔑 Key Features

### 👤 User Management
- Customer signup and login
- JWT-based authentication
- Password hashing
- Terms acceptance tracking

### 📊 Referral System
- File upload management
- Referral tracking
- Points calculation
- Discount generation

### 🏢 Company Management
- Company information handling
- Multi-company support
- Company verification

### 🔗 Link Management
- Dynamic link generation
- Link updating
- Step-specific link handling

### 📁 File Management
- Secure file uploads to S3
- Media file downloads
- File type validation

### 👥 Client Management
- Client listing
- Form approval system
- Referral number tracking

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone [repository-url]
   cd backend
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file with:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=your_region
   RECAPTCHA_SECRET_KEY=your_recaptcha_key
   ```

5. **Run the application**
   ```bash
   python application.py
   ```

## 🔒 Security Features

- Password hashing using Werkzeug
- JWT token-based authentication
- CORS protection with specific origin allowlist
- reCAPTCHA verification
- Secure file upload validation
- AWS credentials management

## 🌐 API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/check-auth` - Check authentication status

### File Management
- `POST /api/upload` - Upload files
- `GET /api/download-media/<encoded_key>` - Download media files

### Referral Management
- `POST /api/submit` - Submit referral form
- `GET /api/get-discount` - Get discount information
- `POST /api/update-referrals` - Update referral numbers

### Company Management
- `POST /api/add-company` - Add new company
- `GET /api/company-name` - Get company information
- `POST /api/company-exists` - Check company existence

### Client Management
- `GET /api/clients` - Get all clients
- `POST /api/approve-form` - Approve/disapprove submissions

### Link Management
- `GET /api/step-links/<step_name>` - Get step-specific links
- `POST /api/update-link` - Update link information

## 📡 CORS Configuration

The server is configured to accept requests from:
- `https://app.smartreferralhub.com`
- `http://localhost:5173` (development)

## 🔧 AWS Configuration

The application requires AWS services:
- **DynamoDB**: For user and referral data storage
- **S3**: For file storage and media handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

[License Type] - See LICENSE file for details
