# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Team Members

- Belle Mbaezue 
- Kathy Lin
- Andy Chi
- Selma Nahas

## Product vision statement

4CAST is a predictive digital wardrobe that helps users make cohesive styling decisions, discover new outfit combinations, maximize the use of clothing they already own, and track garment utilization and textile circularity.

## User stories

[User Stories](https://github.com/lkykathy/web-app-exercise-4CAST/issues)

## Steps necessary to run the software

### Prerequisites

Before running 4CAST, install:

- [Python 3.12](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- Pipenv, Python's virtual environment and dependency manager
- A [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account and database connection string
- An [OpenWeatherMap](https://openweathermap.org/) account and API key

### 1. Clone the repository

Open a terminal and run:

```bash
git clone https://github.com/lkykathy/web-app-exercise-4CAST.git
cd web-app-exercise-4CAST
```

### 2. Install dependencies

Install Pipenv if it is not already installed:

```bash
python3 -m pip install --user pipenv
```

Install the project dependencies specified in the `Pipfile`:

```bash
pipenv install
```

This installs Flask, PyMongo with SRV connection support, python-dotenv, and their dependencies in the project's virtual environment.

### 3. Configure MongoDB Atlas

Create a MongoDB Atlas cluster if one is not already available. Create a database user, configure Network Access to allow your IP address, and copy the cluster's connection string.

### 4. Configure environment variables

Create a file named `env.example` in the project root containing the following placeholders:

```dotenv
MONGO_DBNAME=your_database_name
MONGO_URI=your_mongodb_connection_string
OPENWEATHER_API_KEY=your_openweathermap_api_key
```

Copy the example file to create your local environment configuration:

```bash
cp env.example .env
```

Open `.env` and replace the placeholders with your actual MongoDB database name, connection string, and OpenWeatherMap API key.

Ensure `.env` is included in `.gitignore` so that credentials are not committed to GitHub. Commit `env.example` with placeholder values only.

### 5. Run the application

Activate the project's virtual environment:

```bash
pipenv shell
```

Start the Flask application:

```bash
python app.py
```

If `app.py` does not start the development server directly, run the application through Flask instead:

```bash
pipenv run flask --app app run --debug
```

Once the server starts, open a browser and navigate to:

http://127.0.0.1:5000

To stop the application, press `Ctrl+C` in the terminal.

### Troubleshooting

- **MongoDB connection errors:** Verify the connection string, database credentials, and authorized IP address in MongoDB Atlas.
- **Weather API errors:** Verify that the OpenWeatherMap API key is valid and that `.env` uses the environment variable name expected by the application.
- **Port conflicts:** If port 5000 is already in use, start Flask on port 5001 using `pipenv run flask --app app run --debug --port 5001`, then visit http://127.0.0.1:5001.
- **Missing dependencies:** Run `pipenv install` from the project root and ensure you are using Python 3.12.


## Task boards

[Task Board - Sprint #1](https://github.com/users/lkykathy/projects/1)

[Task Board - Sprint #2](https://github.com/users/lkykathy/projects/2)