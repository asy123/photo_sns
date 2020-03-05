from app import app as App
import app.config
import app.views

if __name__ == '__main__':
    App.run(debug=True)
