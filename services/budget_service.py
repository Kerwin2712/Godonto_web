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

        # Intenta una ruta relativa desde la raíz de tu proyecto
        # Asumiendo que tu script se ejecuta desde algún lugar dentro del proyecto
        # y 'pictures' está en la raíz del repositorio.
        # Puedes ajustar 'ruta_base' si tu script está en un subdirectorio.

        # Opción 1: Si 'pictures' está directamente en la raíz de tu repo y el script
        # se ejecuta desde la raíz o un subdirectorio predecible.
        # Esto funciona bien si la "raíz" del despliegue es la raíz de tu repo.
        image_path = "pictures/1.png" # Ruta relativa directa

        # Opción 2: Si el script se ejecuta desde un subdirectorio y 'pictures' está en la raíz del repo.
        # Necesitarías saber cuántos niveles subir.
        # Si budget_service.py está en `src/`, y pictures está en la raíz:
        # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # image_path = os.path.join(project_root, "pictures", "1.png")

        # Para tu caso con os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pictures", "1.png")
        # Podríamos intentar simplificarlo o hacer la ruta más robusta.
        # Una forma más segura de obtener la raíz del proyecto si el script está en un subdirectorio:
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # # Suponiendo que 'budget_service.py' está directamente en la raíz o en un subdirectorio conocido como 'app'
        # # Ajusta 'app' si tu estructura es diferente.
        # if os.path.basename(current_dir) == "app": # Si tu app principal está en una carpeta 'app'
        #     project_root = os.path.dirname(current_dir)
        # else: # Si budget_service.py está en la raíz
        #     project_root = current_dir

        # Simplificación para el caso más común en Render:
        # Si 'pictures' está directamente en la raíz de tu repositorio,
        # y tu aplicación se ejecuta desde un directorio que tiene acceso a esa raíz,
        # una ruta relativa simple puede funcionar, o una ruta absoluta basada en el directorio de trabajo.
        # Es más seguro usar `os.getcwd()` para la raíz del proyecto.
        try:
            # Intenta encontrar la raíz del proyecto en Render
            # Render suele clonar tu repo en /opt/render/project/src/
            # O el directorio de trabajo actual podría ser la raíz de tu repo.
            project_root = os.getcwd() # Directorio de trabajo actual
            # Puedes imprimir esto en los logs de Render para verificar: logger.info(f"CWD: {project_root}")
            image_path = os.path.join(project_root, "pictures", "1.png")

            if not os.path.exists(image_path):
                logger.warning(f"Imagen no encontrada en: {image_path}. Intentando ruta alternativa...")
                # Si no la encuentra, intenta una ruta relativa directa
                image_path = "pictures/1.png" # A veces, una ruta más simple funciona en Render si la raíz es tu repo

            if not os.path.exists(image_path):
                logger.error(f"Imagen aún no encontrada después de varios intentos: {image_path}. El PDF se generará sin ella.")
            else:
                try:
                    pdf.image(image_path, x=0, y=0, w=210, h=297)
                except Exception as e:
                    logger.error(f"Error al añadir imagen al PDF desde {image_path}: {e}")

        except Exception as e:
            logger.error(f"Error al determinar la ruta de la imagen o al añadirla: {e}")


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