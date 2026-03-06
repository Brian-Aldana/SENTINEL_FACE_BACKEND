from api import create_app

app = create_app()

if __name__ == "__main__":
    import os
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=5000)