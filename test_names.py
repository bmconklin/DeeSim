import fantasynames as fn
import inspect

print("Available functions in fantasynames:")
for name, obj in inspect.getmembers(fn):
    if inspect.isfunction(obj):
        print(f"- {name}")

print("\n\nTesting common ones:")
try:
    print(f"Elf: {fn.elf()}")
    print(f"Dwarf: {fn.dwarf()}")
    print(f"Human: {fn.human()}")
except Exception as e:
    print(f"Error calling function: {e}")
