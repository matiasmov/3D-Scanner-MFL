import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import serial
import sys

print("========================================")
print("     ESCOLHA O MODO DE VISUALIZAÇÃO     ")
print("========================================")
print("1 - Modo 2D Ultrarrápido (Fluido, sem lag)")
print("2 - Modo 3D da Chapa (Malha volumétrica)")
tipo_visao = input("Digite 1 para 2D ou 2 para 3D: ").strip()

MAX_X_CM = 50.0  
MAX_Y_CM = 20.0  

if tipo_visao == '2':
    print("\n========================================")
    print("    CONFIGURAÇÃO DAS DIMENSÕES DA CHAPA ")
    print("========================================")
    MAX_X_CM = float(input("Comprimento base da chapa em cm (Ex: 50): "))
    MAX_Y_CM = float(input("Largura total da chapa em cm (Ex: 20): "))

print("\n----------------------------------------")
print("        SELECIONE A ESCALA DO SINAL     ")
print("----------------------------------------")
print("1 - Modo Suave (Sinal reduzido)")
print("2 - Modo Real (Fiel 1:1 ao sensor)")
print("3 - Modo Exagerado (Picos ampliados)")
escolha_escala = input("Digite a escala (1, 2 ou 3): ").strip()

if escolha_escala == '1':
    FATOR_ESCALA = 0.5
    modo_nome = "Suave"
elif escolha_escala == '3':
    FATOR_ESCALA = 4.5
    modo_nome = "Exagerado"
else:
    FATOR_ESCALA = 1.0
    modo_nome = "Real"

print(f">> Iniciando [Visão {'2D' if tipo_visao == '1' else '3D'}] em [{modo_nome}]...")

PORTA_SERIAL = '/dev/ttyACM0' 
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=0.01)
except Exception as e:
    print(f"Erro ao abrir a porta serial: {e}")
    sys.exit(1)

plt.ion()

# ==========================================
# EXECUTAR MODO 2D ULTRARRÁPIDO
# ==========================================
if tipo_visao == '1':
    limite_y_2d = 80 if escolha_escala == '1' else (300 if escolha_escala == '3' else 120)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    x_vals, y_vals = [], []
    line, = ax.plot([], [], color='cyan', lw=1.5, label='Desvio Magnético (Sinal)')
    ax.set_ylim(-limite_y_2d, limite_y_2d)
    ax.set_xlim(0, MAX_X_CM)

    limiar_plot = 40.0 * FATOR_ESCALA
    ax.axhline(limiar_plot, color='orange', linestyle='--', label='Limiar (+)')
    ax.axhline(-limiar_plot, color='orange', linestyle='--', label='Limiar (-)')

    ax.set_xlabel('Posição do Odômetro (cm)')
    ax.set_ylabel('Intensidade')
    ax.set_title(f'Scanner MFL - Visão 2D [{modo_nome}]')
    ax.legend(loc='upper right')
    ax.grid(True, color='gray', linestyle=':', alpha=0.5)
    ax.set_facecolor('#1e1e1e')
    fig.patch.set_facecolor('#2d2d2d')
    ax.tick_params(colors='white')

    CM_POR_PULSO = 0.05
    print("Modo 2D rodando. Pressione Ctrl+C para sair.")
    try:
        while True:
            if ser.in_waiting > 0:
                linha = ser.readline().decode('utf-8', errors='ignore').strip()
                if linha:
                    partes = linha.split(',')
                    if len(partes) == 3:
                        try:
                            pulsos_crus = float(partes[0])
                            desvio_real = float(partes[1])
                            trinca = int(partes[2])

                            pos_cm = pulsos_crus * CM_POR_PULSO
                            desvio = desvio_real * FATOR_ESCALA
                            
                            x_vals.append(pos_cm)
                            y_vals.append(desvio)
                            
                            if len(x_vals) > 200:
                                x_vals.pop(0)
                                y_vals.pop(0)

                            line.set_xdata(x_vals)
                            line.set_ydata(y_vals)
                            
                            # Expande o eixo X automaticamente se passar do tamanho base
                            xmax_atual = max(x_vals) if x_vals else MAX_X_CM
                            ax.set_xlim(0, max(MAX_X_CM, xmax_atual + 5))

                            plt.draw()
                            plt.pause(0.0001)

                            if trinca == 1:
                                print(f"[ALERTA] Trinca em X={pos_cm:.1f}cm | Desvio: {desvio_real}")
                        except ValueError:
                            continue
    except KeyboardInterrupt:
        pass

