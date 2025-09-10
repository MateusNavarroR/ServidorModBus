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

PORT = 1502

#pip install pymodbus==2.5.3
#sudo lsof -i :1502

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

        amplitude = hr[3] if hr[3] != 0 else 50
        freq = hr[4] if hr[4] != 0 else 0.2
        setpoint = hr[9] if hr[9] != 0 else 100
        Kp = hr[10] if hr[10] != 0 else 1

        hr[0] = i                                # HR0: Rampa
        hr[1] = int(amplitude + amplitude * math.sin(i * freq))  # HR1: Senoide
        hr[2] = random.randint(0, 250)          # HR2: Aleatório
        hr[5] = i % 200                           # HR5: Dente de Serra
        hr[6] = random.choice([0,1])            # HR6: Booleano
        hr[8] = 50 + int(20 * math.sin(i*0.05)) # HR8: Variável de processo
        medida = hr[8]
        erro = setpoint - medida
        hr[7] = medida + int(Kp * erro)         # HR7: Saída do controlador

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
        print("(4) - Configurar senoide (HR3=Amplitude, HR4=Freq)")
        print("(5) - Configurar PID (HR9=Setpoint, HR10=Kp)")

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
            elif opc == '4':
                amp = int(input("Amplitude da senoide: "))
                freq = float(input("Frequência da senoide: "))
                context[slave_id].setValues(3, 3, [amp])
                context[slave_id].setValues(3, 4, [freq])
            elif opc == '5':
                sp = int(input("Setpoint do PID: "))
                kp = float(input("Kp do PID: "))
                context[slave_id].setValues(3, 9, [sp])
                context[slave_id].setValues(3, 10, [kp])
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
