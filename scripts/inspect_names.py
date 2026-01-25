import fantasynames as fn
import inspect

print("Available functions:")
for name, obj in inspect.getmembers(fn):
    if inspect.isfunction(obj):
        print(f"- {name}")
