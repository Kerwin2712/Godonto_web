import flet as ft

def presup_view(page: ft.Page):
    """Vista de presupuesto para la aplicación"""
    
    def on_submit(e):
        # Aquí iría la lógica para manejar el envío del formulario
        pass

    # Componentes UI
    title = ft.Text("Crear Presupuesto", size=24, weight=ft.FontWeight.BOLD)
    
    cliente = ft.TextField(
        label="Cliente",
        width=300,
        autofocus=True,
        keyboard_type=ft.KeyboardType.TEXT
    )
    
    fecha = ft.DatePicker(
        label="Fecha",
        width=300
    )
    
    monto = ft.TextField(
        label="Monto",
        width=300,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    
    submit_button = ft.ElevatedButton(
        "Enviar",
        on_click=on_submit,
        width=300
    )
    
    return ft.View(
        "/presupuesto",
        controls=[
            title,
            cliente,
            fecha,
            monto,
            submit_button
        ]
    )
    
