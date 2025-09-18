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
import subprocess
import platform

PORT = int(input("Digite a porta para o servidor MODBUS (padrão 1502): ") or 1502)

#pip install flask
#pip install pymodbus==2.5.3
#pip install pyinstaller
#sudo lsof -i :1502
#pyinstaller --onefile comunicacao.py


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
