#pyenv v-env setup
if command -v pyenv >/dev/null 2>&1; then 
  echo 'pyenv exists.'
else 
  "$(curl pyenv.run | sh)"
  shell_type=$(basename "$SHELL")
  if [ "$shell_type" = "bash" ]; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
  elif [ "$shell" = "zsh" ]; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
  elif [ "$shell" = "ksh" ]; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.kshrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.kshrc
    source ~/.kshrc
  else
    echo 'issue detecting shell. add manually.'
  fi
fi
if command -v pyenv >/dev/null 2>&1; then 
  echo 'pyenv setup complete.'
else 
  echo 'pyenv install issue, add to shell manually.'

pyenv virtualenv system main
pyenv activate main

pip install pynmea2 adafruit-circuitpython-ssd1306 Pillow bleak pybluez requests serial datetime subprocess asyncio board busio

#python check
if command -v /usr/bin/python3 >/dev/null 2>&1 ; then echo 'python path as expected.\n' ; else 'fix python path. python3 not found in /usr/bin.' ; fi 

# make sure to run this from the folder you want the file to live in, or modify this appropriately. otherwise the systemd service will not work.
mkdir wigle_wardriver; cd wigle_wardriver
export dldir="$(pwd)"

sudo cat <<'EOF' > /etc/systemd/system/wardriving.service
[Unit]
Description=Wardriving Script
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${dldir}/wigle_wardrive.py
WorkingDirectory=${dldir}
StandardOutput=inherit
StandardError=inherit
Restart=always
User=${USER}
Environment="PATH=/home/${USER}/.pyenv/versions/main/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYENV_ROOT=/home/${USER}/.pyenv"
Environment="PYENV_VERSION=main"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wardriving.service
sudo systemctl start wardriving.service
sudo systemctl status wardriving.service
