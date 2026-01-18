from app import create_app


app = create_app()


if __name__ == "__main__":
    # Production-like run (no reloader, no debug) for stability in this env
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
