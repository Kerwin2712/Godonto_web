import logging
from fpdf import FPDF
from datetime import datetime
import os
import sys # Importar sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Función para obtener la ruta de recursos (copia esto si no tienes un módulo compartido)
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BudgetService:
    @staticmethod
    def generate_pdf_to_path(file_path: str, quote_data: dict):
        """
        Genera un PDF de presupuesto y lo guarda en la ruta de archivo especificada,
        utilizando una imagen de fondo como plantilla y rellenando los campos.
        
        Args:
            file_path (str): La ruta completa donde se guardará el archivo PDF.
            quote_data (dict): Un diccionario con los datos del presupuesto, incluyendo
                                'client_name', 'client_cedula', 'quote_id', 'items', 'date',
                                'client_phone', 'client_email', 'client_address', 'notes', 'discount'.
        """
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Intenta cargar la imagen de fondo
        try:
            # Usa la función resource_path para construir la ruta de la imagen
            image_path = resource_path(os.path.join("pictures", "1.png"))
            
            if os.path.exists(image_path):
                pdf.image(image_path, x=0, y=0, w=210, h=297) # A4 size (210mm x 297mm)
            else:
                logger.warning("Imagen de fondo no encontrada, generando PDF sin ella. Ruta buscada: %s", image_path)
        except Exception as e:
            logger.error(f"Error al cargar imagen de fondo: {e}")

        # --- Datos dinámicos del presupuesto y cliente ---

        # Datos del cliente (Nombre, C.I.)
        pdf.set_font("Arial", size=12)
        pdf.text(130, 22, str(quote_data.get('client_name', 'N/A'))) # Posición para el Nombre del cliente
        pdf.text(130, 32, str(quote_data.get('client_cedula', 'N/A'))) # Posición para la Cédula del cliente
        
        # Información de contacto del cliente (Ubicación, Teléfono, Email)
        # Ajustar estas coordenadas para que se alineen con los espacios de la plantilla
        pdf.set_font("Arial", size=10) 
        # La plantilla tiene "Ubicación :" y "Teléfono :", pondremos los datos dinámicos después.
        # Asumiendo que 65mm es el inicio del texto para estos campos.
        pdf.text(45, 50, "Av Centenario Entrada el Piñal Casa #10") # Posición para la dirección del cliente
        pdf.text(45, 57, "04247432710") # Posición para el teléfono del cliente
        # Si la plantilla tiene un espacio para el email, puedes agregarlo aquí
        # pdf.text(65, 64, str(quote_data.get('client_email', 'N/A'))) 

        # Número de presupuesto (N.°) y Fecha
        pdf.set_font("Arial", size=12)
        pdf.text(170, 49, str(quote_data.get('quote_id', 'N/A'))) # Posición para el N.° de presupuesto
        
        # Formatear la fecha
        date_obj = quote_data.get('date')
        date_str = ""
        if isinstance(date_obj, datetime):
            date_str = date_obj.strftime("%d/%m/%Y") # Formato dd/mm/yyyy
        elif isinstance(date_obj, str):
            date_str = date_obj # Si ya viene como string, usarlo directamente
        else:
            date_str = datetime.now().strftime("%d/%m/%Y") # Fecha actual si no se proporciona
        pdf.text(150, 56, date_str) # Posición para la Fecha del presupuesto

        # --- Items del presupuesto (Descripción, Cantidad, Precio, Total) ---
        pdf.set_font("Arial", size=10) # Tamaño de fuente para los ítems
        total_budget = 0.0
        y_pos_items_start = 100 # Posición Y inicial para la primera fila de ítems
        item_line_height = 7 # Espacio vertical entre cada línea de ítem

        # Coordenadas X para cada columna de ítems, ajustadas a tu plantilla
        x_desc = 15  # Descripción
        x_qty = 95   # Cantidad
        x_price = 130 # Precio Unitario
        x_subtotal = 160 # Subtotal

        current_y_pos = y_pos_items_start

        for i, item in enumerate(quote_data.get('items', []), start=1):
            # Asegurarse de que treatment_name sea una cadena de texto
            treatment_name = str(item.get('treatment', 'N/A'))
            quantity = item.get('quantity', 0)
            price = item.get('price', 0.0)
            subtotal = price * quantity
            
            total_budget += subtotal

            # Formatear números
            quantity_str = str(quantity)
            price_str = f"{price:,.2f}" # Formato con coma para miles y 2 decimales
            subtotal_str = f"{subtotal:,.2f}$" # Formato con coma para miles, 2 decimales y signo de dólar
            
            # Dibujar el número de ítem y la descripción
            pdf.text(x_desc, current_y_pos, f"{i}. )")
            
            # Ajuste básico para descripciones largas si no quieres que se salgan
            max_desc_visual_width = 70 # Ancho aproximado para la descripción en mm
            # Asegurarse de que treatment_name sea una cadena antes de get_string_width
            if pdf.get_string_width(treatment_name) > max_desc_visual_width:
                # Truncar y añadir elipsis si es demasiado largo para el espacio
                while pdf.get_string_width(treatment_name + "...") > max_desc_visual_width and len(treatment_name) > 3:
                    treatment_name = treatment_name[:-1]
                treatment_name += "..." if len(treatment_name) > 3 else "" # Asegura que no se agregue "..." a cadenas muy cortas

            pdf.text(x_desc + 10, current_y_pos, treatment_name) # Descripción (ajustado para el número del ítem)
            pdf.text(x_qty, current_y_pos, quantity_str) # Cantidad
            pdf.text(x_price, current_y_pos, price_str) # Precio Unitario
            pdf.text(x_subtotal, current_y_pos, subtotal_str) # Subtotal
            
            current_y_pos += item_line_height # Mueve la posición para el siguiente ítem

        # --- Agregar el descuento como un ítem más si existe ---
        discount_amount = quote_data.get('discount', 0.0)
        if discount_amount > 0:
            pdf.set_font("Arial", size=10)
            discount_display_name = "Descuento"
            discount_quantity = 1
            discount_price = -discount_amount # Mostrar como un valor negativo para restar
            discount_subtotal = -discount_amount # El subtotal del descuento es el descuento mismo (negativo)
            
            total_budget -= discount_amount # Restar el descuento del total general

            # Formatear números para el descuento
            discount_price_str = f"{discount_price:,.2f}" 
            discount_subtotal_str = f"{discount_subtotal:,.2f}$"
            
            # Dibujar el ítem de descuento
            pdf.text(x_desc, current_y_pos, f"{len(quote_data.get('items', [])) + 1}. )")
            pdf.text(x_desc + 10, current_y_pos, discount_display_name)
            pdf.text(x_qty, current_y_pos, str(discount_quantity))
            pdf.text(x_price, current_y_pos, discount_price_str)
            pdf.text(x_subtotal, current_y_pos, discount_subtotal_str)
            
            current_y_pos += item_line_height # Mueve la posición para el siguiente ítem

        # --- Total general ---
        pdf.set_font("Arial", size=12, style='B') # Negrita para el total
        # La posición del TOTAL en la plantilla es 160, 261.
        pdf.text(160, 261, f"{total_budget:,.2f} $") # Total calculado y formateado

        # --- Información para el Pago (Banco, Tlf, C.I., Beneficiario) ---
        pdf.set_font("Arial", size=10) # Tamaño para info bancaria
        # Estas coordenadas son las que tenías en tu versión original, ajustadas a la plantilla
        pdf.text(38, 254, "Provincial") # Banco
        pdf.text(30, 261, "0412-2153091") # Tlf (Teléfono de cuenta)
        pdf.text(30, 268, "17130498") # C.I. (Cédula del titular de cuenta)
        pdf.text(50, 275, "María José Quintero H") # Beneficiario

        # --- Notas ---
        pdf.set_font("Arial", size=10)
        notes_text = str(quote_data.get('notes', '')) # Asegurarse de que las notas sean string
        if notes_text:
            # Posición aproximada para las notas, debes ajustarla según el espacio en tu plantilla.
            # Por ejemplo, unos 10mm debajo del último ítem y dejando espacio para el pie de página.
            y_pos_notes_area = current_y_pos + 5 # Comienza un poco debajo del último ítem
            x_notes_area = 15
            width_notes_area = 180 # Ancho total para las notas (aproximado)
            
            # Usar multi_cell para manejar notas que pueden ser largas y ocupar varias líneas
            pdf.set_xy(x_notes_area, y_pos_notes_area)
            pdf.multi_cell(width_notes_area, 5, notes_text, 0, 'L') # Ancho, alto de línea, texto, borde (0=sin), alineación ('L'=izquierda)


        try:
            # Guardar el PDF directamente en la ruta proporcionada
            pdf.output(file_path)
            logger.info(f"PDF generado exitosamente en: {file_path}")
        except Exception as e:
            logger.error(f"Error al generar el PDF en la ruta especificada '{file_path}': {e}")
            raise # Volver a lanzar la excepción para que el llamador la maneje

