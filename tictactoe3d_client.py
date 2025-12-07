import socketio
from tkinter import *
from tkinter import messagebox, simpledialog # <--- AGREGADO simpledialog
import platform

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Creamos una ventanita oculta temporal para pedir la IP
root_temp = Tk()
root_temp.withdraw() # Ocultar la ventana principal temporal

# Preguntar al usuario la IP
# Si lo dejas vacío o pones "nube", usa la de Render.
# Si pones "localhost", es tu propia máquina.
# Si pones una IP (ej: 192.168.1.5), se conecta a esa red WiFi.
ip_input = simpledialog.askstring(
    "Conexión", 
    "Ingresa la IP del Servidor:\n(Ej: 192.168.1.X o 'localhost')\nDeja vacío para jugar Online (Render)",
    parent=root_temp
)

root_temp.destroy() # Destruir la ventana temporal

if not ip_input or ip_input.strip() == "":
    # MODO 100% (WAN / INTERNET)
    SERVER_URL = "https://servidor-tictactoe3d.onrender.com"
    print("Modo: ONLINE (Render)")
else:
    # MODO 75% (WIFI / LAN)
    # Asumimos que es local, usamos http y puerto 3000
    # Si el usuario escribe 'localhost', queda http://localhost:3000
    SERVER_URL = f"http://{ip_input}:3000"
    print(f"Modo: LOCAL/WIFI ({SERVER_URL})")

sio = socketio.Client()
jugadas = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
botones = []

# Variables globales de interfaz
tablero = None
texto_label = None

# Variables para las coordenadas verdes
label_x = None
label_y = None
label_z = None

myPlayer = None        
currentPlayer = 1
gameOver = False

# Detectar sistema operativo para el color de fondo por defecto de los botones
DEFAULT_BG = "SystemButtonFace" if platform.system() == "Windows" else "lightgray"

def botonClick(i):
    if gameOver:
        return
    if myPlayer is None:
        return
    if myPlayer != currentPlayer:
        messagebox.showinfo("Turno", "No es tu turno")
        return

    z = i // 16
    y = (i % 16) // 4
    x = i % 4

    sio.emit("play", {"x": x, "y": y, "z": z})

def actualizar_tablero():
    for z in range(4):
        for y in range(4):
            for x in range(4):
                index = z*16 + y*4 + x
                val = jugadas[z][y][x]
                
                # Restaurar color de fondo si no es parte de la victoria (se maneja en reset)
                # Nota: El color verde de victoria se pone en "fin", aquí solo ponemos texto
                
                if val == -1:
                    botones[index].config(text="X", fg="blue")
                elif val == 1:
                    botones[index].config(text="O", fg="red")
                else:
                    botones[index].config(text="", fg="black")

    # Actualizar texto de turno
    if myPlayer == currentPlayer:
        texto_label.config(text=f"Tu turno (Jugador {myPlayer})", fg="blue")
    else:
        texto_label.config(text=f"Turno del Jugador {currentPlayer}", fg="black")

def limpiar_colores():
    """Restaura el color de fondo de todos los botones."""
    for btn in botones:
        btn.config(bg=DEFAULT_BG)

#   ---- SOCKETS ----

@sio.event
def connect():
    print("Conectado al servidor")

@sio.on("boardState")
def board_state(data):
    global jugadas, currentPlayer, gameOver, myPlayer
    jugadas = data["board"]
    currentPlayer = data["currentPlayer"]
    gameOver = data["gameOver"]
    
    if "yourPlayer" in data:
        myPlayer = data["yourPlayer"]
        if myPlayer == 0:
            tablero.title("TicTacToe 3D - Espectador")
        else:
            tablero.title(f"TicTacToe 3D - Jugador {myPlayer}")
    
    # Limpiamos colores (por si venimos de un Reset tras victoria)
    limpiar_colores()
    tablero.after(0, actualizar_tablero)

@sio.on("update")
def update(data):
    global jugadas, currentPlayer, gameOver
    
    jugadas = data["board"]
    currentPlayer = data["currentPlayer"]
    gameOver = data["gameOver"]

    # Actualizar coordenadas verdes (último movimiento)
    if "lastMove" in data:
        lx = data["lastMove"]["x"]
        ly = data["lastMove"]["y"]
        lz = data["lastMove"]["z"]
        
        if label_x and label_y and label_z:
            label_x.config(text=f"X={lx}")
            label_y.config(text=f"Y={ly}")
            label_z.config(text=f"Z={lz}")

    tablero.after(0, actualizar_tablero)

