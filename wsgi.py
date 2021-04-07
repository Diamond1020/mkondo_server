from flask_cors import CORS

from app import init_app

app = init_app()

cors = CORS(app, origins="*")

if __name__ == '__main__':
    app.run()
