from flask import Flask, render_template, jsonify, request
from threading import Thread
import time
import math
import random
import sys
import os
import subprocess
import platform
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

reset_flag = False
global_i = 0

# --- Função para liberar porta ---
def free_port(port):
    if platform.system() == "Windows":
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        pids = set()
        for line in lines:
            if f":{port} " in line:
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
        if not pids:
            print("Nenhum processo usando a porta.")
            return
        print(f"Processos usando a porta: {', '.join(pids)}")
        confirm = input("Deseja finalizar esses processos? (s/n): ")
        if confirm.lower() == 's':
            for pid in pids:
                subprocess.run(['taskkill', '/PID', pid, '/F'])
                print(f"Processo {pid} finalizado.")
        else:
            print("Nenhum processo foi finalizado.")
    else:
        print(f"Verificando processos na porta {port}...")
        result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
        print(result.stdout)
        pids = set()
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                pids.add(parts[1])
        if not pids:
            print("Nenhum processo usando a porta.")
            return
        print(f"Processos usando a porta: {', '.join(pids)}")
        confirm = input("Deseja finalizar esses processos? (s/n): ")
        if confirm.lower() == 's':
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"Processo {pid} finalizado.")
                except Exception as e:
                    print(f"Erro ao finalizar {pid}: {e}")
        else:
            print("Nenhum processo foi finalizado.")

free_port(PORT)

# --- Servidor Modbus ---
store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0]*16))
context = ModbusServerContext(slaves=store, single=True)

def update_registers(context):
    global reset_flag, global_i
    while True:
        slave_id = 0x00
        hr = context[slave_id].getValues(3, 0, count=16)

        if reset_flag:
            context[0x00].setValues(3, 0, [0]*16)
            global_i = 0
            reset_flag = False
        else:            
            hr[0] = global_i                                # HR0: Rampa
            hr[1] = int(50 + 50 * math.sin(global_i * 0.1))  # HR1: Senoide
            hr[2] = random.randint(0, 50)           # HR2: Aleatório
            hr[5] = global_i % 200                          # HR5: Dente de Serra
            hr[6] = random.choice([0,1])             # HR6: Booleano
            hr[8] = 50 + int(20 * math.sin(global_i*0.05)) # HR8: Variável processo
            setpoint = hr[9] if hr[9] != 0 else 100
            Kp = hr[10] if hr[10] != 0 else 1
            hr[7] = max(0,int(Kp * (setpoint - hr[8]))) # HR7: Saída PID
        context[0x00].setValues(3, 0, hr)
        global_i += 1
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
    global reset_flag
    reset_flag = True
    return jsonify(success=True)


# --- Executa Flask + Modbus TCP ---
if __name__ == "__main__":
    print(f"Servidor MODBUS TCP rodando em 0.0.0.0:{PORT}")
    Thread(target=lambda: StartTcpServer(context, address=("0.0.0.0", PORT)), daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
