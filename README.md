# Logic Coverage App

A small Flask app for exploring logic coverage criteria from a boolean predicate.

## Quickstart

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the app

```bash
python3 app.py
```

Open your browser at:

<http://127.0.0.1:5000>

## If port 5000 is already in use

Run Flask on another port:

```bash
python3 -m flask --app app run --debug --port 5001
```

Then open:

<http://127.0.0.1:5001>

## Run tests

```bash
pytest -q
```

## Project files

- `app.py`: Flask web interface
- `logic_coverage.py`: core logic coverage computations
- `test_logic_coverage.py`: automated tests
