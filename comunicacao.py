from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from threading import Thread
import time
import math
import random
import os
import signal
import socket

#pip install pymodbus==2.5.3
#sudo lsof -i :1502

PORT = 1502


def free_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('', port))
        s.close()
        return  # Porta livre
    except OSError:
        # Porta ocupada, tentar encontrar PID e matar
        print(f"Porta {port} ocupada, tentando liberar...")
        try:
            import subprocess
            result = subprocess.run(['lsof', '-t', f'-i:{port}'], capture_output=True, text=True)
            pids = result.stdout.split()
            for pid in pids:
                print(f"Morrendo processo {pid}...")
                os.kill(int(pid), signal.SIGKILL)
            print(f"Porta {port} liberada!")
        except Exception as e:
            print(f"Erro ao liberar porta: {e}")

free_port(PORT)

# Criar bloco de memória MODBUS (100 registradores)
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0]*100)
)
context = ModbusServerContext(slaves=store, single=True)

# Função que atualiza os registradores dinamicamente
def update_registers(context):
    i = 0
    while True:
        slave_id = 0x00
        hr = context[slave_id].getValues(3, 0, count=10)  

        amplitude = hr[3] if hr[3] != 0 else 50
        freq = hr[4] if hr[4] != 0 else 0.2

        hr[0] = i                    # HR0: rampa
        hr[1] = int(amplitude + amplitude * math.sin(i * freq))  # HR1: senoide
        hr[2] = random.randint(0, 100)            # HR2: aleatório

        context[slave_id].setValues(3, 0, hr)    # atualiza os registradores
        i += 1
        time.sleep(1)  



thread = Thread(target=update_registers, args=(context,))
thread.daemon = True
thread.start()

# Iniciar servidor MODBUS TCP na porta PORT
print(f"Servidor MODBUS TCP rodando em 0.0.0.0:{PORT}")
StartTcpServer(context, address=("0.0.0.0", PORT))
