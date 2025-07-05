import flet as ft
import logging
from typing import Optional, List, Dict
from services.dentist_service import DentistService
from models.dentist import Dentist
from utils.alerts import show_success, show_error # Asumiendo que tienes este módulo

logger = logging.getLogger(__name__)

class DentistsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.dentists: List[Dentist] = [] # Lista para almacenar los dentistas mostrados
        self.edit_dentist_id: Optional[int] = None # Para saber si estamos editando o creando

        # Componentes UI
        self.search_bar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.BLUE_400,
            bar_hint_text="Buscar dentista...",
            view_hint_text="Escriba el nombre o teléfono del dentista...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.search_bar.open_view()
            ),
            controls=[],
            expand=True,
            on_change=self._handle_search_change,
            on_submit=self._handle_search_submit
        )
        self.dentists_list_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )

        self.dentist_name_field = ft.TextField(label="Nombre del Dentista", expand=True)
        self.dentist_phone_field = ft.TextField(
            label="Teléfono",
            keyboard_type=ft.KeyboardType.PHONE,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9+\-() ]", replacement_string=""),
            width=200
        )
        self.dentist_is_active_checkbox = ft.Checkbox(label="Activo", value=True)

        # Este es el diálogo principal para añadir/editar dentistas
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(""), # El título se establecerá dinámicamente
            content=ft.Column([
                self.dentist_name_field,
                self.dentist_phone_field,
                self.dentist_is_active_checkbox,
            ], spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_dialog),
                ft.FilledButton("Guardar", on_click=self._save_dentist_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Diálogo de dentista descartado")
        )

        self.page.overlay.append(self.dialog)
        self.page.update()

    def _load_dentists(self, search_term: str = ""):
        """Carga los dentistas desde el servicio y actualiza la UI."""
        try:
            self.dentists = DentistService.get_all_dentists(search_term=search_term)
            self._update_dentists_display()
        except Exception as e:
            logger.error(f"Error al cargar dentistas: {e}")
            show_error(self.page, f"Error al cargar dentistas: {e}")

    def _update_dentists_display(self):
        """Actualiza la columna de visualización de dentistas."""
        self.dentists_list_view.controls.clear()
        if not self.dentists:
            self.dentists_list_view.controls.append(ft.Text("No hay dentistas para mostrar.", italic=True))
        else:
            for d in self.dentists:
                self.dentists_list_view.controls.append(self._build_dentist_card(d))
        self.page.update()

    def _build_dentist_card(self, dentist: Dentist):
        """Crea un ft.Card para un dentista individual."""
        return ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(dentist.name, weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(f"Teléfono: {dentist.phone if dentist.phone else 'N/A'}"),
                                ft.Text(f"Estado: {'Activo' if dentist.is_active else 'Inactivo'}"),
                            ],
                            expand=True
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Editar dentista",
                                    on_click=lambda e, d_id=dentist.id, d_name=dentist.name, d_phone=dentist.phone, d_active=dentist.is_active: self._open_add_edit_dialog(d_id, d_name, d_phone, d_active)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Eliminar dentista",
                                    icon_color=ft.colors.RED_500,
                                    on_click=lambda e, d_id=dentist.id: self._confirm_delete_dentist(d_id)
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
        """Maneja el cambio en el campo de búsqueda de dentistas."""
        search_term = e.control.value.strip()
        self._load_dentists(search_term)

    def _handle_search_submit(self, e):
        """Maneja el envío de la búsqueda (ej. al presionar Enter)."""
        search_term = e.control.value.strip()
        self._load_dentists(search_term)
        e.control.close_view() # Cierra la vista de sugerencias
        e.control.update()

    def _open_add_edit_dialog(self, dentist_id: Optional[int] = None, name: str = "", phone: str = "", is_active: bool = True):
        """Abre el diálogo para añadir o editar un dentista."""
        self.edit_dentist_id = dentist_id
        if dentist_id is None:
            self.dialog.title = ft.Text("Añadir Nuevo Dentista")
            self.dentist_name_field.value = ""
            self.dentist_phone_field.value = ""
            self.dentist_is_active_checkbox.value = True
        else:
            self.dialog.title = ft.Text("Editar Dentista")
            self.dentist_name_field.value = name
            self.dentist_phone_field.value = phone
            self.dentist_is_active_checkbox.value = is_active

        self.dialog.open = True
        self.page.update()

    def _close_dialog(self, e):
        """Cierra el diálogo."""
        self.dialog.open = False
        self.page.update()

    def _save_dentist_dialog(self, e):
        """Maneja el guardado de un dentista desde el diálogo."""
        name = self.dentist_name_field.value.strip()
        phone = self.dentist_phone_field.value.strip()
        is_active = self.dentist_is_active_checkbox.value

        dentist_data = {
            "name": name,
            "phone": phone if phone else None, # Guardar como None si está vacío
            "is_active": is_active
        }

        try:
            if self.edit_dentist_id is None:
                # Crear nuevo dentista
                success, message = DentistService.create_dentist(dentist_data)
            else:
                # Actualizar dentista existente
                success, message = DentistService.update_dentist(
                    dentist_id=self.edit_dentist_id,
                    dentist_data=dentist_data
                )

            if success:
                show_success(self.page, message)
                self._load_dentists() # Recargar la lista de dentistas
                self._close_dialog(e)
            else:
                show_error(self.page, message)
        except Exception as ex:
            logger.error(f"Error al guardar dentista: {ex}")
            show_error(self.page, f"Error al guardar dentista: {ex}")

    def _confirm_delete_dentist(self, dentist_id: int):
        """Muestra un diálogo de confirmación antes de eliminar un dentista."""
        # Verificar si el dentista tiene citas asociadas
        if DentistService.has_appointments(dentist_id):
            show_error(self.page, "No se puede eliminar el dentista porque tiene citas asociadas. Por favor, elimine o reasigne las citas primero.")
            return

        def delete_confirmed(e):
            if e.control.data: # Si el botón "Sí" fue presionado
                self._delete_dentist(dentist_id)
            # Cerrar el diálogo de confirmación
            self.page.dialog.open = False
            self.page.update()

        # Crear una nueva instancia de AlertDialog para la confirmación de eliminación
        confirmation_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación"),
            content=ft.Text("¿Está seguro de que desea eliminar este dentista?"),
            actions=[
                ft.TextButton("No", on_click=delete_confirmed, data=False),
                ft.FilledButton("Sí", on_click=delete_confirmed, data=True, style=ft.ButtonStyle(bgcolor=ft.colors.RED_500)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # Asignar el diálogo de confirmación a self.page.dialog y abrirlo
        self.page.dialog = confirmation_dialog
        self.page.open(self.page.dialog)
        self.page.update()

    def _delete_dentist(self, dentist_id: int):
        """Elimina un dentista."""
        try:
            success, message = DentistService.delete_dentist(dentist_id)
            if success:
                show_success(self.page, message)
                self._load_dentists() # Recargar la lista
            else:
                show_error(self.page, message)
        except Exception as e:
            logger.error(f"Error al eliminar dentista: {e}")
            show_error(self.page, f"Error al eliminar dentista: {e}")

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
                            text="Añadir Dentista",
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
        """Construye y devuelve la vista principal de dentistas."""
        self._load_dentists()

        return ft.View(
            "/dentists",
            controls=[
                ft.AppBar(
                    title=ft.Text("Gestión de Dentistas"),
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
                            ft.Container(content=self._build_controls_row()),
                            ft.Divider(),
                            self.dentists_list_view
                        ],
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15
                    ),
                    padding=20,
                ),
            ],
            scroll=ft.ScrollMode.AUTO
        )

def dentists_view(page: ft.Page):
    """Función de fábrica para crear la vista de gestión de dentistas."""
    return DentistsView(page).build_view()
