import flet as ft
import logging
from typing import Optional, List, Dict
from services.treatment_service import TreatmentService # Asegúrate de que este servicio existe y tiene los métodos CRUD
from utils.alerts import show_success, show_error

logger = logging.getLogger(__name__)

class TreatmentsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.treatments: List[Dict] = [] # Lista para almacenar los tratamientos mostrados
        self.edit_treatment_id: Optional[int] = None # Para saber si estamos editando o creando

        # Componentes UI
        self.search_bar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.BLUE_400,
            bar_hint_text="Buscar tratamiento...",
            view_hint_text="Escriba el nombre del tratamiento...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.search_bar.open_view()
            ),
            controls=[],
            expand=True,
            on_change=self._handle_search_change,
            on_submit=self._handle_search_submit
        )

        self.treatments_list_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )

        self.treatment_name_field = ft.TextField(label="Nombre del Tratamiento", expand=True)
        self.treatment_price_field = ft.TextField(
            label="Precio ($)",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9.]", replacement_string=""),
            on_focus=self._on_price_focus, # <-- Añadido on_focus aquí
            width=150
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(""), # El título se establecerá dinámicamente
            content=ft.Column([
                self.treatment_name_field,
                self.treatment_price_field,
            ], spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_dialog),
                ft.FilledButton("Guardar", on_click=self._save_treatment_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Diálogo de tratamiento descartado")
        )

        self.page.overlay.append(self.dialog)
        self.page.update()

    def _on_price_focus(self, e):
        """Borra el contenido del campo de precio si es '0.00' al obtener el foco."""
        if self.treatment_price_field.value == "0.00":
            self.treatment_price_field.value = ""
            self.treatment_price_field.update()
    
    def _load_treatments(self, search_term: str = ""):
        """Carga los tratamientos desde el servicio y actualiza la UI."""
        try:
            self.treatments = TreatmentService.get_all_treatments(search_term=search_term)
            self._update_treatments_display()
        except Exception as e:
            logger.error(f"Error al cargar tratamientos: {e}")
            show_error(self.page, f"Error al cargar tratamientos: {e}")

    def _update_treatments_display(self):
        """Actualiza la columna de visualización de tratamientos."""
        self.treatments_list_view.controls.clear()
        if not self.treatments:
            self.treatments_list_view.controls.append(ft.Text("No hay tratamientos para mostrar.", italic=True))
        else:
            for t in self.treatments:
                self.treatments_list_view.controls.append(self._build_treatment_card(t))
        self.page.update()

    def _build_treatment_card(self, treatment: Dict):
        """Crea un ft.Card para un tratamiento individual."""
        return ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(treatment.name, weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(f"Precio: ${treatment.price:.2f}"),
                            ],
                            expand=True
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Editar tratamiento",
                                    on_click=lambda e, t_id=treatment.id, t_name=treatment.name, t_price=treatment.price: self._open_add_edit_dialog(t_id, t_name, t_price)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Eliminar tratamiento",
                                    icon_color=ft.colors.RED_500,
                                    on_click=lambda e, t_id=treatment.id: self._confirm_delete_treatment(t_id)
                                )
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=10
            )
        )

    def _handle_search_change(self, e):
        """Maneja el cambio en el campo de búsqueda de tratamientos."""
        search_term = e.control.value.strip()
        self._load_treatments(search_term)

    def _handle_search_submit(self, e):
        """Maneja el envío de la búsqueda (ej. al presionar Enter)."""
        search_term = e.control.value.strip()
        self._load_treatments(search_term)
        e.control.close_view() # Cierra la vista de sugerencias
        e.control.update()


    def _open_add_edit_dialog(self, treatment_id: Optional[int] = None, name: str = "", price: float = 0.0):
        """Abre el diálogo para añadir o editar un tratamiento."""
        self.edit_treatment_id = treatment_id
        if treatment_id is None:
            self.dialog.title = ft.Text("Añadir Nuevo Tratamiento")
            self.treatment_name_field.value = ""
            self.treatment_price_field.value = "0.00"
        else:
            self.dialog.title = ft.Text("Editar Tratamiento")
            self.treatment_name_field.value = name
            self.treatment_price_field.value = f"{price:.2f}"
        
        self.dialog.open = True
        self.page.update()

    def _close_dialog(self, e):
        """Cierra el diálogo."""
        self.dialog.open = False
        self.page.update()

    def _save_treatment_dialog(self, e):
        """Maneja el guardado de un tratamiento desde el diálogo."""
        name = self.treatment_name_field.value.strip()
        price_str = self.treatment_price_field.value.strip()

        if not name:
            show_error(self.page, "El nombre del tratamiento es requerido.")
            return
        
        try:
            price = float(price_str) if price_str else 0.0
            if price < 0:
                show_error(self.page, "El precio no puede ser negativo.")
                return
        except ValueError:
            show_error(self.page, "Por favor, introduzca un precio válido.")
            return

        try:
            if self.edit_treatment_id is None:
                # Crear nuevo tratamiento
                success, message = TreatmentService.create_treatment(name=name, price=price)
            else:
                # Actualizar tratamiento existente
                success, message = TreatmentService.update_treatment(
                    treatment_id=self.edit_treatment_id,
                    name=name,
                    price=price
                )
            
            if success:
                show_success(self.page, message)
                self._load_treatments() # Recargar la lista de tratamientos
                self._close_dialog(e)
            else:
                show_error(self.page, message)
        except Exception as ex:
            logger.error(f"Error al guardar tratamiento: {ex}")
            show_error(self.page, f"Error al guardar tratamiento: {ex}")

    def _confirm_delete_treatment(self, treatment_id: int):
        """Muestra un diálogo de confirmación antes de eliminar un tratamiento."""
        def delete_confirmed(e):
            if e.control.data: # Si el botón "Sí" fue presionado
                self._delete_treatment(treatment_id)
            self.dialog.open = False # Cierra el diálogo actual
            self.page.update()

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación"),
            content=ft.Text("¿Está seguro de que desea eliminar este tratamiento?"),
            actions=[
                ft.TextButton("No", on_click=delete_confirmed, data=False),
                ft.FilledButton("Sí", on_click=delete_confirmed, data=True, style=ft.ButtonStyle(bgcolor=ft.colors.RED_500)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.dialog)
        self.page.update()

    def _delete_treatment(self, treatment_id: int):
        """Elimina un tratamiento."""
        try:
            success, message = TreatmentService.delete_treatment(treatment_id)
            if success:
                show_success(self.page, message)
                self._load_treatments() # Recargar la lista
            else:
                show_error(self.page, message)
        except Exception as e:
            logger.error(f"Error al eliminar tratamiento: {e}")
            show_error(self.page, f"Error al eliminar tratamiento: {e}")

    def _build_controls_row(self):
        """
        Construye la fila superior con la barra de búsqueda y el botón de añadir.
        Retorna un ft.ResponsiveRow para manejar la responsividad y el 'wrap' correctamente.
        """
        return ft.ResponsiveRow(
            controls=[
                ft.Column(
                    col={"sm": 12, "md": 8}, # Ocupa 8/12 columnas en pantallas medianas y grandes
                    controls=[self.search_bar],
                    expand=True
                ),
                ft.Column(
                    col={"sm": 12, "md": 4}, # Ocupa 4/12 columnas en pantallas medianas y grandes
                    controls=[
                        ft.FilledButton(
                            icon=ft.icons.ADD,
                            text="Añadir Tratamiento",
                            on_click=lambda e: self._open_add_edit_dialog(),
                            expand=True, # Para que el botón se expanda dentro de su columna
                            height=45 # Para mantener consistencia con otros botones
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END # Alinea el botón a la derecha
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10 # Espacio entre columnas
        )


    def build_view(self):
        """Construye y devuelve la vista principal de tratamientos."""
        # Cargar los tratamientos al construir la vista por primera vez
        self._load_treatments()

        return ft.View(
            "/treatments",
            controls=[
                ft.AppBar(
                    title=ft.Text("Gestión de Tratamientos"),
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: self.page.go("/dashboard"),
                        tooltip="Volver al Dashboard"
                    )
                ),
                ft.Container(
                    content = ft.Column(
                        [
                            ft.Container(content=self._build_controls_row()), # Envuelto en Container
                            ft.Divider(),
                            self.treatments_list_view # Aquí se cargarán las tarjetas de tratamientos
                        ],
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15
                    ),
                    padding=20,
                ),
                
            ],
            scroll=ft.ScrollMode.AUTO # Scrollbar para toda la vista si es necesario
        )

def treatments_view(page: ft.Page):
    """Función de fábrica para crear la vista de gestión de tratamientos."""
    return TreatmentsView(page).build_view()
