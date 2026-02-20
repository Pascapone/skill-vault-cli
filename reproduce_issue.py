from InquirerPy import inquirer
from rich.console import Console

console = Console()
RED = "\033[31m"
RESET = "\033[0m"

def test():
    try:
        # Test ANSI codes
        result = inquirer.text(
            message=f"{RED}This message should be red via ANSI{RESET}:",
            transformer=lambda x: f"{RED}Transformer: {x}{RESET}"
        ).execute()
        print(f"Result: {result}")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    test()
