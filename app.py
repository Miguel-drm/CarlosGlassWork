from datetime import datetime
from Website import create_app
import os

app = create_app()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
