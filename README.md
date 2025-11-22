# LauzHack API

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

Start the server with:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Documentation

Interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Endpoints

- `POST /api/v1/instructions/process`: Send instructions and get them back.
