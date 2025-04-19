import os

class Config:
    """Configurazione base dell'applicazione Flask"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'valtservice_secret_key_default'
    
    # Directory di base per i file dell'applicazione
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Directory per i file di dati
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # Directory per i file caricati
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    
    # Estensioni di file permesse
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    
    # Dimensione massima dei file caricati (10 MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    # Template predefiniti per le intestazioni/piè di pagina PDF
    PDF_HEADER_TEMPLATE = os.path.join(BASE_DIR, 'templates', 'pdf', 'header.html')
    PDF_FOOTER_TEMPLATE = os.path.join(BASE_DIR, 'templates', 'pdf', 'footer.html')
    
    # Numero massimo di offerte nella cronologia (0 = illimitato)
    MAX_HISTORY_ITEMS = 0
    
    @staticmethod
    def init_app(app):
        """Inizializza l'applicazione con la configurazione corrente"""
        # Crea le directory necessarie
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Imposta le configurazioni nell'oggetto app
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        app.config['DATA_DIR'] = Config.DATA_DIR
        app.config['ALLOWED_EXTENSIONS'] = Config.ALLOWED_EXTENSIONS
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

class DevelopmentConfig(Config):
    """Configurazione per l'ambiente di sviluppo"""
    DEBUG = True

class ProductionConfig(Config):
    """Configurazione per l'ambiente di produzione"""
    DEBUG = False
    
    # In produzione, usa un secret key più sicuro
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'difficile_da_indovinare_secret_key'
    
    # Opzioni di sicurezza aggiuntive per l'ambiente di produzione
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # Aggiungi configurazioni di sicurezza specifiche per l'ambiente di produzione
        pass

class SynologyConfig(ProductionConfig):
    """Configurazione specifica per il deployment su NAS Synology"""
    
    # Verifica se siamo su un NAS Synology (tramite environment variable o file)
    @staticmethod
    def is_synology():
        """Verifica se l'applicazione è in esecuzione su un NAS Synology"""
        # Questa è una semplificazione, dovresti usare un metodo specifico
        return os.path.exists('/etc/synology-release')
    
    @staticmethod
    def init_app(app):
        ProductionConfig.init_app(app)
        
        # Se siamo su Synology, usa percorsi specifici
        if SynologyConfig.is_synology():
            # Adatta i percorsi per l'ambiente Synology
            app.config['DATA_DIR'] = '/volume1/web/app_offerte/data'
            app.config['UPLOAD_FOLDER'] = '/volume1/web/app_offerte/static/uploads'
            
            # Crea le directory se non esistono
            os.makedirs(app.config['DATA_DIR'], exist_ok=True)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dizionario di configurazione per permettere la selezione da variabile d'ambiente
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'synology': SynologyConfig,
    'default': DevelopmentConfig
}