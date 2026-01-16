from app import create_app
from dotenv import load_dotenv

load_dotenv()

app = create_app()

if __name__ == '__main__':
    print("Backend Server running on http://127.0.0.1:5002")
    app.run(debug=False, port=5002, host='0.0.0.0')
