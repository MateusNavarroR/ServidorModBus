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



PORT = int(input("Digite a porta para o servidor MODBUS (padrão 1502): ") or 1502)

#pip install pymodbus==2.5.3
#pip install pyinstaller
#sudo lsof -i :1502
#pyinstaller --onefile comunicacao.py


def free_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('', port))
        s.close()
        return
    except OSError:
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

# Criar bloco de memória MODBUS (16 registradores)
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0]*16)
)
context = ModbusServerContext(slaves=store, single=True)

def update_registers(context):
    i = 0
    while True:
        slave_id = 0x00
        hr = context[slave_id].getValues(3, 0, count=16)

        freq = hr[1] if hr[1] != 0 else 60
        hr[1] = freq
        hr[0] = random.choice([0,1]) # HR0: Estado do Motor                                
        hr[2] = int(freq*0.3333)  # HR1: Sensor de Vazão -> Vazão = k*freq + b, sendo b zero temos uma função linear
        hr[3] = int(50 + hr[2] * 0.5 + 5 * math.sin(i*0.1))          # HR3: Pressão que é calculada com o valor da vazão e com uma senoide
        


        # HR0 -> Estado do Motor
        # HR1 -> Frequência
        # HR2 -> Vazão
        # HR3 -> Pressão


        context[slave_id].setValues(3, 0, hr)
        i += 1
        time.sleep(1)

def menu(context):
    while True:
        print("MENU MODBUS")
        print("(1) - Ler registradores")
        print("(2) - Atualizar o valor de frequência")
        print("(3) - Resetar registradores")

        opc = input("Digite uma opção: ")
        try:
            slave_id = 0x00
            hr = context[slave_id].getValues(3, 0, count=16)
            if opc == '1':
                slave_id = 0x00
                hr = context[slave_id].getValues(3, 0, count=4)
                nomes = [
                    "Motor", "Frequência", "Vazão", "Pressão"
                ]
                for i, val in enumerate(hr):
                    print(f"HR{i:02} ({nomes[i]}): {val}")
            elif opc == '2':
                val = int(input(f"Novo valor para HR1: "))
                context[slave_id].setValues(3, 1, [val])
            elif opc == '3':
                context[slave_id].setValues(3, 0, [0]*16)
                print("Registradores resetados.")
            else:
                print("Opção inválida")
        except Exception as e:
            print(f"Erro: {e}")
        print("\n")

# Threads
thread_update = Thread(target=update_registers, args=(context,))
thread_update.daemon = True
thread_update.start()

thread_menu = Thread(target=menu, args=(context,))
thread_menu.daemon = True
thread_menu.start()

# Iniciar servidor MODBUS TCP
print(f"Servidor MODBUS TCP rodando em 0.0.0.0:{PORT}")
StartTcpServer(context, address=("0.0.0.0", PORT))
