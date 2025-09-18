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

        amplitude = hr[3] if hr[3] != 0 else 50
        freq = hr[4] if hr[4] != 0 else 0.2
        setpoint = hr[9] if hr[9] != 0 else 100
        Kp = hr[10] if hr[10] != 0 else 1

        hr[0] = i                                # HR0: Rampa
        hr[1] = int(amplitude + amplitude * math.sin(i * freq))  # HR1: Senoide
        hr[2] = random.randint(0, 50)          # HR2: Aleatório
        hr[5] = i % 200                           # HR5: Dente de Serra
        hr[6] = random.choice([0,1])            # HR6: Booleano
        
        
        hr[8] = 50 + int(20 * math.sin(i*0.05)) # HR8: Variável de processo
        medida = hr[8]
        erro = setpoint - medida
        hr[7] = max(0,int(Kp * erro))         # HR7: Saída do controlador

        # HR11-HR15 permanecem livres

        context[slave_id].setValues(3, 0, hr)
        i += 1
        time.sleep(1)

def menu(context):
    while True:
        print("MENU MODBUS")
        print("(1) - Ler registradores")
        print("(2) - Modificar um registrador")
        print("(3) - Resetar registradores")

        opc = input("Digite uma opção: ")
        try:
            slave_id = 0x00
            hr = context[slave_id].getValues(3, 0, count=16)
            if opc == '1':
                slave_id = 0x00
                hr = context[slave_id].getValues(3, 0, count=16)
                nomes = [
                    "Rampa", "Senoide", "Aleatório", "Amplitude Senoide", "Freq. Senoide",
                    "Dente de Serra", "Booleano", "Saída PID", "Variável Processo",
                    "Setpoint PID", "Kp", "LIVRE", "LIVRE", "LIVRE", "LIVRE", "LIVRE"
                ]
                if len(hr) < 16:
                    hr += [0] * (16 - len(hr))

                for i, val in enumerate(hr):
                    print(f"HR{i:02} ({nomes[i]}): {val}")
            elif opc == '2':
                reg = int(input("Escolha o registrador (0-15): "))
                val = int(input(f"Novo valor para HR{reg}: "))
                context[slave_id].setValues(3, reg, [val])
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
