import flet as ft
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from services.quote_service import QuoteService
from utils.alerts import show_snackbar, show_error, show_success, AlertManager # Importar AlertManager
from utils.date_utils import format_date
from services.budget_service import BudgetService # Importar BudgetService
import logging
import json
import asyncio # Importar asyncio (ahora usado para asyncio.sleep)

logger = logging.getLogger(__name__)

class QuotesView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.quote_service = QuoteService()
        self.all_quotes: List[Dict] = []
        self._temp_pdf_data: Optional[Dict] = None # Para almacenar datos temporales para el PDF

        # Estado de la vista para paginación
        self.current_page = 1
        self.items_per_page = 10
        self.total_items = 0

        # Configurar el FilePicker para la descarga con un handler de resultado
        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self.page.overlay.append(self.file_picker) # Añadir el FilePicker al overlay de la página
        self.page.update()

        # Valores iniciales para los textos de las fechas de filtro
        self.default_start_date = datetime(2025, 1, 1).date()
        self.default_end_date = datetime(2026, 12, 31).date()

        # Componentes UI
        self.search_bar = self._build_search_bar()
        self.status_filter_dropdown = self._build_status_filter_dropdown()

        self.start_date_filter_text = ft.Text(format_date(self.default_start_date))
        self.end_date_filter_text = ft.Text(format_date(self.default_end_date))

        self.start_date_picker = ft.DatePicker(
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2099, 12, 31),
            on_change=lambda e: self._handle_date_filter_change(e, is_start_date=True)
        )
        self.end_date_picker = ft.DatePicker(
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2099, 12, 31),
            on_change=lambda e: self._handle_date_filter_change(e, is_start_date=False)
        )
        self.page.overlay.extend([self.start_date_picker, self.end_date_picker])

        # Grid de presupuestos (ahora ft.GridView)
        self.quotes_grid = ft.GridView(
            expand=True,
            runs_count=3,
            max_extent=450, # Ajustado para un mejor diseño de tarjeta
            child_aspect_ratio=1.0, # Ajustado para tarjetas de presupuesto
            spacing=15,
            run_spacing=15,
        )

        # Controles de paginación
        self.pagination_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER)

        # Cargar datos iniciales
        self.load_quotes(initial_load=True)


    def _build_appbar(self):
        """Construye la barra de aplicación con un título y botones de acción."""
        appbar_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        appbar_text_color = ft.colors.WHITE

        return ft.AppBar(
            title=ft.Text("Gestión de Presupuestos", weight=ft.FontWeight.BOLD, color=appbar_text_color),
            bgcolor=appbar_bgcolor,
            automatically_imply_leading=False,
            leading=ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                on_click=lambda e: self.page.go("/dashboard"),
                tooltip="Volver al Dashboard",
                icon_color=appbar_text_color
            ),
            actions=[
                ft.IconButton(
                    icon=ft.icons.ADD_BOX,
                    tooltip="Nuevo Presupuesto",
                    on_click=lambda e: self.page.go("/presupuesto"),
                    icon_color=appbar_text_color
                ),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    tooltip="Actualizar Lista",
                    on_click=lambda e: self.load_quotes(),
                    icon_color=appbar_text_color
                )
            ]
        )

    def _build_search_bar(self):
        """Construye el componente SearchBar para buscar por cliente."""
        bar_leading_icon_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        view_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        divider_color = ft.colors.BLUE_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        bar_fill_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900


        return ft.SearchBar(
            view_elevation=4,
            divider_color=divider_color,
            bar_hint_text="Buscar por cliente o cédula...",
            view_hint_text="Filtrar presupuestos...",
            bar_leading=ft.Icon(ft.icons.SEARCH, color=bar_leading_icon_color),
            controls=[],
            expand=True,
            on_change=self._handle_search_change,
            bar_text_style=ft.TextStyle(color=view_text_color),
            bar_bgcolor=bar_fill_color, # Color de fondo del SearchBar
            view_bgcolor=bar_fill_color # Color de fondo de la vista de sugerencias
        )

    def _handle_search_change(self, e):
        """Maneja la búsqueda en tiempo real."""
        # Al cambiar la búsqueda, resetear a la primera página
        self.current_page = 1
        self.load_quotes()

    def _build_status_filter_dropdown(self):
        """Construye el Dropdown para filtrar por estado del presupuesto."""
        dropdown_label_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dropdown_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        dropdown_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dropdown_option_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE


        return ft.Dropdown(
            label="Estado",
            options=[
                ft.dropdown.Option("all", "Todos", text_style=ft.TextStyle(color=dropdown_option_color)),
                ft.dropdown.Option("pending", "Pendiente", text_style=ft.TextStyle(color=dropdown_option_color)),
                ft.dropdown.Option("approved", "Aprobado", text_style=ft.TextStyle(color=dropdown_option_color)),
                ft.dropdown.Option("rejected", "Rechazado", text_style=ft.TextStyle(color=dropdown_option_color)),
                ft.dropdown.Option("invoiced", "Facturado", text_style=ft.TextStyle(color=dropdown_option_color))
            ],
            value="all",
            on_change=lambda e: self.load_quotes(),
            expand=True,
            label_style=ft.TextStyle(color=dropdown_label_color),
            filled=True, # Para que el color de fondo se aplique
            bgcolor=dropdown_bg_color, # Color de fondo del Dropdown
            text_style=ft.TextStyle(color=dropdown_text_color) # Color del texto seleccionado
        )

    def _build_date_filter_controls(self):
        """Construye los controles para el filtro de rango de fechas."""
        text_color_date_label = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        date_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        date_container_bg = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        button_bgcolor = ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800
        button_color = ft.colors.WHITE

        self.start_date_filter_text.color = date_text_color
        self.end_date_filter_text.color = date_text_color

        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Text("Fecha Inicio:", size=12, color=text_color_date_label),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.CALENDAR_TODAY,
                            on_click=lambda e: self.page.open(self.start_date_picker),
                            expand=True,
                            style=ft.ButtonStyle(bgcolor=button_bgcolor, color=button_color)
                        ),
                        ft.Container(
                            content=self.start_date_filter_text,
                            padding=10,
                            bgcolor=date_container_bg,
                            border_radius=5,
                            expand=True
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 6}),
                ft.Column([
                    ft.Text("Fecha Fin:", size=12, color=text_color_date_label),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.CALENDAR_TODAY,
                            on_click=lambda e: self.page.open(self.end_date_picker),
                            expand=True,
                            style=ft.ButtonStyle(bgcolor=button_bgcolor, color=button_color)
                        ),
                        ft.Container(
                            content=self.end_date_filter_text,
                            padding=10,
                            bgcolor=date_container_bg,
                            border_radius=5,
                            expand=True
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 6})
            ],
            spacing=10,
            run_spacing=10
        )

    def _handle_date_filter_change(self, e, is_start_date):
        """Maneja el cambio de fecha en los DatePickers del filtro."""
        if is_start_date:
            if self.start_date_picker.value:
                self.start_date_filter_text.value = format_date(self.start_date_picker.value.date())
        else:
            if self.end_date_picker.value:
                self.end_date_filter_text.value = format_date(self.end_date_picker.value.date())

        # Validar que la fecha de fin no sea anterior a la de inicio
        start_date = self.start_date_picker.value.date() if self.start_date_picker.value else None
        end_date = self.end_date_picker.value.date() if self.end_date_picker.value else None

        if start_date and end_date and end_date < start_date:
            # Revertir la fecha final a la fecha de inicio si es inválida
            self.end_date_picker.value = datetime(start_date.year, start_date.month, start_date.day)
            self.end_date_filter_text.value = format_date(start_date)
            show_snackbar(self.page, "La fecha final no puede ser anterior a la inicial", "warning")

        # Al cambiar el filtro de fecha, resetear a la primera página
        self.current_page = 1
        self.load_quotes()

    def load_quotes(self, initial_load: bool = False):
        """Carga los presupuestos de la base de datos aplicando los filtros actuales.

        Args:
            initial_load (bool): Si es True, fuerza el filtro de estado a None para
                                 cargar todos los presupuestos sin importar la selección inicial
                                 del dropdown.
        """
        search_term = self.search_bar.value.strip() if self.search_bar.value else None

        status_filter = self.status_filter_dropdown.value if self.status_filter_dropdown.value != "all" else None
        start_date = self.start_date_picker.value.date() if self.start_date_picker.value else self.default_start_date
        end_date = self.end_date_picker.value.date() if self.end_date_picker.value else self.default_end_date

        offset = (self.current_page - 1) * self.items_per_page

        logger.info(f"Loading quotes with: search_term='{search_term}', status_filter='{status_filter}', start_date={start_date}, end_date={end_date}, limit={self.items_per_page}, offset={offset}")

        try:
            self.all_quotes = self.quote_service.get_all_quotes(
                search_term=search_term,
                status_filter=status_filter,
                start_date=start_date,
                end_date=end_date,
                limit=self.items_per_page,
                offset=offset
            )
            self.total_items = self.quote_service.count_quotes(
                search_term=search_term,
                status_filter=status_filter,
                start_date=start_date,
                end_date=end_date
            )

            logger.info(f"Quotes loaded: {len(self.all_quotes)}, Total items: {self.total_items}")
            self._render_quotes()
            self._update_pagination_controls()

        except Exception as e:
            logger.error(f"Error al cargar presupuestos: {str(e)}")
            AlertManager.show_error(self.page, "Error al cargar presupuestos: " + str(e))

    def _render_quotes(self):
        """Renderiza los presupuestos en el GridView."""
        self.quotes_grid.controls.clear()

        if not self.all_quotes:
            self._render_empty_state()
            return

        for quote in self.all_quotes:
            self.quotes_grid.controls.append(
                self._build_quote_card(quote)
            )
        self.page.update()

    def _render_empty_state(self):
        """Muestra estado cuando no hay presupuestos."""
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        self.quotes_grid.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.INFO_OUTLINE, size=40, color=text_color),
                    ft.Text("No se encontraron presupuestos.",
                           text_align=ft.TextAlign.CENTER, color=text_color)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True,
                alignment=ft.alignment.center
            )
        )
        self.page.update()


    def _build_quote_card(self, quote: Dict):
        """Construye una tarjeta de presupuesto individual."""
        card_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        secondary_text_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        status_color = {
            'pending': ft.colors.ORANGE_700,
            'approved': ft.colors.GREEN_700,
            'rejected': ft.colors.RED_700,
            'expired': ft.colors.BLUE_GREY_700,
            'invoiced': ft.colors.BLUE_700
        }.get(quote['status'], ft.colors.BLUE_GREY_700)

        # Parse treatments_summary if it's a JSON string
        parsed_treatments = []
        if isinstance(quote.get('treatments_summary'), str) and quote['treatments_summary']:
            try:
                parsed_treatments = json.loads(quote['treatments_summary'])
            except json.JSONDecodeError:
                logger.error(f"Error al decodificar JSON para treatments_summary en quote ID {quote['id']}: {quote['treatments_summary']}")
                parsed_treatments = []
        elif isinstance(quote.get('treatments_summary'), list):
            parsed_treatments = quote['treatments_summary']

        treatments_display = []
        if parsed_treatments:
            for i, t in enumerate(parsed_treatments):
                if i < 2: # Show first 2 treatments
                    treatments_display.append(
                        ft.Text(f"- {t.get('name', 'N/A')} (${t.get('price_at_quote', 0.0):.2f})", size=11, color=secondary_text_color, overflow=ft.TextOverflow.ELLIPSIS)
                    )
                else:
                    treatments_display.append(
                        ft.Text(f"...y {len(parsed_treatments) - i} más", size=11, color=secondary_text_color)
                    )
                    break
            if not treatments_display:
                treatments_display.append(ft.Text("Sin tratamientos", size=11, italic=True, color=secondary_text_color))
        else:
            treatments_display.append(ft.Text("Sin tratamientos", size=11, italic=True, color=secondary_text_color))

        # Colores para los botones de acción
        pdf_button_bgcolor = ft.colors.DEEP_ORANGE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.DEEP_ORANGE_800
        pdf_button_text_color = ft.colors.WHITE


        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.RECEIPT_LONG, color=status_color),
                            title=ft.Text(f"Presupuesto #{quote['id']}", weight=ft.FontWeight.BOLD, color=text_color),
                            subtitle=ft.Text(f"Cliente: {quote['client_name']} ({quote['client_cedula']})", color=secondary_text_color),
                            trailing=self._build_quote_card_actions_menu(quote) # Menu de acciones
                        ),
                        ft.Divider(height=1, color=ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.CALENDAR_TODAY, size=16, color=secondary_text_color),
                                    ft.Text(f"Fecha: {format_date(quote['quote_date'])}", size=12, color=text_color)
                                ]),
                                ft.Row([
                                    ft.Icon(ft.icons.ATTACH_MONEY, size=16, color=secondary_text_color),
                                    ft.Text(f"Total: ${quote['total_amount']:,.2f}", size=14, weight=ft.FontWeight.BOLD, color=text_color)
                                ]),
                                ft.Row([
                                    ft.Icon(ft.icons.INFO_OUTLINE, size=16, color=secondary_text_color),
                                    ft.Text(f"Estado: {quote['status'].capitalize()}", color=status_color, size=12, weight=ft.FontWeight.BOLD)
                                ]),
                                ft.Divider(height=1, color=ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600),
                                ft.Text("Tratamientos:", size=12, weight=ft.FontWeight.BOLD, color=text_color),
                                *treatments_display,
                                ft.Divider(height=1, color=ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600),
                                ft.Row(
                                    [
                                        ft.FilledButton(
                                            text="Generar PDF",
                                            icon=ft.icons.PICTURE_AS_PDF,
                                            on_click=lambda e, q_id=quote['id'], c_id=quote['client_id'], q_date=quote['quote_date']: self.page.run_task(self._initiate_pdf_generation, q_id, c_id, q_date),
                                            style=ft.ButtonStyle(bgcolor=pdf_button_bgcolor, color=pdf_button_text_color),
                                            expand=True
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                    spacing=10
                                )
                            ], spacing=5),
                            padding=ft.padding.symmetric(horizontal=15, vertical=5)
                        )
                    ],
                    spacing=0, # Reduce spacing between ListTile and content
                ),
                padding=0, # No padding for the main container within card
                bgcolor=card_bgcolor,
                border_radius=ft.border_radius.all(10),
            ),
            elevation=4,
            margin=10,
            col={"sm": 12, "md": 6, "lg": 4}, # Responsive columns for GridView
        )


    def _build_quote_card_actions_menu(self, quote: Dict):
        """Construye el menú de acciones para las tarjetas de presupuesto (sin el PDF)."""
        icon_color_edit = ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_300
        icon_color_delete = ft.colors.RED_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.RED_300
        icon_color_info = ft.colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_300
        icon_color_status = ft.colors.GREEN_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREEN_300
        icon_color_reject = ft.colors.ORANGE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.ORANGE_300
        icon_color_invoice = ft.colors.PURPLE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.PURPLE_300
        popup_menu_item_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE


        return ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            tooltip="Más Acciones",
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("Editar", color=popup_menu_item_text_color), # Set text color
                    icon=ft.Icon(ft.icons.EDIT, color=icon_color_edit),
                    # MODIFICACIÓN: Pasar quote_id y client_id a la ruta de edición
                    on_click=lambda e: self.page.go(f"/presupuesto/{quote['id']}/{quote['client_id']}")
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Eliminar", color=popup_menu_item_text_color), # Set text color
                    icon=ft.Icon(ft.icons.DELETE, color=icon_color_delete),
                    on_click=lambda e: self._confirm_delete_quote(quote['id'], quote['client_name'])
                ),
                ft.PopupMenuItem(), # Separador
                # La opción de PDF se ha movido a un FilledButton directo en la tarjeta.
                ft.PopupMenuItem(
                    content=ft.Text("Marcar como Aprobado", color=popup_menu_item_text_color), # Set text color
                    icon=ft.Icon(ft.icons.CHECK_CIRCLE, color=icon_color_status),
                    on_click=lambda e: self._change_quote_status(quote['id'], 'approved')
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Marcar como Rechazado", color=popup_menu_item_text_color), # Set text color
                    icon=ft.Icon(ft.icons.CANCEL, color=icon_color_reject),
                    on_click=lambda e: self._change_quote_status(quote['id'], 'rejected')
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Marcar como Facturado", color=popup_menu_item_text_color), # Set text color
                    icon=ft.Icon(ft.icons.RECEIPT, color=icon_color_invoice),
                    on_click=lambda e: self._change_quote_status(quote['id'], 'invoiced')
                ),
            ]
        )

    async def _initiate_pdf_generation(self, quote_id: int, client_id: int, quote_date: date):
        """Prepara los datos del presupuesto y abre el diálogo para guardar el PDF."""
        logger.info(f"Iniciando generación de PDF para presupuesto ID: {quote_id}")
        try:
            # Obtener detalles completos del presupuesto y cliente
            quote_details = self.quote_service.get_quote(quote_id)
            client_info = self.quote_service.get_client_info_for_quote_pdf(client_id)

            if not quote_details or not client_info:
                AlertManager.show_error(self.page, "Error: No se pudieron obtener los detalles completos del presupuesto o del cliente para generar el PDF.")
                return

            # Preparar los ítems para el PDF
            items_for_pdf = [
                {
                    "treatment": item.get('name', 'N/A'),
                    "quantity": item.get('quantity', 0),
                    "price": item.get('price', 0.0) # Usar 'price' ya que get_quote_treatments lo mapea así
                } for item in quote_details.get('treatments', [])
            ]
            
            self._temp_pdf_data = {
                "quote_id": quote_details['id'],
                "client_name": client_info['name'],
                "client_cedula": client_info['cedula'],
                "client_phone": client_info.get('phone', ''),
                "client_email": client_info.get('email', ''),
                "client_address": client_info.get('address', ''),
                "items": items_for_pdf,
                "date": format_date(quote_date), # Usar la fecha del presupuesto
                "total_amount": quote_details['total_amount']
            }

            # VERIFICACIÓN Y CORRECCIÓN: Asegurarse de que self.file_picker y su método save_file no sean None
            if self.file_picker and hasattr(self.file_picker, 'save_file') and callable(self.file_picker.save_file):
                # Añadir un pequeño retraso para permitir que Flet's internal mechanisms se sincronicen
                
                self.file_picker.save_file(
                    file_name=f"presupuesto_{client_info['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
                    allowed_extensions=["pdf"]
                )
                self.page.update() # Asegurarse de que la UI se actualice después de abrir el diálogo
            else:
                logger.error(f"Error: self.file_picker o su método save_file no está disponible. self.file_picker: {self.file_picker}")
                AlertManager.show_error(self.page, "Error interno: El sistema de guardado de archivos no está listo.")

        except Exception as e:
            logger.error(f"Error al iniciar generación de PDF para presupuesto {quote_id}: {e}")
            AlertManager.show_error(self.page, f"Error al preparar el PDF: {e}")

    async def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Maneja el resultado del diálogo de FilePicker (la ruta seleccionada)."""
        logger.info(f"Resultado del FilePicker: {e.path}")
        if e.path:
            if self._temp_pdf_data:
                try:
                    BudgetService.generate_pdf_to_path(e.path, self._temp_pdf_data)
                    AlertManager.show_success(self.page, f"PDF generado exitosamente en {e.path}") # Usando AlertManager
                    self._temp_pdf_data = None # Limpiar datos temporales
                except Exception as ex:
                    logger.error(f"Error al generar PDF en _on_file_picker_result: {ex}")
                    AlertManager.show_error(self.page, f"Error al generar PDF: {ex}") # Usando AlertManager
            else:
                AlertManager.show_error(self.page, "Error: Datos del presupuesto no disponibles para generar el PDF.") # Usando AlertManager
        else:
            AlertManager.show_error(self.page, "Operación de guardado de PDF cancelada.")


    def _change_quote_status(self, quote_id: int, new_status: str):
        """Cambia el estado de un presupuesto."""
        try:
            success = self.quote_service.update_quote_status(quote_id, new_status)
            if success:
                AlertManager.show_success(self.page, f"Estado del presupuesto actualizado a '{new_status.capitalize()}'.") # Usando AlertManager
                self.load_quotes()
            else:
                AlertManager.show_error(self.page, f"No se pudo actualizar el estado del presupuesto {quote_id}.") # Usando AlertManager
        except Exception as e:
            logger.error(f"Error al cambiar estado del presupuesto: {str(e)}")
            AlertManager.show_error(self.page, f"Error al actualizar estado: {str(e)}") # Usando AlertManager

    def _confirm_delete_quote(self, quote_id: int, client_name: str):
        """Muestra un diálogo de confirmación antes de eliminar un presupuesto."""
        AlertManager.show_confirmation(
            page=self.page,
            title="Confirmar Eliminación",
            content=f"¿Está seguro de que desea eliminar el presupuesto de {client_name}? Esta acción no se puede deshacer.",
            on_confirm=lambda: self._delete_quote(quote_id, client_name) # Pasar client_name para el mensaje de éxito
        )

    def _delete_quote(self, quote_id: int, client_name: str):
        """Elimina un presupuesto."""
        try:
            success = self.quote_service.delete_quote(quote_id)
            if success:
                AlertManager.show_success(self.page, f"Presupuesto de {client_name} eliminado exitosamente.") # Usando AlertManager
                self.load_quotes()
            else:
                AlertManager.show_error(self.page, f"No se pudo eliminar el presupuesto {quote_id}.") # Usando AlertManager
        except Exception as e:
            logger.error(f"Error al eliminar presupuesto: {str(e)}")
            AlertManager.show_error(self.page, f"Error al eliminar: {str(e)}") # Usando AlertManager

    def _update_pagination_controls(self):
        """Actualiza los controles de paginación."""
        total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
        
        # Colores para los íconos de paginación y el texto del número de página
        icon_color_pagination = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        text_color_pagination = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dropdown_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        dropdown_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dropdown_option_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE


        self.pagination_row.controls = [
            ft.IconButton(
                icon=ft.icons.FIRST_PAGE,
                on_click=lambda e: self.change_page(1),
                disabled=self.current_page == 1,
                icon_color=icon_color_pagination
            ),
            ft.IconButton(
                icon=ft.icons.CHEVRON_LEFT,
                on_click=lambda e: self.change_page(self.current_page - 1),
                disabled=self.current_page == 1,
                icon_color=icon_color_pagination
            ),
            ft.Text(f"Página {self.current_page} de {total_pages}", color=text_color_pagination),
            ft.IconButton(
                icon=ft.icons.CHEVRON_RIGHT,
                on_click=lambda e: self.change_page(self.current_page + 1),
                disabled=self.current_page * self.items_per_page >= self.total_items,
                icon_color=icon_color_pagination
            ),
            ft.IconButton(
                icon=ft.icons.LAST_PAGE,
                on_click=lambda e: self.change_page(total_pages),
                disabled=self.current_page * self.items_per_page >= self.total_items,
                icon_color=icon_color_pagination
            ),
            ft.Dropdown(
                options=[
                    ft.dropdown.Option("5", text_style=ft.TextStyle(color=dropdown_option_color)),
                    ft.dropdown.Option("10", text_style=ft.TextStyle(color=dropdown_option_color)),
                    ft.dropdown.Option("20", text_style=ft.TextStyle(color=dropdown_option_color)),
                    ft.dropdown.Option("50", text_style=ft.TextStyle(color=dropdown_option_color)),
                ],
                value=str(self.items_per_page),
                width=100,
                on_change=self.change_items_per_page,
                filled=True, # Para que el color de fondo se aplique
                bgcolor=dropdown_bg_color, # Color de fondo del Dropdown
                text_style=ft.TextStyle(color=dropdown_text_color) # Color del texto seleccionado
            )
        ]
        self.page.update()

    def change_page(self, new_page):
        """Cambia la página actual y recarga los presupuestos."""
        self.current_page = new_page
        self.load_quotes()

    def change_items_per_page(self, e):
        """Cambia el número de items por página y recarga los presupuestos."""
        self.items_per_page = int(e.control.value)
        self.current_page = 1 # Resetear a la primera página al cambiar items por página
        self.load_quotes()


    def build_view(self):
        """Construye la vista completa de gestión de presupuestos."""
        main_content_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        divider_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600

        return ft.View(
            "/quotes",
            controls=[
                self._build_appbar(),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Filtros", size=18, weight="bold", color=section_title_color),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column([self.search_bar], col={"sm": 12, "md": 6, "lg": 4}),
                                    ft.Column([self.status_filter_dropdown], col={"sm": 12, "md": 6, "lg": 3}),
                                    ft.Column([self._build_date_filter_controls()], col={"sm": 12, "md": 12, "lg": 5})
                                ],
                                spacing=10,
                                run_spacing=10
                            ),
                            ft.Divider(height=20, color=divider_color),
                            ft.Text("Listado de Presupuestos", size=18, weight="bold", color=section_title_color),
                            ft.Container(
                                content=ft.Column([ # Contenedor para el GridView y paginación
                                    self.quotes_grid,
                                    ft.Divider(height=20, color=divider_color),
                                    self.pagination_row
                                ], expand=True),
                                expand=True,
                                padding=ft.padding.symmetric(horizontal=10),
                                bgcolor=main_content_bgcolor # Usa el color de fondo del contenido principal
                            )
                        ],
                        spacing=20,
                        expand=True,
                        scroll=ft.ScrollMode.AUTO, # Permite scroll a la columna si el contenido es mucho
                        horizontal_alignment=ft.CrossAxisAlignment.START
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=main_content_bgcolor # Color de fondo del contenedor principal de la vista
                )
            ],
            padding=0
        )

def quotes_view(page: ft.Page):
    """Función de fábrica para crear la vista de gestión de presupuestos."""
    return QuotesView(page).build_view()

