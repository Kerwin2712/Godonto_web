import flet as ft
from typing import Dict, List, Tuple, Optional, Callable
from models.appointment import Appointment
from models.client import Client
from datetime import date


class WidgetBuilder:
    """Clase para construir componentes UI reutilizables"""
    # Add these new methods to the WidgetBuilder class in widgets.py
    
    @staticmethod
    def metric_card(
        title: str, 
        value: str, 
        change: Optional[float] = None, 
        icon: str = ft.icons.INFO,
        width: int = 200,
        height: int = 120
    ) -> ft.Card:
        """Crea una tarjeta de métrica visual con indicador de cambio
        
        Args:
            title: Título de la métrica
            value: Valor principal
            change: Porcentaje de cambio (positivo/negativo)
            icon: Icono a mostrar
            width: Ancho de la tarjeta
            height: Alto de la tarjeta
            
        Returns:
            ft.Card: Tarjeta configurada
        """
        change_color = ft.colors.GREEN if change and change >= 0 else ft.colors.RED
        change_icon = ft.icons.ARROW_UPWARD if change and change >= 0 else ft.icons.ARROW_DOWNWARD
        
        change_widget = ft.Row([
            ft.Icon(change_icon, color=change_color, size=16),
            ft.Text(f"{abs(change):.1f}%" if change is not None else "N/A", 
                color=change_color, size=12)
        ], spacing=2) if change is not None else ft.Container()
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, size=20),
                        ft.Text(title, size=14, weight="bold")
                    ]),
                    ft.Text(value, size=24, weight="bold"),
                    change_widget
                ], spacing=8),
                padding=15,
                width=width,
                height=height
            ),
            elevation=3,
            margin=5
        )

    @staticmethod
    def interactive_table(
        columns: List[ft.DataColumn],
        data: List[Dict],
        page_size: int = 10,
        on_sort: Optional[Callable] = None,
        on_export: Optional[Callable] = None
    ) -> ft.Column:
        """Crea una tabla interactiva con paginación y ordenamiento
        
        Args:
            columns: Lista de columnas
            data: Lista de diccionarios con los datos
            page_size: Número de filas por página
            on_sort: Callback para ordenamiento
            on_export: Callback para exportación
            
        Returns:
            ft.Column: Tabla interactiva completa
        """
        current_page = 1
        total_pages = max(1, len(data) // page_size + (1 if len(data) % page_size else 0))
        
        # Implementar lógica de paginación y ordenamiento aquí
        # (Código completo omitido por brevedad)
        
        return ft.Column([
            ft.Row([
                ft.Text("Filtrar:"),
                ft.TextField(width=200),
                ft.ElevatedButton("Exportar CSV", on_click=on_export)
            ]),
            ft.DataTable(
                columns=columns,
                rows=[],  # Se llenará con los datos paginados
                sort_column_index=0,
                sort_ascending=True,
                #on_select_all=lambda e: print("Select all"),
                heading_row_color=ft.colors.GREY_200,
                divider_thickness=0.5
            ),
            ft.Row([
                ft.IconButton(ft.icons.FIRST_PAGE),
                ft.IconButton(ft.icons.CHEVRON_LEFT),
                ft.Text(f"Página {current_page} de {total_pages}"),
                ft.IconButton(ft.icons.CHEVRON_RIGHT),
                ft.IconButton(ft.icons.LAST_PAGE)
            ], alignment=ft.MainAxisAlignment.CENTER)
        ])

    @staticmethod
    def date_range_picker(
        reports_view,
        on_date_change: Callable,
        initial_start: Optional[date] = None,
        initial_end: Optional[date] = None
    ) -> ft.Row:
        """Selector de rango de fechas con presets rápidos
        
        Args:
            on_date_change: Callback cuando cambian las fechas
            initial_start: Fecha inicial opcional
            initial_end: Fecha final opcional
            
        Returns:
            ft.Row: Controles del selector de fechas
        """
        start_picker = ft.DatePicker()
        end_picker = ft.DatePicker()
        
        start_text = ft.Text(initial_start.strftime("%d/%m/%Y") if initial_start else "Seleccionar")
        end_text = ft.Text(initial_end.strftime("%d/%m/%Y") if initial_end else "Seleccionar")
        
        def update_range(e):
            on_date_change(start_picker.value, end_picker.value)
            
        return ft.Row([
            ft.Dropdown(
                options=[
                    ft.dropdown.Option("hoy", "Hoy"),
                    ft.dropdown.Option("semana", "Esta semana"),
                    ft.dropdown.Option("mes", "Este mes"),
                    ft.dropdown.Option("personalizado", "Personalizado")
                ],
                on_change=lambda e: reports_view.handle_preset_change(e.control.value),
                width=150
            ),
            ft.ElevatedButton(
                content=start_text,
                on_click=lambda _: start_picker.pick_date()
            ),
            ft.Text("a"),
            ft.ElevatedButton(
                content=end_text,
                on_click=lambda _: end_picker.pick_date()
            ),
            ft.IconButton(ft.icons.CHECK, on_click=update_range)
        ])
    
    
    @staticmethod
    def build_stat_card(
        title: str, 
        value: str, 
        icon: str, 
        icon_color: str,
        width: int = 180,
        height: int = 120
    ) -> ft.Card:
        """
        Construye una tarjeta de estadística
        
        Args:
            title: Título de la tarjeta
            value: Valor a mostrar
            icon: Icono a mostrar
            icon_color: Color del icono
            width: Ancho de la tarjeta
            height: Alto de la tarjeta
            
        Returns:
            Componente Card de Flet
        """
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(icon, color=icon_color, size=24),
                                ft.Text(title, size=14, color=ft.colors.GREY_600)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Text(
                            str(value),
                            size=28,
                            weight="bold"
                        )
                    ],
                    spacing=5
                ),
                padding=15,
                width=width,
                height=height
            ),
            elevation=2
        )

    @staticmethod
    def build_appointment_card(
        appointment: Appointment,
        on_edit: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None
    ) -> ft.Card:
        """
        Construye una tarjeta de cita con acciones
        
        Args:
            appointment: Objeto Appointment
            on_edit: Callback para editar
            on_complete: Callback para completar
            on_cancel: Callback para cancelar
            
        Returns:
            Componente Card de Flet
        """
        status_colors = {
            'pending': ft.colors.ORANGE,
            'completed': ft.colors.GREEN,
            'cancelled': ft.colors.RED
        }
        
        status_color = status_colors.get(appointment.status.lower(), ft.colors.BLUE)
        
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(ft.icons.CALENDAR_TODAY, color=status_color),
                title=ft.Text(appointment.client_name),
                subtitle=ft.Text(
                    f"{appointment.date.strftime('%d/%m/%Y')} a las {appointment.time}",
                    size=12
                ),
                trailing=WidgetBuilder._build_appointment_menu(
                    appointment,
                    on_edit,
                    on_complete,
                    on_cancel
                )
            ),
            elevation=1,
            margin=ft.margin.symmetric(vertical=5)
        )

    @staticmethod
    def _build_appointment_menu(
        appointment: Appointment,
        on_edit: Optional[Callable],
        on_complete: Optional[Callable],
        on_cancel: Optional[Callable]
    ) -> ft.PopupMenuButton:
        """Construye el menú de acciones para una cita"""
        return ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            items=[
                ft.PopupMenuItem(
                    text="Completar",
                    on_click=lambda e: on_complete(appointment) if on_complete else None,
                    icon=ft.icons.CHECK_CIRCLE_OUTLINE
                ),
                ft.PopupMenuItem(
                    text="Cancelar",
                    on_click=lambda e: on_cancel(appointment) if on_cancel else None,
                    icon=ft.icons.CANCEL_OUTLINED
                ),
                ft.PopupMenuItem(
                    text="Editar",
                    on_click=lambda e: on_edit(appointment) if on_edit else None,
                    icon=ft.icons.EDIT
                ),
            ]
        )

    @staticmethod
    def build_bar_chart(
        title: str, 
        data: List[Tuple[str, float]], 
        x_label: str = "", 
        y_label: str = "",
        bar_color: str = ft.colors.BLUE_400
    ) -> ft.Container:
        """
        Construye un gráfico de barras
        
        Args:
            title: Título del gráfico
            data: Lista de tuplas (etiqueta, valor)
            x_label: Etiqueta del eje X
            y_label: Etiqueta del eje Y
            bar_color: Color de las barras
            
        Returns:
            Componente Container con el gráfico
        """
        max_value = max([v for _, v in data]) if data else 0
        y_interval = max(2, round(max_value / 5))  # Intervalo dinámico

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, weight="bold"),
                    ft.BarChart(
                        bar_groups=[
                            ft.BarChartGroup(
                                x=idx,
                                bar_rods=[
                                    ft.BarChartRod(
                                        from_y=0,
                                        to_y=value,
                                        width=20,
                                        color=bar_color,
                                        border_radius=4,
                                        tooltip=f"{label}: {value}"
                                    )
                                ],
                            ) for idx, (label, value) in enumerate(data)
                        ],
                        border=ft.border.all(1, ft.colors.GREY_400),
                        left_axis=ft.ChartAxis(
                            labels=[
                                ft.ChartAxisLabel(
                                    value=value,
                                    label=ft.Text(str(value), size=12),
                                ) for value in range(0, int(max_value) + y_interval, y_interval)
                            ],
                            labels_size=40,
                            title=ft.Text(y_label, size=12),
                        ),
                        bottom_axis=ft.ChartAxis(
                            labels=[
                                ft.ChartAxisLabel(
                                    value=idx,
                                    label=ft.Text(label[:15], size=10),  # Limitar longitud
                                ) for idx, (label, _) in enumerate(data)
                            ],
                            labels_size=40,
                            title=ft.Text(x_label, size=12),
                        ),
                        tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_800),
                        interactive=True,
                        expand=True,
                    )
                ],
                spacing=10,
            ),
            padding=10,
            border_radius=5,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
        )

    @staticmethod
    def build_data_table(
        columns: List[ft.DataColumn],
        rows: List[ft.DataRow],
        height: Optional[int] = None
    ) -> ft.DataTable:
        """
        Construye una tabla de datos
        
        Args:
            columns: Lista de columnas
            rows: Lista de filas
            height: Altura opcional
            
        Returns:
            Componente DataTable de Flet
        """
        return ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True,
            height=height
        )

    @staticmethod
    def build_pie_chart(
        title: str,
        data: Dict[str, float],
        colors: Dict[str, str],
        size: int = 250
    ) -> ft.Column:
        """
        Construye un gráfico de torta
        
        Args:
            title: Título del gráfico
            data: Diccionario con datos {etiqueta: valor}
            colors: Diccionario de colores {etiqueta: color}
            size: Tamaño del gráfico
            
        Returns:
            Componente Column con el gráfico
        """
        total = sum(data.values()) if data else 1
        return ft.Column(
            controls=[
                ft.Text(title, size=16, weight="bold"),
                ft.Container(
                    content=ft.PieChart(
                        sections=[
                            ft.PieChartSection(
                                value=value,
                                color=colors.get(key, ft.colors.GREY),
                                radius=size/2.5,
                                title=f"{key}\n{value/total:.1%}",
                                title_style=ft.TextStyle(
                                    size=12,
                                    color=ft.colors.WHITE,
                                    weight="bold"
                                )
                            ) for key, value in data.items()
                        ],
                        sections_space=1,
                        center_space_radius=size/6,
                        expand=True
                    ),
                    height=size,
                    width=size,
                    padding=10
                )
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

    @staticmethod
    def build_appointment_badge(has_appointments: bool) -> ft.Container:
        """
        Construye un indicador visual de citas
        
        Args:
            has_appointments: True si hay citas
            
        Returns:
            Componente Container con el indicador
        """
        return ft.Container(
            content=ft.CircleAvatar(
                radius=4,
                bgcolor=ft.colors.BLUE_400 if has_appointments else ft.colors.TRANSPARENT
            ),
            width=10,
            height=10
        )


# Funciones de conveniencia (para mantener compatibilidad)
def build_stat_card(*args, **kwargs):
    return WidgetBuilder.build_stat_card(*args, **kwargs)

def build_appointment_card(*args, **kwargs):
    return WidgetBuilder.build_appointment_card(*args, **kwargs)

def build_bar_chart(*args, **kwargs):
    return WidgetBuilder.build_bar_chart(*args, **kwargs)

def build_data_table(*args, **kwargs):
    return WidgetBuilder.build_data_table(*args, **kwargs)

def build_pie_chart(*args, **kwargs):
    return WidgetBuilder.build_pie_chart(*args, **kwargs)

def build_appointment_badge(*args, **kwargs):
    return WidgetBuilder.build_appointment_badge(*args, **kwargs)