@sio.on("gameOver")
def fin(data):
    global gameOver
    gameOver = True
    ganador = data.get("winner", 0)
    linea_ganadora = data.get("winLine", [])

    # 1. Resaltar la línea ganadora en VERDE
    for (gx, gy, gz) in linea_ganadora:
        idx = gz*16 + gy*4 + gx
        botones[idx].config(bg="#39FF14")  # Verde neón

    def show():
        messagebox.showinfo("FIN", f"¡Jugador {ganador} ganó!")

        # 2. Lógica de reinicio solo para Jugador 1
        if myPlayer == 1:
            r = messagebox.askquestion("Reiniciar", "¿Quieres reiniciar la partida para ambos?")
            if r == "yes":
                # Limpiamos etiquetas locales
                label_x.config(text="X=")
                label_y.config(text="Y=")
                label_z.config(text="Z=")
                sio.emit("reset")
            else:
                tablero.destroy()
        else:
            if myPlayer == 0:
                msg = "Esperando que el anfitrión reinicie..."
            else:
                msg = "Esperando a que el Jugador 1 reinicie la partida..."
            
            messagebox.showinfo("Juego Terminado", msg)

    tablero.after(100, show)

@sio.on("opponentLeft")
def opponent_left(data):
    """Manejo de desconexión del rival."""
    messagebox.showwarning("Desconexión", "El oponente se ha desconectado. El juego se reiniciará.")
    label_x.config(text="X=")
    label_y.config(text="Y=")
    label_z.config(text="Z=")
    # No necesitamos emitir reset aquí, el servidor ya reseteó el estado,
    # pero podríamos limpiar el tablero localmente si hiciera falta.

#   ---- INTERFAZ ----

def inicio():
    global tablero, texto_label, botones
    global label_x, label_y, label_z 

    tablero = Tk()
    tablero.geometry("1200x600") # Ventana más ancha para los paneles
    tablero.title("TicTacToe 3D")

    # Contenedor principal para los 4 tableros
    main_frame = Frame(tablero)
    main_frame.pack(pady=20)

    # Crear botones organizados en 4 paneles (LabelFrames)
    # Z=0, Z=1, Z=2, Z=3
    for z in range(4):
        # Marco para cada nivel
        frame_nivel = LabelFrame(main_frame, text=f"Nivel Z={z}", font=("Arial", 12, "bold"), padx=5, pady=5)
        frame_nivel.grid(row=0, column=z, padx=10)
        
        for y in range(4):
            for x in range(4):
                # Calculamos el índice lineal (0 a 63)
                index = z*16 + y*4 + x
                
                btn = Button(frame_nivel, width=5, height=2, font=("Helvetica", 12),
                             command=lambda i=index: botonClick(i))
                btn.grid(row=y, column=x, padx=1, pady=1)
                botones.append(btn)

    # Panel inferior para controles e info
    info_frame = Frame(tablero)
    info_frame.pack(pady=20, fill=X)

    # Coordenadas (Izquierda)
    coords_frame = Frame(info_frame)
    coords_frame.pack(side=LEFT, padx=50)
    
    label_x = Label(coords_frame, text="X=", font=("Arial", 16, "bold"), fg="green")
    label_x.pack(side=LEFT, padx=10)
    label_y = Label(coords_frame, text="Y=", font=("Arial", 16, "bold"), fg="green")
    label_y.pack(side=LEFT, padx=10)
    label_z = Label(coords_frame, text="Z=", font=("Arial", 16, "bold"), fg="green")
    label_z.pack(side=LEFT, padx=10)

    # Texto de estado (Centro)
    texto_label = Label(info_frame, text="Conectando...", font=("Arial", 18))
    texto_label.pack(side=LEFT, expand=True)

    # Botón Reiniciar (Derecha)
    def manualReset():
        if myPlayer != 1:
            messagebox.showwarning("Acceso", "Solo el Jugador 1 puede reiniciar.")
            return
            
        r = messagebox.askquestion("RESET","¿Forzar reinicio de partida?")
        if r == "yes":
            label_x.config(text="X=")
            label_y.config(text="Y=")
            label_z.config(text="Z=")
            sio.emit("reset")

    btn_reset = Button(info_frame, text="Reiniciar Partida", font=("Arial", 12), command=manualReset, bg="#ffcccc")
    btn_reset.pack(side=RIGHT, padx=50)

    tablero.mainloop()

if __name__ == "__main__":
    try:
        sio.connect(SERVER_URL)
        inicio()
    except Exception as e:
        print(f"Error de conexión: {e}")
        # Si falla, abrimos una ventana vacía para mostrar el error visualmente (opcional)
        root = Tk()
        root.withdraw()
        messagebox.showerror("Error", f"No se pudo conectar al servidor:\n{SERVER_URL}\n\n{e}")