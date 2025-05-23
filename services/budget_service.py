import logging
from fpdf import FPDF # Necesitarías instalar esto: pip install fpdf2
from datetime import datetime
import os 

logger = logging.getLogger(__name__)

class BudgetService:
    @staticmethod
    def generate_pdf_bytes(budget_data: dict) -> bytes: # Cambiado para devolver bytes
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Asegúrate de que la ruta de la imagen sea correcta en el entorno de Render
        # Si 'pictures' está en la raíz de tu repositorio, esto debería funcionar.
        # Considera usar una ruta absoluta o verificar si el archivo existe.
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pictures", "1.png")
        if not os.path.exists(image_path):
            logger.warning(f"Imagen no encontrada en: {image_path}. El PDF se generará sin ella.")
            # Si no quieres que falle, puedes omitir la imagen o usar una imagen de placeholder
        else:
            try:
                pdf.image(image_path, x=0, y=0, w=210, h=297)
            except Exception as e:
                logger.error(f"Error al añadir imagen al PDF: {e}")

        # Datos del cliente
        pdf.text(130, 22, budget_data['client_name'])
        pdf.text(130, 32, budget_data['client_cedula'])
        
        # Tu información estática
        pdf.text(45, 50, "Ejido")
        pdf.text(45, 57, "XXXX-XXXXXXXX")
        
        # Fecha del presupuesto
        pdf.text(125, 56, str(datetime.date.today()))
        pdf.set_font("Arial", "B", 12)
        
        #pdf.line(10, 95, 200, 95) # Línea debajo de los encabezados

        pdf.set_font("Arial", "", 12)
        total_budget = 0.0
        y_pos = 100 # Posición Y inicial para los ítems
        item_counter = 1
        
        for item in budget_data['items']:
            # Asegúrate de que los valores sean strings para .text()
            treatment_str = str(item['treatment'])
            quantity_str = str(item['quantity'])
            price_str = f"${item['price']:,.2f}"
            subtotal = item['price'] * item['quantity']
            subtotal_str = f"${subtotal:,.2f}"

            pdf.text(15, y_pos, f"{item_counter}. {treatment_str}")
            pdf.text(95, y_pos, quantity_str)
            pdf.text(130, y_pos, price_str)
            pdf.text(160, y_pos, subtotal_str)
            
            total_budget += subtotal
            y_pos += 10 # Espacio entre líneas
            item_counter += 1

        #pdf.line(10, y_pos + 5, 200, y_pos + 5) # Línea antes del total

        #pdf.text(140, y_pos + 15, "Total:")
        pdf.text(160, 261, f"${total_budget:,.2f}") # Formatear el total también
        
        # Información de banco (ajusta la posición según el total dinámico)
        pdf.text(38, 254, "Banco")
        pdf.text(30, 261, "XXXX-XXXXXXXX")
        pdf.text(30, 268, "12345678")
        pdf.text(50, 275, "Nombre")
        pdf.text(25, 289, "0108...3091")

        try:
            # En lugar de guardar en un archivo, devolvemos los bytes
            return pdf.output(dest='S').encode('latin1') # 'S' para string (bytes), latin1 para compatibilidad
        except Exception as e:
            logger.error(f"Error al generar los bytes del PDF: {e}")
            raise

    # También podrías añadir métodos para guardar presupuestos en una base de datos si es necesario
    # @staticmethod
    # def save_budget(budget_data: dict, client_id: int):
    #     # Lógica de base de datos para guardar el presupuesto
    #     pass