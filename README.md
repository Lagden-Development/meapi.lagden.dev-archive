# MeAPI - Personal API Aggregator

## Project Overview

MeAPI is a web application that allows users to create a personal API to expose and share their service data (like Spotify listening history) through a unified, customizable interface. It provides easy API key management, service toggling, and usage statistics.

> **Note:** This repository is an archive of the MeAPI project which was previously available at meapi.lagden.dev but has since been shut down.

![MeAPI Dashboard](https://meapi.lagden.dev/static/images/dashboard.png)

## Features

- **User Authentication**
  - Automatic username and password generation
  - Secure credential storage
  - Session management

- **API Key Management**
  - Generate and regenerate API keys
  - Public and private API endpoints
  - Copy key functionality with blur protection

- **Service Integration**
  - Spotify integration to share listening history and currently playing tracks
  - Enable/disable service toggles
  - Public/private visibility controls
  - OAuth2 setup flow for service authorization

- **Dashboard**
  - Usage statistics and graphs
  - API request tracking
  - Account information
  - Recent activity logs

## Technical Stack

- **Backend**
  - Flask web framework
  - MongoDB database
  - Flask extensions (Session, Minify)
  - OAuth2 integration

- **Frontend**
  - Tailwind CSS for styling
  - JavaScript/jQuery for interactivity
  - Chart.js for data visualization
  - D3.js for color schemes and advanced visualizations
  - Responsive design

## Project Structure

```
├── app.py                   # Main Flask application
├── db.py                    # MongoDB connection setup
├── serve.py                 # Production server using waitress
├── requirements.txt         # Python dependencies
├── config.py                # Configuration (not included in repository)
├── data/
│   └── services.json        # Service definitions and routes
├── endpoints/
│   ├── main_endpoints.py    # Main page routes
│   ├── service_setup_endpoints.py # Service connection flows
│   └── api/                 # API endpoints
│       ├── account_endpoints.py    # User account management
│       ├── service_endpoints.py    # Service management
│       └── services/        # Service-specific endpoints
│           └── spotify_endpoints.py # Spotify API integration
├── static/
│   └── css/                 # CSS files
│       ├── base.css         # Tailwind source
│       └── tailwind.css     # Compiled CSS
└── templates/               # HTML templates
    ├── base.html            # Base template
    ├── navbar.html          # Navigation component
    ├── dashboard.html       # Main dashboard
    ├── login_register.html  # Authentication page
    ├── api.html             # API management page
    ├── services.html        # Services listing
    └── services/            # Service-specific templates
        └── service.html     # Individual service page
```

## API Endpoints

MeAPI provides several API endpoints for accessing your service data:

### Spotify Service
- **Public Endpoint**: `/api/spotify/listening/<string:uuid>`
- **Private Endpoint**: `/api/spotify/listening/<string:uuid>?api_key=<string:api_key>`
- **Description**: Returns your current Spotify status and recently played tracks

### Account Management
- `/api/account/login` - User authentication
- `/api/account/register` - User registration
- `/api/account/regenerate_api_key` - Generate new API key

### Service Management
- `/api/service/<serviceId>/enable` - Enable a service
- `/api/service/<serviceId>/disable` - Disable a service
- `/api/service/<serviceId>/make_public` - Make service publicly accessible
- `/api/service/<serviceId>/make_private` - Restrict service to API key access

## Setup and Installation

⚠️ **Note**: This repository is for reference only as the service has been shut down. If you want to run your own instance, you would need to:

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `config.py` file with your MongoDB URI and service credentials (not included in the repo)

3. Generate Tailwind CSS:
   ```
   npx tailwindcss -i ./static/css/base.css -o ./static/css/tailwind.css
   ```

4. Run the development server:
   ```
   python app.py
   ```

5. Or use the production server:
   ```
   python serve.py
   ```

## Authentication Flow

1. Users receive randomly generated usernames and passwords
2. Password is shown only once during registration
3. If a user forgets their password, they must create a new account

## Setting Up Services

### Spotify
1. Navigate to Services > Spotify
2. Click "Start Setup"
3. Authorize MeAPI to access your Spotify data
4. After authorization, your Spotify listening data will be available via the API

## Usage Examples

### Fetching Spotify Data
```javascript
// Public endpoint
fetch('https://meapi.lagden.dev/api/spotify/listening/your-uuid')
  .then(response => response.json())
  .then(data => console.log(data));

// Private endpoint with API key
fetch('https://meapi.lagden.dev/api/spotify/listening/your-uuid?api_key=your-api-key')
  .then(response => response.json())
  .then(data => console.log(data));
```

## Security Considerations

- API keys should be kept secure
- The service uses HTTPS to encrypt data in transit
- All passwords are hashed before storage
- Spotify tokens are refreshed automatically

## Credits and License

© 2024 Zachariah Michael Lagden (All Rights Reserved)

This code is provided as reference only and may not be used, copied, distributed, modified, or sold without the express permission of the author.

## Contact

For questions about this archived project, you can reach out via:
- Email: contact@lagden.dev
- Discord: https://discord.gg/zXumZ5jsBF

---

**MeAPI** was a project that allowed users to easily expose their service data through a personal API. Although it's now shut down, this repository serves as an archive and reference for similar projects.