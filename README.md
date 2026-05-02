# G8BikeShare — Dublin Bike-Sharing Web Application

**(Developers: Hao Zhang, Yu Ning Chen, and Limu Zhang)**

G8BikeShare is a web application designed to improve the experience of using Dublin Bikes. The central problem it addresses is the uncertainty users face when relying on the service: arriving at a station to find it empty, returning a bike to a full station, or deciding whether weather conditions make cycling viable.

G8BikeShare solves this by combining three live data sources — the JCDecaux Dublin Bikes API, the OpenWeatherMap API, and a locally scraped historical database — with a Gemini-powered AI assistant and a machine learning availability predictor. The system is deployed on AWS EC2 and accessible via a browser.

![Website Mockup Image](/docs/features/homepage-final.png)

---

## Table of Contents

- [G8BikeShare](#g8bikeshare--dublin-bike-sharing-web-application)
  * [Table of Contents](#table-of-contents)
  * [Features](#features)
    + [Live Station Map](#live-station-map)
    + [Weather Dashboard](#weather-dashboard)
    + [Journey Planner](#journey-planner)
    + [48-Hour Availability Trend](#48-hour-availability-trend)
    + [AI Bike Assistant](#ai-bike-assistant)
    + [User Login](#user-login)
  * [Mockups vs. Production](#mockups-vs-production)
  * [Machine Learning Model](#machine-learning-model)
  * [Technologies Used](#technologies-used)
    + [Languages and Frameworks](#languages-and-frameworks)
    + [Resources and Tools](#resources-and-tools)
  * [Testing](#testing)
  * [Deployment](#deployment)
    + [EC2 Deployment](#ec2-deployment)
    + [Fork](#fork)
    + [Clone](#clone)

---

## Features

### Live Station Map

The interactive map is a core feature of the application, dynamically rendered using live data fetched from the JCDecaux Dublin Bikes API. Each of Dublin's bike stations is represented by a colour-coded clickable marker showing real-time bike and dock availability. Clicking a marker opens a sidebar with full station details, a 48-hour historical trend chart, AI assistant recommendations, and a machine learning prediction of future availability. Users can also search by station name or filter by available bike count using the controls above the map.

![screenshot](/docs/features/map-final.png)
![screenshot](/docs/features/station-sidebar.png)

### Weather Dashboard

The weather page pulls live data from the OpenWeatherMap API and renders current temperature, feels-like temperature, humidity, wind speed, and weather condition. A ride-suitability verdict helps users decide at a glance whether conditions are suitable for cycling. A 5-day forecast is visualised as line and bar charts.

![screenshot](/docs/features/weather-dashboard.png)

### Journey Planner

Users select a preferred origin station from a dropdown (showing available bikes and docks) and enter a destination address. Clicking **Open in Google Maps** launches Google Maps with bicycling mode pre-selected and the station's coordinates as the origin, allowing users to move from station selection to turn-by-turn navigation with minimal friction.

![screenshot](/docs/features/journey-planner.png)

### 48-Hour Availability Trend

The dashboard sidebar includes a Chart.js visualisation of the selected station's hourly average availability over the previous 48 hours, computed from the scraped historical database. Users toggle between three views: occupancy percentage, average available bikes, and average available docks. A narrative summary beneath the chart highlights peak occupancy and the most recent data point.

![screenshot](/docs/features/trend-chart.png)

### AI Bike Assistant

A Gemini-powered chatbot allows users to ask natural-language questions about station availability, weather conditions, and cycling routes. Each request is sent with a structured prompt containing live weather data, the currently selected station snapshot, a list of top available stations, and recent conversation history. The backend returns an AI response together with weather context and, where a station can be inferred from the reply, the dashboard highlights that station on the map. A rule-based fallback assistant provides immediate advice when the AI is unavailable.

![screenshot](/docs/features/ai-assistant.png)

### User Login

Users can create an account or sign in through the authentication pages. After successful login, the username is displayed in the navigation bar to confirm the active session. Basic input validation is applied to improve usability and reduce invalid submissions.

![screenshot](/docs/features/log-in-final.png)
![screenshot](/docs/features/sign-up-final.png)

---

## Mockups vs. Production

- **Homepage**
  - Mockup:
    ![screenshot](/docs/mockup/dublinbikes-mockup.png)
  - Final:
    ![screenshot](/docs/features/homepage-final.png)

- **Map (Find a Bike)**
  - Mockup:
    ![screenshot](/docs/mockup/map-mockup.png)
  - Final:
    ![screenshot](/docs/features/map-final.png)

---

## Machine Learning Model

G8BikeShare includes a machine learning component that predicts the number of available bikes (`num_bikes_available`) at any Dublin Bikes station for the upcoming 24 hours, helping users plan journeys during high-demand periods.

**Features used:** hour of day, day of week, is_holiday, station_id, temperature, humidity, wind speed, weather condition code, and precipitation probability.

**Models evaluated:**

| Model | MAE | R² |
|---|---|---|
| Linear Regression | 8.14 | 0.00 |
| Decision Tree | 1.02 | 0.93 |
| **Random Forest** ☑️ | **0.98** | **0.97** |
| XGBoost | 5.43 | 0.52 |

**Random Forest** was selected as the final model for its lowest MAE (< 1 bike average error) and highest R² score, offering the best balance of accuracy, stability, and deployment suitability. Training occurs offline; dashboard predictions are fast enough for interactive use.

The full ML code (data cleaning notebook, training script, and evaluation notebook) is available in the `/ml` directory of this repository.

---

## Technologies Used

### Languages and Frameworks

- [HTML](https://en.wikipedia.org/wiki/HTML) — Web content structure.
- [CSS](https://en.wikipedia.org/wiki/CSS) — Styling and layout.
- [JavaScript](https://en.wikipedia.org/wiki/JavaScript) — Frontend interactivity.
  - [Chart.js](https://www.chartjs.org/) — 48-hour trend charts and weather forecast visualisations.
  - [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript) — Interactive station map.
- [Python](https://www.python.org/) — Backend logic, data scraping, and machine learning.
  - [Flask](https://flask.palletsprojects.com/) — Web framework and REST API.
  - [pytest](https://pytest.org/) — Automated backend unit testing.
  - [scikit-learn](https://scikit-learn.org/) — Machine learning model training and evaluation.
- [MySQL](https://www.mysql.com/) — Relational database for station, availability, weather, and user data.

### Resources and Tools

- [Visual Studio Code](https://code.visualstudio.com/) — Development environment.
- [Git](https://git-scm.com/) and [GitHub](https://github.com/) — Version control and collaboration.
- [Jira](https://www.atlassian.com/software/jira) — Sprint and backlog management.
- [JCDecaux API](https://developer.jcdecaux.com/) — Real-time Dublin Bikes station data.
- [OpenWeatherMap API](https://openweathermap.org/api) — Live weather data and forecasts.
- [Google Gemini API](https://ai.google.dev/) — AI assistant natural-language responses.
- [AWS EC2](https://aws.amazon.com/ec2/) — Cloud deployment (Ubuntu, free tier).
- [Figma](https://www.figma.com/) — UI wireframes and mockups.
- [WhatsApp](https://www.whatsapp.com/) and [Zoom](https://zoom.us/) — Team communication.
- [HTML W3C Validator](https://validator.w3.org/) — HTML markup validation.
- [CSS Jigsaw Validator](https://jigsaw.w3.org/css-validator/) — CSS validation.

---

## Testing

Testing was conducted across three levels:

**1. HTML & CSS Validation** — All pages were validated using the W3C HTML Validator and W3C CSS Jigsaw Validator with no errors.

**2. Automated Backend Unit Testing** — A pytest suite of 23 tests was implemented using Flask's built-in test client. External API calls were mocked to keep tests deterministic. The suite covers page routes, weather endpoints, authentication validation, and JSON API responses. Final results: **23/23 tests passing**, 48% total line coverage (49% for `app.py`, 41% for `ml_predictor.py`).

**3. Manual Testing** — All pages (Homepage, Dashboard, Journey, Weather, About, Login) were manually tested against defined test cases covering navigation, API rendering, geolocation, AI interaction, and responsive design. All tests passed. One documented constraint: the browser Geolocation API requires HTTPS; the EC2 deployment currently runs over HTTP, so "Locate Me" is fully functional on localhost but restricted on the live deployment. Planned resolution: serve EC2 over HTTPS.

Full manual test cases are documented in the project report.

---

## Deployment

### EC2 Deployment

The application is deployed on an AWS EC2 instance running Ubuntu (free tier). The following services run on the instance:

- **Flask app** — serves the web application and REST API.
- **Bike scraper** — continuously polls the JCDecaux API and writes to MySQL.
- **Weather scraper** — continuously polls OpenWeatherMap and writes to MySQL.
- **MySQL** — stores all station, availability, weather, and user data.

To deploy on your own EC2 instance:

1. Launch an Ubuntu EC2 instance and open ports 22 (SSH) and 5000 (Flask) in the security group.
2. SSH into the instance and install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv mysql-server -y
   ```
3. Clone the repository and install Python requirements:
   ```bash
   git clone https://github.com/COMP30830-G8-DublinBikes/DublinBikes.git
   cd DublinBikes
   pip install -r requirements.txt
   ```
4. Configure your `.env` file with your API keys and MySQL credentials:
   ```
   JCDECAUX_API_KEY=your_key
   OPENWEATHER_API_KEY=your_key
   GEMINI_API_KEY=your_key
   DB_HOST=localhost
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=g8bikeshare
   ```
5. Initialise the database schema, then run the Flask app and scrapers:
   ```bash
   python app.py
   python scraper_bikes.py &
   python scraper_weather.py &
   ```

### Fork

1. Log in to GitHub and locate this repository.
2. Click the **Fork** button at the top right of the repository page.
3. You will now have a copy of the repository in your own GitHub account.

### Clone

1. On the repository page, click the **Code** button and copy the URL.
2. In your terminal, run:
   ```bash
   git clone https://github.com/COMP30830-G8-DublinBikes/DublinBikes.git
   ```
3. Navigate into the project directory:
   ```bash
   cd DublinBikes
   ```
