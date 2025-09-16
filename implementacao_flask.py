from flask import Flask, render_template, jsonify, request
from threading import Thread
import time
import math
import random
import sys
import os
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
import socket, os, signal

#pyinstaller --onefile --add-data "templates:index" --add-data "static:static" implementacao_flask.py
#pip install flask
#pip install pymodbus==2.5.3
#pip install pyinstaller
#sudo lsof -i :1502
#pyinstaller --onefile comunicacao.py


#Garante que o Flask ache os arquivos estáticos e templates quando empacotado com PyInstaller


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)





PORT = int(input("Digite a porta para o servidor MODBUS (padrão 1502): ") or 1502)

# --- Função para liberar porta ---
def free_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('', port))
        s.close()
        return
    except OSError:
        print(f"Porta {port} ocupada, tentando liberar...")
        import subprocess
        result = subprocess.run(['lsof', '-t', f'-i:{port}'], capture_output=True, text=True)
        pids = result.stdout.split()
        for pid in pids:
            os.kill(int(pid), signal.SIGKILL)
        print(f"Porta {port} liberada!")

free_port(PORT)

# --- Servidor Modbus ---
store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0]*16))
context = ModbusServerContext(slaves=store, single=True)

def update_registers(context):
    i = 0
    while True:
        hr = context[0x00].getValues(3, 0, count=16)
        hr[0] = i                                # HR0: Rampa
        hr[1] = int(50 + 50 * math.sin(i * 0.1))  # HR1: Senoide
        hr[2] = random.randint(0, 50)           # HR2: Aleatório
        hr[5] = i % 200                          # HR5: Dente de Serra
        hr[6] = random.choice([0,1])             # HR6: Booleano
        hr[8] = 50 + int(20 * math.sin(i*0.05)) # HR8: Variável processo
        setpoint = hr[9] if hr[9] != 0 else 100
        Kp = hr[10] if hr[10] != 0 else 1
        hr[7] = max(0,int(Kp * (setpoint - hr[8]))) # HR7: Saída PID
        context[0x00].setValues(3, 0, hr)
        i += 1
        time.sleep(1)

Thread(target=update_registers, args=(context,), daemon=True).start()

# --- Flask Web ---
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registradores")
def get_regs():
    hr = context[0x00].getValues(3, 0, count=16)
    return jsonify(hr)

@app.route("/set_reg", methods=["POST"])
def set_reg():
    data = request.json
    reg = int(data["reg"])
    val = int(data["val"])
    context[0x00].setValues(3, reg, [val])
    return jsonify(success=True)

@app.route("/reset_regs", methods=["POST"])
def reset_regs():
    context[0x00].setValues(3, 0, [0]*16)
    return jsonify(success=True)


# --- Executa Flask + Modbus TCP ---
if __name__ == "__main__":
    print(f"Servidor MODBUS TCP rodando em 0.0.0.0:{PORT}")
    Thread(target=lambda: StartTcpServer(context, address=("0.0.0.0", PORT)), daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
