from flask import Flask
import monitor  # Import your existing script
import threading

app = Flask(__name__)

@app.route('/trigger')
def trigger_monitor():
    # Run in a separate thread so the web request doesn't wait
    threading.Thread(target=monitor.run_logic).start()
    return "Monitor started", 200

if __name__ == '__main__':
    app.run(port=5000)