# ==========================================
# EXECUTAR MODO 3D DA CHAPA
# ==========================================
else:
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(projection='3d')
    scan_data = {}
    current_y_cm = 0.0
    ultimo_cm = 0
    CM_POR_PULSO = 0.05

    print(f"Modo 3D rodando (Chapa base {MAX_X_CM}x{MAX_Y_CM}cm). Pressione Ctrl+C para sair.")
    try:
        while True:
            if ser.in_waiting > 0:
                linha = ser.readline().decode('utf-8', errors='ignore').strip()
                if linha:
                    partes = linha.split(',')
                    if len(partes) == 3:
                        try:
                            pulsos_crus = float(partes[0])
                            desvio_real = float(partes[1])
                            trinca = int(partes[2])

                            desvio = desvio_real * FATOR_ESCALA
                            pos_cm = pulsos_crus * CM_POR_PULSO  # Sem trava rígida de clip

                            if pos_cm <= 0.5 and ultimo_cm > (MAX_X_CM * 0.4):
                                current_y_cm = min(current_y_cm + 1.0, MAX_Y_CM)
                            ultimo_cm = pos_cm

                            if current_y_cm not in scan_data:
                                scan_data[current_y_cm] = {}
                            scan_data[current_y_cm][pos_cm] = desvio

                            # Expande dinamicamente o limite do gráfico se passar do tamanho digitado
                            max_x_observado = max([max(yd.keys()) for yd in scan_data.values()]) if scan_data else MAX_X_CM
                            limite_x_plot = max(MAX_X_CM, max_x_observado + 5)

                            ax.clear()
                            ax.set_xlim(0, limite_x_plot)
                            ax.set_ylim(0, MAX_Y_CM)
                            ax.set_zlim(-120 * FATOR_ESCALA, 120 * FATOR_ESCALA)
                            ax.set_xlabel('Comprimento (X em cm)')
                            ax.set_ylabel('Largura (Y em cm)')
                            ax.set_zlabel('Desvio (Z)')
                            ax.set_title(f'Reconstrução 3D - Y={current_y_cm}cm [{modo_nome}]')

                            all_x = sorted(list(set(x for yd in scan_data.values() for x in yd.keys())))
                            all_y = sorted(list(scan_data.keys()))
                            
                            if len(all_y) == 1 and len(all_x) > 1:
                                scan_data[current_y_cm + 1.0] = scan_data[current_y_cm].copy()
                                all_y = sorted(list(scan_data.keys()))

                            if len(all_x) > 1 and len(all_y) > 1:
                                Xg, Yg = np.meshgrid(all_x, all_y)
                                Zg = np.zeros_like(Xg, dtype=float)
                                for i, yv in enumerate(all_y):
                                    for j, xv in enumerate(all_x):
                                        Zg[i, j] = scan_data[yv].get(xv, 0.0)
                                ax.plot_wireframe(Xg, Yg, Zg, color='darkblue', rstride=1, cstride=1, linewidth=0.6)

                            plt.draw()
                            plt.pause(0.001)

                            if trinca == 1:
                                print(f"[ALERTA 3D] Trinca em X={pos_cm:.1f}cm, Y={current_y_cm}cm")
                        except ValueError:
                            continue
    except KeyboardInterrupt:
        pass

print("\n[INFO] Monitoramento encerrado com segurança.")
try:
    ser.close()
except:
    pass
plt.close('all')
sys.exit(0)