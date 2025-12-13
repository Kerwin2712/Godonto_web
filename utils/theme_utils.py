import flet as ft

class AppTheme:
    """
    Centralized theme management for the application.
    Provides consistent colors based on the current ThemeMode.
    """
    @staticmethod
    def get_colors(theme_mode: ft.ThemeMode):
        is_dark = theme_mode == ft.ThemeMode.DARK
        
        return {
            # Backgrounds
            'bg_primary': ft.colors.BLUE_GREY_900 if is_dark else ft.colors.WHITE,
            'bg_secondary': ft.colors.BLUE_GREY_800 if is_dark else ft.colors.GREY_50,
            
            # Text
            'text_primary': ft.colors.WHITE if is_dark else ft.colors.BLACK,
            'text_secondary': ft.colors.BLUE_GREY_200 if is_dark else ft.colors.GREY_700,
            'text_inverse': ft.colors.BLACK if is_dark else ft.colors.WHITE,
            
            # Borders and Dividers
            'border': ft.colors.BLUE_GREY_600 if is_dark else ft.colors.GREY_300,
            'divider': ft.colors.BLUE_GREY_600 if is_dark else ft.colors.GREY_400,
            
            # AppBar
            'appbar_bg': ft.colors.BLUE_GREY_900 if is_dark else ft.colors.BLUE_700,
            'appbar_text': ft.colors.WHITE, # Usually white for both in this app style, or customize
            
            # specific colors
            'success': ft.colors.GREEN_700 if is_dark else ft.colors.GREEN_500,
            'error': ft.colors.RED_300 if is_dark else ft.colors.RED_500,
            
            # Cards
            'card_bg': ft.colors.BLUE_GREY_800 if is_dark else ft.colors.WHITE,
        }
