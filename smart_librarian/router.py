# === router.py ===
import importlib.util
import os
import sys

class Router:
    def __init__(self):
        self.default_controller = "home"
        self.default_action = "index"

    def route(self, path):
        parts = path.strip("/").split("/")
        controller_name = parts[0] if parts[0] else self.default_controller
        action_name = parts[1] if len(parts) > 1 else self.default_action
        params = parts[2:] if len(parts) > 2 else []

        controller_file = f"smart_librarian/controllers/{controller_name}_controller.py"
        class_name = f"{controller_name.capitalize()}Controller"

        if not os.path.isfile(controller_file):
            return f"Error: Page not found <br> <a href='/home/index'>Go to Home</a>", 404

        spec = importlib.util.spec_from_file_location(class_name, controller_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[class_name] = module
        spec.loader.exec_module(module)

        controller_class = getattr(module, class_name, None)
        if controller_class is None:
            return f"Error: Controller '{class_name}' not found", 404

        controller_instance = controller_class()
        if not hasattr(controller_instance, action_name):
            return f"Error: Action '{action_name}' not found in {class_name}", 404

        return getattr(controller_instance, action_name)(*params)
