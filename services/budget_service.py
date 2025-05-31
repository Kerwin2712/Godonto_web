import logging
from fpdf import FPDF
from datetime import datetime
import os
from pathlib import Path
#print
logger = logging.getLogger(__name__)

class BudgetService:
    @staticmethod
    def generate_pdf(budget_data: dict):
        # Obtener la ruta de la carpeta Documentos del usuario
        documentos_path = Path.home() / "Documents"
        pdfs_folder = documentos_path / "pdfs_presupuestos"
        
        # Crear la carpeta si no existe
        os.makedirs(pdfs_folder, exist_ok=True)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Intenta cargar la imagen de fondo
        try:
            image_path = os.path.join("pictures", "1.png")
            if os.path.exists(image_path):
                pdf.image(image_path, x=0, y=0, w=210, h=297)
            else:
                logger.warning("Imagen de fondo no encontrada, generando PDF sin ella")
        except Exception as e:
            logger.error(f"Error al cargar imagen de fondo: {e}")

        # Datos del cliente
        pdf.text(130, 22, budget_data['client_name'])
        pdf.text(130, 32, budget_data['client_cedula'])
        
        # Información estática
        pdf.text(45, 50, "Ejido")
        pdf.text(45, 57, "XXXX-XXXXXXXX")
        
        # Número de factura
        n_factura = 1000
        pdf.text(170, 49, str(n_factura))
        
        # Fecha del presupuesto
        pdf.text(125, 56, str(budget_data.get('date', datetime.now())))

        # Items del presupuesto
        total_budget = 0.0
        y_pos = 100
        
        for i, item in enumerate(budget_data['items'], start=1):
            treatment_str = str(item['treatment'])
            quantity_str = str(item['quantity'])
            price_str = f"{item['price']}"
            subtotal = item['price'] * item['quantity']
            subtotal_str = f"{subtotal}$"
            
            pdf.text(15, y_pos, f"{i}. )    {treatment_str}")
            pdf.text(95, y_pos, quantity_str)
            pdf.text(130, y_pos, price_str)
            pdf.text(160, y_pos, subtotal_str)
            
            total_budget += subtotal
            y_pos += 10

        # Total
        pdf.text(160, 261, f"{total_budget} $")
        
        # Información de banco
        pdf.text(38, 254, "Banco")
        pdf.text(30, 261, "XXXX-XXXXXXXX")
        pdf.text(30, 268, "12345678")
        pdf.text(50, 275, "Nombre")
        pdf.text(25, 289, "0108...3091")

        try:
            # Generar nombre del archivo
            safe_client_name = "".join(c for c in budget_data['client_name'] if c.isalnum() or c in (' ', '-')).replace(' ', '_')
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = pdfs_folder / f"Presupuesto_{safe_client_name}_{date_str}.pdf"
            
            # Guardar el PDF directamente
            pdf.output(filename)
            return filename
        except Exception as e:
            logger.error(f"Error al generar el PDF: {e}")
            raise