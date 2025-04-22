from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import json
import uuid
import shutil
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.pdf_generator import generate_pdf

app = Flask(__name__)
app.secret_key = 'valtservice_secret_key'  # Cambiare in produzione
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join(app.root_path, 'data')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Inizializzazione delle cartelle necessarie
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Controlla se l'estensione del file è consentita"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.context_processor
def inject_now():
    """Inietta la data attuale nei template"""
    return {'now': datetime.now()}

def get_next_offer_number():
    """Genera il prossimo numero di offerta nel formato YYYY-XXXX"""
    counter_file = os.path.join(app.config['DATA_FOLDER'], "counter.json")
    
    # Inizializza il contatore se non esiste
    if not os.path.exists(counter_file):
        current_year = str(datetime.now().year)
        counter = {current_year: 0}
        with open(counter_file, 'w') as f:
            json.dump(counter, f)
    
    # Carica il contatore
    with open(counter_file, 'r') as f:
        counter = json.load(f)
    
    current_year = str(datetime.now().year)
    if current_year not in counter:
        counter[current_year] = 0
    
    counter[current_year] += 1
    
    # Salva il contatore aggiornato
    with open(counter_file, 'w') as f:
        json.dump(counter, f)
    
    return f"{current_year}-{counter[current_year]:04d}"

def update_offerte_index(data, data_folder):
    """Aggiorna il file di indice delle offerte"""
    try:
        index_file = os.path.join(data_folder, "offerte_index.json")
        
        # Carica l'indice esistente
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = []
        
        # Verifica se l'offerta è già presente nell'indice
        for i, entry in enumerate(index):
            if entry.get('id') == data['id']:
                # Aggiorna la voce esistente
                index[i] = {
                    'id': data['id'],
                    'offer_number': data['offer_number'],
                    'date': data['date'],
                    'customer': data['customer'],
                    'customer_email': data['customer_email'],
                    'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
                }
                break
        else:
            # Aggiungi una nuova voce
            index.append({
                'id': data['id'],
                'offer_number': data['offer_number'],
                'date': data['date'],
                'customer': data['customer'],
                'customer_email': data['customer_email'],
                'description': data['offer_description'][:100] + '...' if len(data['offer_description']) > 100 else data['offer_description']
            })
        
        # Salva l'indice aggiornato
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4, ensure_ascii=False)
        
    except Exception as e:
        print(f"ERRORE nell'aggiornamento dell'indice: {e}")

def get_offerta_direct(offerta_id, data_folder):
    """Ottiene direttamente un'offerta dal file JSON usando l'ID"""
    try:
        # Carica l'indice
        index_file = os.path.join(data_folder, "offerte_index.json")
        if not os.path.exists(index_file):
            print(f"ERRORE: File indice non trovato: {index_file}")
            return None
            
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        # Trova l'offerta nell'indice
        for entry in index:
            if entry.get('id') == offerta_id:
                # Costruisci il percorso del file JSON
                customer_folder = os.path.join(data_folder, entry['customer'].upper())
                offer_folder = os.path.join(customer_folder, entry['offer_number'])
                json_path = os.path.join(offer_folder, "dati_offerta.json")
                
                if not os.path.exists(json_path):
                    print(f"ERRORE: File JSON non trovato: {json_path}")
                    return None
                    
                # Carica i dati completi
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Assicurati che tabs esista
                if 'tabs' not in data or not isinstance(data['tabs'], list):
                    data['tabs'] = []
                    
                return data
                
        print(f"ERRORE: Offerta con ID {offerta_id} non trovata nell'indice")
        return None
        
    except Exception as e:
        print(f"ERRORE in get_offerta_direct: {e}")
        return None

def get_all_offerte():
    """Restituisce tutte le offerte dall'indice"""
    index_file = os.path.join(app.config['DATA_FOLDER'], "offerte_index.json")
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"ERRORE nel caricamento dell'indice: {e}")
    return []

