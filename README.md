# 🌱 Carbon Footprint Tracker

A comprehensive web application built with Streamlit to help individuals track, analyze, and reduce their environmental impact by monitoring their daily carbon footprint across multiple categories.

## Features

### 🔐 User Authentication
- Secure user registration and login system
- Password hashing for security
- User profile management
- Admin dashboard for system management

### 📊 Carbon Footprint Tracking
- **Home Energy**: Track electricity, natural gas, and water usage
- **Transportation**: Monitor car travel, public transit, and flights
- **Food Consumption**: Log meat, dairy, and plant-based meals
- Real-time carbon footprint calculations with industry-standard emission factors

### 📈 Analytics & Visualization
- Interactive dashboards with trend analysis
- Comprehensive history tracking
- Category-wise carbon breakdown with pie charts
- Time-series visualization of carbon footprint trends
- Comparison with global averages

### 🔥 Gamification
- Daily streak tracking to encourage consistent logging
- Personal best streak records
- Achievement system to motivate users

### 👤 User Management
- Detailed user profiles with customizable information
- Password change functionality
- Admin panel for user and data management

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd carbon-footprint-tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Access the application**
   - Open your web browser and navigate to `http://localhost:8501`
   - The application will automatically create the SQLite database on first run

## Usage

### Getting Started

1. **Register an Account**
   - Click "Register" on the login page
   - Fill in your personal information
   - Create a secure password

2. **Track Your Carbon Footprint**
   - Navigate to the "Calculate" page
   - Enter your daily activities across different categories
   - The system automatically calculates your total carbon footprint

3. **Monitor Your Progress**
   - View your dashboard for comprehensive analytics
   - Check your streak and achievement progress
   - Analyze trends and patterns in your carbon emissions

### Admin Features

The application includes a default admin account:
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change the default admin password immediately after first login for security.

Admin capabilities include:
- View all users and their activity
- Monitor system-wide carbon footprint data
- Access database statistics and health checks
- Manage user accounts

## Carbon Footprint Calculations

The application uses the following emission factors:

| Category | Emission Factor |
|----------|----------------|
| Electricity | 0.4 kg CO2/kWh |
| Natural Gas | 5.3 kg CO2/therm |
| Water | 0.0002 kg CO2/gallon |
| Car Travel | 8.887 kg CO2/gallon (assuming 25 MPG) |
| Public Transit | 0.17 kg CO2/mile |
| Short-haul Flights | 500 kg CO2/flight |
| Long-haul Flights | 1600 kg CO2/flight |
| Meat | 3.0 kg CO2/serving |
| Dairy | 0.7 kg CO2/serving |
| Plant-based | 0.2 kg CO2/serving |

## Database Schema

The application uses SQLite with the following main tables:

- **users**: User account information and profiles
- **carbon_footprint**: Daily carbon footprint entries
- **user_streaks**: Streak tracking and user statistics

## Technology Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **Visualization**: Plotly
- **Data Processing**: Pandas

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## Security Considerations

- Passwords are hashed using SHA-256
- SQLite database with parameterized queries to prevent SQL injection
- Session management through Streamlit's session state
- Admin privileges are properly controlled

## Future Enhancements

- [ ] Data export functionality (CSV, PDF reports)
- [ ] Social features (sharing achievements, challenges)
- [ ] Mobile app integration
- [ ] API for third-party integrations
- [ ] Advanced analytics and predictions
- [ ] Carbon offset recommendations
- [ ] Integration with smart home devices
- [ ] Multi-language support

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, questions, or feature requests, please open an issue in the repository or contact the development team.

## Acknowledgments

- Emission factors based on EPA and international environmental standards
- Built with the Streamlit community's excellent documentation and examples
- Inspired by the global movement towards environmental awareness and sustainability
