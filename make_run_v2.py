import zlib
import base2048

# Read and minify the Python script
# with open('main.py', 'r', encoding='utf-8') as f:
#     minified_code = python_minifier.minify(f.read())

with open('mini.py', 'r', encoding='utf-8') as f:
    minified_code = f.read()

# Compress and encode
compressed_code = zlib.compress(minified_code.encode("ascii"), 9)
encoded_code = base2048.encode(compressed_code)

# Construct the command
to_exec = (
    'import zlib,base2048;'
    'exec(zlib.decompress(base2048.decode("' + encoded_code + '")))'
)

# Output to file
with open("run2.sh", "w") as run_script:
    run_script.write("pip install base2048 ")
    with open("requirements.txt", "r") as requirements:
        run_script.write(requirements.read().strip().replace("\n", " "))
    run_script.write("\n")
    run_script.write(f"python -c '{to_exec}'")
