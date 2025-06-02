from datetime import datetime
from Website import create_app

app = create_app()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)
