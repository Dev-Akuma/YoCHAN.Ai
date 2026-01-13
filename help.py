import subprocess

def get_project_summary():
    # -I ignores the __pycache__ and .git folders to keep it clean
    result = subprocess.check_output(["tree", "-I", "__pycache__|.git"]).decode("utf-8")
    return result

print(get_project_summary())