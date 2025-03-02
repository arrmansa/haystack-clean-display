import python_minifier
import gzip
import base64
import json

# Read and minify the Python script
with open('main.py', 'r', encoding='utf-8') as f:
    minified_code = python_minifier.minify(f.read())

# Compress and encode
compressed_code = gzip.compress(minified_code.encode("ascii"))
encoded_code = base64.a85encode(compressed_code).decode("ascii")

# Construct the command
to_exec = (
    'import gzip,base64;'
    'exec(gzip.decompress(base64.a85decode(' + json.dumps(encoded_code) + ')).decode("ascii"))'
)

# Escape single quotes for Zsh compatibility
to_exec = to_exec.replace("'", "'\"'\"'")  # Escape single quotes by breaking the string

# Output to file
with open("run.sh", "w") as run_script:
    run_script.write("pip install ")
    with open("requirements.txt", "r") as requirements:
        run_script.write(requirements.read().strip().replace("\n", " "))
    run_script.write("\n")
    run_script.write(f"python -c '{to_exec}'")
