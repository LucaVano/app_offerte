import os
from app import app as application
from waitress import serve
import logging

# Configurazione di logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

if __name__ == '__main__':
    # Ottieni la porta dall'ambiente o usa il default 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Determina se in ambiente di produzione
    is_production = os.environ.get('FLASK_ENV') != 'development'
    
    if is_production:
        # Usa Waitress in produzione
        logging.info(f"Avvio server in modalità produzione sulla porta {port}")
        serve(application, host='0.0.0.0', port=port, threads=4)
    else:
        # Usa il server di sviluppo Flask
        logging.info(f"Avvio server in modalità sviluppo sulla porta {port}")
        application.run(host='0.0.0.0', port=port, debug=True)