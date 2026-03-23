# OriginX

FastAPI-powered platform for verifying image authenticity and detecting manipulated media.

## Overview

OriginX is a backend system designed to analyze uploaded images and determine whether they are authentic or potentially manipulated.
It provides a REST API built with FastAPI that can process images, run verification logic, and return structured results for applications or services that require media verification.

The project is designed to be lightweight, modular, and easy to integrate with web or mobile platforms.

## Features

* Image authenticity verification
* REST API built with FastAPI
* Image upload and analysis endpoints
* Modular backend architecture
* Ready for deployment and integration
* Logging and debugging support

## Tech Stack

* Python
* FastAPI
* Uvicorn
* REST API architecture

## Project Structure

```
OriginX/
│
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   └── utils/
│
├── deployment/
├── scripts/
├── tests/
│
├── requirements.txt
└── README.md
```

## Installation

Clone the repository:

```
git clone https://github.com/Shibin-bs/OriginX.git
cd OriginX
```

Install dependencies:

```
pip install -r requirements.txt
```

Run the server:

```
uvicorn app.main:app --reload
```

The API will start at:

```
http://127.0.0.1:8000
```

## API Documentation

FastAPI automatically generates API documentation.

After running the server, open:

```
http://127.0.0.1:8000/docs
```

This provides an interactive interface to test endpoints.

## Example Workflow

1. Upload an image to the API.
2. The backend processes and analyzes the file.
3. Verification logic runs to detect manipulation.
4. The API returns a response containing authenticity analysis.

## Deployment

The project includes deployment scripts and configuration files to simplify running OriginX in production environments.

Refer to:

* `DEPLOYMENT_STATUS.md`
* `START_PRODUCTION.md`

## Author

Mohammed Shibin B S

## License

This project is currently provided for educational and experimental purposes.