def process_form_final(form, files):
    """
    Versione finale della funzione process_form che risolve definitivamente il problema
    """
    # DEBUG: Stampa tutti i campi del form
    print("\n------------------------------")
    print("DUMP COMPLETO DEL FORM RICEVUTO:")
    form_data = dict(form)
    for k, v in form_data.items():
        print(f"  {k}: {v}")
    print("------------------------------\n")

    tabs = []
    
    # Utilizza un pattern regex per trovare gli indici nelle chiavi
    tab_indices = set()
    product_indices = dict()  # Memorizza gli indici dei prodotti per ogni tab
    
    # Cerca gli indici numerici nei nomi dei campi
    for key in form:
        # Cerca pattern come tab_0type_
        match = re.search(r'tab_(\d+)type_', key)
        if match:
            idx = int(match.group(1))
            tab_indices.add(idx)
            print(f"DEBUG: Trovato tab_{idx}type_ : {form[key]}")
            continue
            
        # Cerca pattern come tab_type_0
        match = re.search(r'tab_type_(\d+)', key)
        if match:
            idx = int(match.group(1))
            tab_indices.add(idx)
            print(f"DEBUG: Trovato tab_type_{idx} : {form[key]}")
            continue
            
        # Cerca pattern per gli indici dei prodotti nelle schede multiprodotto
        # Come product_1name__0, product_1model__0
        match = re.search(r'product_(\d+)(name|model|price|quantity|description)__(\d+)', key)
        if match:
            tab_idx = int(match.group(1))
            prod_idx = int(match.group(3))
            
            if tab_idx not in product_indices:
                product_indices[tab_idx] = set()
            
            product_indices[tab_idx].add(prod_idx)
            print(f"DEBUG: Trovato prodotto {prod_idx} per tab {tab_idx}")
    
    # Debug degli indici trovati
    print(f"DEBUG: Indici tab trovati: {sorted(tab_indices)}")
    print(f"DEBUG: Indici prodotti trovati: {product_indices}")

    # Crea le schede
    for idx in sorted(tab_indices):
        print(f"DEBUG: Elaborazione tab {idx}")
        
        # Determina il tipo di scheda (controlla entrambi i formati possibili)
        tab_type = None
        if f'tab_{idx}type_' in form:
            tab_type = form[f'tab_{idx}type_']
        elif f'tab_type_{idx}' in form:
            tab_type = form[f'tab_type_{idx}']
        
        print(f"DEBUG: Tipo tab {idx}: {tab_type}")
        
        if not tab_type:
            print(f"DEBUG: Tipo non trovato per tab {idx}, salto...")
            continue
        
        # Elabora in base al tipo
        if tab_type == 'single_product':
            # GESTIONE PRODOTTO SINGOLO
            
            # Cerca i campi con entrambi i formati possibili
            product_name = get_form_value(form, [f'product_{idx}name_', f'product_name_{idx}'])
            product_code = get_form_value(form, [f'product_{idx}code_', f'product_code_{idx}'])
            unit_price = get_form_value(form, [f'unit_{idx}price_', f'unit_price_{idx}'], '0')
            quantity = get_form_value(form, [f'quantity_{idx}'], '1')
            description = get_form_value(form, [f'description_{idx}'])
            discount = get_form_value(form, [f'discount_{idx}'], '0')
            power_w = get_form_value(form, [f'power_{idx}w_', f'power_w_{idx}'])
            volts = get_form_value(form, [f'volts_{idx}'])
            size = get_form_value(form, [f'size_{idx}'])
            posizione = get_form_value(form, [f'posizione_{idx}'])
            
            # Checkbox dello sconto - necessita di un trattamento speciale
            discount_flag_keys = [f'discount_{idx}flag_', f'discount_flag_{idx}']
            discount_flag = any(key in form and form[key] == 'on' for key in discount_flag_keys)
            
            # Gestione caricamento immagine
            image_path = get_form_value(form, [f'existing_image_{idx}'], '')
            product_image = None
            for img_key in [f'product_{idx}image_', f'product_image_{idx}']:
                if img_key in files:
                    product_image = files[img_key]
                    break
            
            if product_image and product_image.filename and allowed_file(product_image.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_image.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                product_image.save(file_path)
                image_path = '/static/uploads/' + filename
                print(f"DEBUG: Salvata immagine in {image_path}")
            
            # Crea la scheda prodotto singolo
            if product_name and product_code:  # Solo se i campi essenziali sono presenti
                single_product_tab = {
                    'type': 'single_product',
                    'product_code': product_code,
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'description': description,
                    'discount': discount,
                    'discount_flag': discount_flag,
                    'power_w': power_w,
                    'volts': volts,
                    'size': size,
                    'posizione': posizione,
                    'product_image_path': image_path
                }
                
                print(f"DEBUG: Aggiunto prodotto singolo: {product_name}")
                tabs.append(single_product_tab)
            else:
                print(f"DEBUG: Saltato prodotto singolo per tab {idx} - dati essenziali mancanti")
        
        elif tab_type == 'multi_product':
            # GESTIONE MULTIPRODOTTO
            print(f"DEBUG: Elaborazione multiprodotto {idx}")
            
            # Recupera i prodotti per questa scheda
            products = []
            
            # Se abbiamo già trovato gli indici dei prodotti per questa scheda
            if idx in product_indices:
                print(f"DEBUG: Trovati {len(product_indices[idx])} prodotti per tab {idx}")
                
                for prod_idx in sorted(product_indices[idx]):
                    # Costruisci i nomi dei campi per questo prodotto
                    name_key = f'product_{idx}name__{prod_idx}'
                    model_key = f'product_{idx}model__{prod_idx}'
                    price_key = f'product_{idx}price__{prod_idx}'
                    quantity_key = f'product_{idx}quantity__{prod_idx}'
                    description_key = f'product_{idx}description__{prod_idx}'
                    
                    # Solo se abbiamo il nome del prodotto
                    if name_key in form and form[name_key].strip():
                        product = [
                            form.get(name_key, ''),
                            form.get(model_key, ''),
                            form.get(price_key, '0'),
                            form.get(quantity_key, '1'),
                            form.get(description_key, '')
                        ]
                        print(f"DEBUG: Aggiunto prodotto {prod_idx} in multiprodotto {idx}: {product[0]}")
                        products.append(product)
            
            # Se non abbiamo trovato prodotti con l'approccio diretto, proviamo un altro metodo
            if not products:
                print(f"DEBUG: Tentando approccio alternativo per i prodotti del tab {idx}")
                
                # Cerca tutti i possibili campi prodotto per questa scheda
                product_name_keys = []
                for key in form:
                    if f'product_{idx}name__' in key and form[key].strip():
                        product_name_keys.append(key)
                
                for name_key in product_name_keys:
                    try:
                        # Estrai l'indice del prodotto dal nome del campo
                        prod_idx = int(name_key.split('__')[1])
                        
                        # Altri campi di questo prodotto
                        model_key = f'product_{idx}model__{prod_idx}'
                        price_key = f'product_{idx}price__{prod_idx}'
                        quantity_key = f'product_{idx}quantity__{prod_idx}'
                        description_key = f'product_{idx}description__{prod_idx}'
                        
                        product = [
                            form.get(name_key, ''),
                            form.get(model_key, ''),
                            form.get(price_key, '0'),
                            form.get(quantity_key, '1'),
                            form.get(description_key, '')
                        ]
                        print(f"DEBUG: Aggiunto prodotto con approccio alternativo: {product[0]}")
                        products.append(product)
                    except (ValueError, IndexError):
                        print(f"DEBUG: Errore parsing indice prodotto da {name_key}")
            
            # Se abbiamo trovato dei prodotti, crea la scheda multiprodotto
            if products:
                max_items_per_page = 3  # Default
                for key in [f'max_{idx}items_per_page_', f'max_items_per_page_{idx}']:
                    if key in form:
                        try:
                            max_items_per_page = int(form[key])
                            break
                        except ValueError:
                            pass
                
                multi_product_tab = {
                    'type': 'multi_product',
                    'max_items_per_page': max_items_per_page,
                    'products': products
                }
                
                print(f"DEBUG: Aggiunto tab multiprodotto con {len(products)} prodotti")
                tabs.append(multi_product_tab)
            else:
                print(f"DEBUG: Nessun prodotto trovato per multiprodotto {idx}")
    
    # Se non abbiamo trovato nessuna scheda, proviamo un approccio completamente diverso
    if not tabs:
        print("DEBUG: Nessuna scheda trovata con i metodi standard, tentativo di recupero diretto")
        
        # Cerca tutti i possibili campi prodotto nel form
        product_fields = {}
        
        for key in form:
            # Crea un dizionario di tutti i campi che sembrano essere prodotti
            if key.startswith('product_') and '_name_' in key:
                idx = key.split('_name_')[1]
                if idx not in product_fields:
                    product_fields[idx] = {'type': 'single_product'}
                product_fields[idx]['product_name'] = form[key]
            
            elif key.startswith('product_') and 'name_' in key:
                parts = key.split('name_')
                if len(parts) == 2:
                    idx = parts[0].replace('product_', '')
                    if idx not in product_fields:
                        product_fields[idx] = {'type': 'single_product'}
                    product_fields[idx]['product_name'] = form[key]
        
        # Crea schede per ogni prodotto trovato
        for idx, fields in product_fields.items():
            if 'product_name' in fields and fields['product_name'].strip():
                # Questo è un prodotto singolo valido, trova gli altri campi
                prefix = f'product_{idx}'
                
                # Cerca gli altri campi di questo prodotto
                for key in form:
                    if key.startswith(prefix):
                        field_name = key.replace(prefix, '')
                        if field_name.startswith('_code_'):
                            fields['product_code'] = form[key]
                        elif field_name.startswith('_price_'):
                            fields['unit_price'] = form[key]
                        # Aggiungi altri campi...
                
                # Se abbiamo i campi essenziali, crea la scheda
                if 'product_code' in fields:
                    single_product_tab = {
                        'type': 'single_product',
                        'product_code': fields.get('product_code', ''),
                        'product_name': fields.get('product_name', ''),
                        'quantity': fields.get('quantity', '1'),
                        'unit_price': fields.get('unit_price', '0'),
                        'description': fields.get('description', ''),
                        'discount': '0',
                        'discount_flag': False,
                        'power_w': '',
                        'volts': '',
                        'size': '',
                        'posizione': '',
                        'product_image_path': ''
                    }
                    
                    print(f"DEBUG: Aggiunto prodotto singolo con recupero diretto: {fields.get('product_name')}")
                    tabs.append(single_product_tab)
    
    print(f"DEBUG: Processo completato. Totale schede elaborate: {len(tabs)}")
    return tabs

def get_form_value(form, possible_keys, default=''):
    """
    Cerca un valore nel form provando diverse possibili chiavi
    
    Args:
        form: Il form da cui ottenere i valori
        possible_keys: Lista di possibili chiavi da provare
        default: Valore predefinito se nessuna chiave viene trovata
        
    Returns:
        Il valore trovato o il default
    """
    for key in possible_keys:
        if key in form:
            return form[key]
    return default

@app.route('/')
def index():
    offerte = get_all_offerte()
    return render_template('index.html', offerte=offerte)

@app.route('/nuova-offerta', methods=['GET', 'POST'])
def nuova_offerta():
    try:
        if request.method == 'GET':
            # Genera un nuovo numero di offerta per il form
            next_number = get_next_offer_number()
            today_date = datetime.now().strftime('%Y-%m-%d')
            return render_template('nuova_offerta.html', next_number=next_number, today_date=today_date)
        
        elif request.method == 'POST':
            print("DEBUG - Ricevuto POST per nuova offerta")
            
            # Crea un dizionario per la nuova offerta
            data = {
                'date': request.form.get('date'),
                'customer': request.form.get('customer'),
                'customer_email': request.form.get('customer_email'),
                'address': request.form.get('address'),
                'offer_description': request.form.get('offer_description'),
                'offer_number': request.form.get('offer_number'),
                'id': str(uuid.uuid4()),
                'tabs': process_form_final(request.form, request.files)
            }
            
            print(f"DEBUG - Dati offerta preparati - {len(data['tabs'])} tabs")
            
            # Salva direttamente i dati in un file JSON
            customer_folder = os.path.join(app.config['DATA_FOLDER'], data['customer'].upper())
            offer_folder = os.path.join(customer_folder, data['offer_number'])
            os.makedirs(offer_folder, exist_ok=True)
            
            json_path = os.path.join(offer_folder, "dati_offerta.json")
            
            print(f"DEBUG - Salvataggio JSON in: {json_path}")
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"DEBUG - JSON salvato con successo")
            
            # Aggiorna indice offerte
            update_offerte_index(data, app.config['DATA_FOLDER'])
            
            # Genera il PDF
            pdf_path = generate_pdf(data, app.root_path)
            
            # Aggiorna il percorso del PDF
            data['pdf_path'] = os.path.basename(pdf_path)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            flash('Offerta creata con successo!', 'success alert-permanent')
            return redirect(url_for('view_offerta', offerta_id=data['id']))
        
        return redirect(url_for('index'))
    
    except Exception as e:
        import traceback
        print(f"ERRORE in nuova_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Si è verificato un errore: {str(e)}', 'danger alert-permanent')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/json')
def debug_offerta_json(offerta_id):
    """Endpoint di debug che mostra il JSON dell'offerta"""
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta:
            return jsonify({"error": "Offerta non trovata"}), 404
        return jsonify(offerta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/offerta/<offerta_id>')
def view_offerta(offerta_id):
    try:
        # Ottieni l'offerta direttamente dal file JSON
        offerta_data = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        
        if not offerta_data:
            flash('Offerta non trovata', 'danger')
            return redirect(url_for('index'))
        
        print(f"DEBUG view_offerta: ID={offerta_id}, tabs={len(offerta_data.get('tabs', []))}")
        
        return render_template('vista_offerta.html', offerta=offerta_data)
    except Exception as e:
        import traceback
        print(f"Errore in view_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Errore nel caricamento dell\'offerta: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/modifica', methods=['GET', 'POST'])
def edit_offerta(offerta_id):
    try:
        if request.method == 'GET':
            # Ottieni l'offerta direttamente dal file JSON
            offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
            if not offerta:
                flash('Offerta non trovata', 'danger')
                return redirect(url_for('index'))
                
            return render_template('nuova_offerta.html', offerta=offerta, is_edit=True, today_date=datetime.now().strftime('%Y-%m-%d'))
            
        elif request.method == 'POST':
            print(f"DEBUG - Ricevuto POST per modifica offerta {offerta_id}")
            
            # Stesso approccio di nuova_offerta, ma manteniamo l'ID originale
            # Ottieni prima i dati dell'offerta esistente
            original_offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
            if not original_offerta:
                flash('Offerta non trovata', 'danger')
                return redirect(url_for('index'))
            
            # Aggiorna i dati dell'offerta
            data = {
                'date': request.form.get('date'),
                'customer': request.form.get('customer'),
                'customer_email': request.form.get('customer_email'),
                'address': request.form.get('address'),
                'offer_description': request.form.get('offer_description'),
                'offer_number': request.form.get('offer_number'),
                'id': offerta_id,  # Mantieni l'ID originale
                'tabs': process_form_final(request.form, request.files)
            }
            
            print(f"DEBUG - Dati offerta preparati per modifica - {len(data['tabs'])} tabs")
            
            # Mantieni il percorso PDF esistente
            if original_offerta and 'pdf_path' in original_offerta:
                data['pdf_path'] = original_offerta['pdf_path']
            
            # Gestisci il caso in cui il cliente o il numero offerta sono cambiati
            old_customer = original_offerta.get('customer', '').upper()
            old_offer_number = original_offerta.get('offer_number', '')
            
            new_customer = data['customer'].upper()
            new_offer_number = data['offer_number']
            
            old_folder = os.path.join(app.config['DATA_FOLDER'], old_customer, old_offer_number)
            new_folder = os.path.join(app.config['DATA_FOLDER'], new_customer, new_offer_number)
            
            # Crea nuova cartella se necessario
            os.makedirs(os.path.dirname(new_folder), exist_ok=True)
            os.makedirs(new_folder, exist_ok=True)
            
            # Salva i dati aggiornati
            json_path = os.path.join(new_folder, "dati_offerta.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Se la posizione è cambiata, copia i file necessari
            if old_folder != new_folder and os.path.exists(old_folder):
                for filename in os.listdir(old_folder):
                    if filename != "dati_offerta.json":  # File JSON già riscritto
                        src_path = os.path.join(old_folder, filename)
                        dst_path = os.path.join(new_folder, filename)
                        shutil.copy2(src_path, dst_path)
                
                # Prova a rimuovere le vecchie cartelle
                try:
                    shutil.rmtree(old_folder)
                    # Se la cartella cliente è vuota, rimuovi anche quella
                    old_customer_folder = os.path.join(app.config['DATA_FOLDER'], old_customer)
                    if os.path.exists(old_customer_folder) and not os.listdir(old_customer_folder):
                        shutil.rmtree(old_customer_folder)
                except:
                    pass  # Ignora errori nella pulizia
            
            # Aggiorna l'indice
            update_offerte_index(data, app.config['DATA_FOLDER'])
            
            # Rigenera il PDF
            pdf_path = generate_pdf(data, app.root_path)
            data['pdf_path'] = os.path.basename(pdf_path)
            
            # Salva di nuovo con il percorso PDF aggiornato
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            flash('Offerta aggiornata con successo!', 'success')
            return redirect(url_for('view_offerta', offerta_id=offerta_id))
            
    except Exception as e:
        import traceback
        print(f"ERRORE in edit_offerta: {e}")
        print(traceback.format_exc())
        flash(f'Si è verificato un errore: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/offerta/<offerta_id>/pdf')
def download_pdf(offerta_id):
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta or not offerta.get('pdf_path'):
            flash('PDF non trovato', 'danger')
            return redirect(url_for('view_offerta', offerta_id=offerta_id))
        
        pdf_path = os.path.join(app.config['DATA_FOLDER'], offerta['customer'].upper(), 
                               offerta['offer_number'], offerta['pdf_path'])
        
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f'Errore nel download del PDF: {str(e)}', 'danger')
        return redirect(url_for('view_offerta', offerta_id=offerta_id))

@app.route('/offerta/<offerta_id>/elimina', methods=['POST'])
def delete_offerta(offerta_id):
    try:
        offerta = get_offerta_direct(offerta_id, app.config['DATA_FOLDER'])
        if not offerta:
            flash('Offerta non trovata', 'danger')
            return redirect(url_for('index'))
        
        # Rimuovi dall'indice
        index_file = os.path.join(app.config['DATA_FOLDER'], "offerte_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            index = [entry for entry in index if entry.get('id') != offerta_id]
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=4, ensure_ascii=False)
        
        # Rimuovi i file
        customer_folder = os.path.join(app.config['DATA_FOLDER'], offerta['customer'].upper())
        offer_folder = os.path.join(customer_folder, offerta['offer_number'])
        
        if os.path.exists(offer_folder):
            shutil.rmtree(offer_folder)
        
        # Se la cartella cliente è vuota, rimuovi anche quella
        if os.path.exists(customer_folder) and not os.listdir(customer_folder):
            shutil.rmtree(customer_folder)
        
        flash('Offerta eliminata con successo', 'success')
    except Exception as e:
        print(f"ERRORE nell'eliminazione dell'offerta: {e}")
        flash(f'Errore durante l\'eliminazione dell\'offerta: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/api/next-offer-number', methods=['GET'])
def api_next_offer_number():
    next_number = get_next_offer_number()
    return jsonify({'next_number': next_number})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)