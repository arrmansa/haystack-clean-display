pip install pandas pyautogui pynput py2app setuptools==70.3.0
py2applet --make-setup main.py
rm -rf build dist
python setup.py py2app --emulate-shell-environment --redirect-stdout-to-asl
dist/main.app/Contents/MacOS/main
cd dist
open -a main.app
zip -yr main.app.zip main.app
#python setup.py py2app -A
# need to add 'excludes': ['rubicon'], in options, python 3.11 - fails, 3.10 fails
# 3.9 + setuptools==69.5.1 + py2app==0.26.1  # --redirect-stdout-to-asl
pyright .
ruff format --line-length=150
rm -rf build dist
python setup.py py2app --emulate-shell-environment --no-chdir
cd dist
open -a main.app
zip -yr main.app.zip main.app