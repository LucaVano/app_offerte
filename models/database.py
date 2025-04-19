import os
import json
import datetime
import uuid
import shutil

class Database:
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.counter_file = os.path.join(data_folder, "counter.json")
        self.index_file = os.path.join(data_folder, "offerte_index.json")
        
        # Assicurati che i file di database esistano
        self._initialize_database()
    
    def _initialize_database(self):
        """Inizializza i file di database se non esistono"""
        os.makedirs(self.data_folder, exist_ok=True)
        
        # Inizializza il file contatore se non esiste
        if not os.path.exists(self.counter_file):
            current_year = str(datetime.datetime.now().year)
            counter = {current_year: 0}
            with open(self.counter_file, 'w') as f:
                json.dump(counter, f)
        
        # Inizializza l'indice delle offerte se non esiste
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)
    
    def get_next_offer_number(self, custom_number=None, update_counter=False):
        """Genera il prossimo numero di offerta nel formato YYYY-XXXX"""
        if custom_number and update_counter:
            try:
                year, number = custom_number.split('-')
                number = int(number)
                counter = self._load_counter()
                counter[year] = number
                self._save_counter(counter)
                return custom_number
            except:
                # In caso di errore nel formato, genera un nuovo numero
                pass
        
        current_year = str(datetime.datetime.now().year)
        counter = self._load_counter()
        
        if current_year not in counter:
            counter[current_year] = 0
        
        counter[current_year] += 1
        self._save_counter(counter)
        
        return f"{current_year}-{counter[current_year]:04d}"
    
    def _load_counter(self):
        """Carica il contatore delle offerte"""
        try:
            with open(self.counter_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            current_year = str(datetime.datetime.now().year)
            counter = {current_year: 0}
            self._save_counter(counter)
            return counter
    
    def _save_counter(self, counter):
        """Salva il contatore delle offerte"""
        with open(self.counter_file, 'w') as f:
            json.dump(counter, f)
    
    def get_all_offerte(self):
        """Restituisce tutte le offerte dall'indice"""
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def get_offerta(self, offerta_id):
        """Ottiene una singola offerta dall'ID"""
        index = self.get_all_offerte()
        for offerta in index:
            if offerta.get('id') == offerta_id:
                # Carica il file JSON completo dell'offerta
                json_path = os.path.join(self.data_folder, offerta['customer'].upper(), 
                                        offerta['offer_number'], "dati_offerta.json")
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        offerta_completa = json.load(f)
                        offerta_completa['id'] = offerta_id  # Aggiungi l'ID per riferimento
                        return offerta_completa
                except:
                    return offerta  # Restituisce i dati di indice se il file completo non è disponibile
        return None
    
    def save_offerta(self, data):
        """Salva una nuova offerta e restituisce l'ID"""
        # Assegna un ID univoco
        offerta_id = str(uuid.uuid4())
        data['id'] = offerta_id
        
        # Assegna il numero di offerta se non fornito
        if not data.get('offer_number'):
            data['offer_number'] = self.get_next_offer_number()
        
        # Crea le cartelle per il cliente e l'offerta
        customer_folder = os.path.join(self.data_folder, data['customer'].upper())
        offer_folder = os.path.join(customer_folder, data['offer_number'])
        os.makedirs(offer_folder, exist_ok=True)
        
        # Salva il file JSON completo
        json_path = os.path.join(offer_folder, "dati_offerta.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Aggiorna l'indice
        index = self.get_all_offerte()
        index_entry = {
            'id': offerta_id,
            'offer_number': data['offer_number'],
            'date': data['date'],
            'customer': data['customer'],
            'customer_email': data['customer_email'],
            'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
        }
        index.append(index_entry)
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4, ensure_ascii=False)
        
        return offerta_id
    
    def update_offerta(self, offerta_id, data):
        """Aggiorna un'offerta esistente"""
        existing_offerta = self.get_offerta(offerta_id)
        if not existing_offerta:
            return False
        
        # Conserva l'ID originale
        data['id'] = offerta_id
        
        # Gestisci il caso in cui il cliente o il numero di offerta cambi
        old_customer = existing_offerta.get('customer', '').upper()
        old_offer_number = existing_offerta.get('offer_number', '')
        
        new_customer = data.get('customer', '').upper()
        new_offer_number = data.get('offer_number', '')
        
        old_folder = os.path.join(self.data_folder, old_customer, old_offer_number)
        new_folder = os.path.join(self.data_folder, new_customer, new_offer_number)
        
        # Salva il nuovo file JSON
        os.makedirs(os.path.dirname(new_folder), exist_ok=True)
        json_path = os.path.join(new_folder, "dati_offerta.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Se la posizione è cambiata, sposta tutti i file
        if old_folder != new_folder and os.path.exists(old_folder):
            if not os.path.exists(new_folder):
                os.makedirs(new_folder, exist_ok=True)
            
            # Copia tutti i file dalla vecchia alla nuova cartella
            for filename in os.listdir(old_folder):
                if filename != "dati_offerta.json":  # Skip del file JSON che abbiamo già riscritto
                    shutil.copy2(
                        os.path.join(old_folder, filename),
                        os.path.join(new_folder, filename)
                    )
            
            # Cancella la vecchia cartella se è vuota
            try:
                shutil.rmtree(old_folder)
                # Se la cartella cliente è vuota, rimuovi anche quella
                if not os.listdir(os.path.dirname(old_folder)):
                    shutil.rmtree(os.path.dirname(old_folder))
            except:
                pass  # Ignora errori nella pulizia delle cartelle
        
        # Aggiorna l'indice
        index = self.get_all_offerte()
        for i, entry in enumerate(index):
            if entry.get('id') == offerta_id:
                index[i] = {
                    'id': offerta_id,
                    'offer_number': new_offer_number,
                    'date': data['date'],
                    'customer': new_customer,
                    'customer_email': data['customer_email'],
                    'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
                }
                break
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4, ensure_ascii=False)
        
        return True
    
    def update_offerta_pdf_path(self, offerta_id, pdf_path):
        """Aggiorna il percorso del PDF per un'offerta"""
        offerta = self.get_offerta(offerta_id)
        if not offerta:
            return False
        
        offerta['pdf_path'] = pdf_path
        return self.update_offerta(offerta_id, offerta)
    
    def delete_offerta(self, offerta_id):
        """Elimina un'offerta dal database"""
        offerta = self.get_offerta(offerta_id)
        if not offerta:
            return False
        
        # Rimuovi dall'indice
        index = self.get_all_offerte()
        index = [entry for entry in index if entry.get('id') != offerta_id]
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4, ensure_ascii=False)
        
        # Rimuovi i file
        customer_folder = os.path.join(self.data_folder, offerta['customer'].upper())
        offer_folder = os.path.join(customer_folder, offerta['offer_number'])
        
        try:
            if os.path.exists(offer_folder):
                shutil.rmtree(offer_folder)
            
            # Se la cartella cliente è vuota, rimuovi anche quella
            if os.path.exists(customer_folder) and not os.listdir(customer_folder):
                shutil.rmtree(customer_folder)
        except:
            return False
        
        return True