from rich.console import Console
from rich.theme import Theme

console_theme = Theme({
    'warning': 'dark_orange',
    'error' : 'bold red',
})

console = Console(theme=console_theme)

