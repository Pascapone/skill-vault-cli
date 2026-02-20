from InquirerPy import inquirer
from prompt_toolkit.formatted_text import HTML

def test():
    try:
        # Test HTML formatting
        result = inquirer.text(
            message=HTML('<style color="red">This message should be red via HTML</style>:'),
            transformer=lambda x: HTML(f'<style color="red">Transformer: {x}</style>')
        ).execute()
        print(f"Result: {result}")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
