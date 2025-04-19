class Offerta:
    """Classe che rappresenta un'offerta commerciale."""
    
    def __init__(self, data=None):
        """
        Inizializza un'offerta con i dati forniti
        
        Args:
            data (dict): Dizionario contenente i dati dell'offerta
        """
        if data is None:
            data = {}
            
        self.id = data.get('id', '')
        self.offer_number = data.get('offer_number', '')
        self.date = data.get('date', '')
        self.customer = data.get('customer', '')
        self.customer_email = data.get('customer_email', '')
        self.address = data.get('address', '')
        self.offer_description = data.get('offer_description', '')
        self.tabs = data.get('tabs', [])
        self.pdf_path = data.get('pdf_path', '')
    
    def to_dict(self):
        """
        Converte l'offerta in un dizionario
        
        Returns:
            dict: Dizionario con i dati dell'offerta
        """
        return {
            'id': self.id,
            'offer_number': self.offer_number,
            'date': self.date,
            'customer': self.customer,
            'customer_email': self.customer_email,
            'address': self.address,
            'offer_description': self.offer_description,
            'tabs': self.tabs,
            'pdf_path': self.pdf_path
        }
    
    def get_total_price(self):
        """
        Calcola il prezzo totale dell'offerta
        
        Returns:
            float: Prezzo totale dell'offerta
        """
        total = 0.0
        
        for tab in self.tabs:
            if tab.get('type') == 'single_product':
                try:
                    price = float(tab.get('unit_price', 0))
                    quantity = float(tab.get('quantity', 0))
                    discount = float(tab.get('discount', 0)) if tab.get('discount_flag') else 0
                    
                    # Applica lo sconto se necessario
                    if discount > 0:
                        price = price * (1 - discount / 100)
                    
                    total += price * quantity
                except (ValueError, TypeError):
                    pass
            
            elif tab.get('type') == 'multi_product':
                products = tab.get('products', [])
                for product in products:
                    try:
                        if len(product) >= 4:  # Nome, modello, prezzo, quantità
                            price = float(product[2])
                            quantity = float(product[3])
                            total += price * quantity
                    except (ValueError, TypeError, IndexError):
                        pass
        
        return total
    
    def get_product_count(self):
        """
        Restituisce il numero totale di prodotti nell'offerta
        
        Returns:
            int: Numero di prodotti
        """
        count = 0
        
        for tab in self.tabs:
            if tab.get('type') == 'single_product':
                count += 1
            elif tab.get('type') == 'multi_product':
                count += len(tab.get('products', []))
        
        return count