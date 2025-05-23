import logging
from fpdf import FPDF # Necesitarías instalar esto: pip install fpdf2
from datetime import datetime

logger = logging.getLogger(__name__)

class BudgetService:
    @staticmethod
    def generate_pdf(budget_data: dict, output_path: str = "presupuesto.pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.image("pictures/1.png", x=0, y=0, w=210, h=297)
        
        pdf.text(130, 22, budget_data['client_name'])
        pdf.text(130, 32, budget_data['client_cedula'])
        pdf.text(45, 50, "Ejido")
        pdf.text(45, 57, "XXXX-XXXXXXXX")
        #pdf.text(170, 49, str(n_factura))
        pdf.text(125, 56, str(datetime.date.today()))

        total_budget = 0.0
        for item in budget_data['items']:
            indice = len(budget_data['items'])
            pdf.text(15, 100 + (indice * 10), f"{indice}. )    " + item['treatment'])
            pdf.text(95, 100 + (indice * 10), str(item['quantity']))
            pdf.text(130, 100 + (indice * 10), f"${item['price']:,.2f}")
            subtotal = item['price'] * item['quantity']
            pdf.text(160, 100 + (indice * 10), f"${subtotal:,.2f}")
            
            total_budget += subtotal
        
        pdf.text(160, 261, f"{total_budget:,.2f} $")

        pdf.text(38, 254, "Banco")
        pdf.text(30, 261, "XXXX-XXXXXXXX")
        pdf.text(30, 268, "12345678")
        pdf.text(50, 275, "Nombre")
        pdf.text(25, 289, "0108...3091")
        
        try:
            pdf.output(output_path)
            logger.info(f"PDF generado exitosamente en {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al generar el PDF: {e}")
            raise

    # También podrías añadir métodos para guardar presupuestos en una base de datos si es necesario
    # @staticmethod
    # def save_budget(budget_data: dict, client_id: int):
    #     # Lógica de base de datos para guardar el presupuesto
    #     pass