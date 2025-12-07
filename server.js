// server.js
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

// *************************************************************************
// ESTA ES LA LÍNEA CLAVE PARA LA NUBE (RENDER)
// Usa el puerto que le da el entorno (process.env.PORT) o por defecto usa 3000
const PORT = process.env.PORT || 3000;
// *************************************************************************

// ----------------------
// Estado del juego
// ----------------------
let board;
let currentPlayer; // 1 o 2
let gameOver = false;
let players = {};  // socket.id -> playerNumber

// Inicializar tablero
function resetGame() {
  board = Array.from({ length: 4 }, () =>
    Array.from({ length: 4 }, () =>
      Array(4).fill(0)
    )
  );
  currentPlayer = 1;
  gameOver = false;
  console.log("Juego reiniciado.");
}
resetGame();

function generateLines() {
  const lines = [];
  const directions = [
    [1,0,0], [0,1,0], [0,0,1],
    [1,1,0], [1,-1,0],
    [1,0,1], [1,0,-1],
    [0,1,1], [0,1,-1],
    [1,1,1], [1,1,-1],
    [1,-1,1], [1,-1,-1]
  ];

  for (let x = 0; x < 4; x++) {
    for (let y = 0; y < 4; y++) {
      for (let z = 0; z < 4; z++) {

        for (let [dx, dy, dz] of directions) {
          const line = [];

          for (let i = 0; i < 4; i++) {
            const nx = x + dx*i;
            const ny = y + dy*i;
            const nz = z + dz*i;

            if (
              nx < 0 || nx >= 4 ||
              ny < 0 || ny >= 4 ||
              nz < 0 || nz >= 4
            ) break;

            line.push([nx, ny, nz]);
          }

          if (line.length === 4) {
            lines.push(line);
          }
        }

      }
    }
  }
  return lines;
}

const winningLines = generateLines();

// ----------------------
// Comprobar ganador (Devuelve la línea ganadora o null)
// ----------------------
function getWinningLine(player) {
  const val = player === 1 ? -1 : 1;
  // Buscamos si alguna línea cumple la condición
  const line = winningLines.find(line =>
    line.every(([x, y, z]) => board[z][y][x] === val)
  );
  return line || null;
}

// ----------------------
// Socket.IO
// ----------------------
io.on('connection', (socket) => {
  console.log('Cliente conectado:', socket.id);

  // Asignar jugador
  if (Object.values(players).length < 2) {
    // Si ya existe el 1, asigna el 2, si no el 1.
    const assigned = Object.values(players).includes(1) ? 2 : 1;
    players[socket.id] = assigned;
    console.log(`Socket ${socket.id} asignado como Jugador ${assigned}`);
  } else {
    players[socket.id] = 0; // espectador
    console.log(`Socket ${socket.id} es espectador`);
  }

  // Enviar estado inicial
  socket.emit('boardState', {
    board,
    currentPlayer,
    gameOver,
    yourPlayer: players[socket.id]
  });

  // ------------------
  // JUGAR
  // ------------------
  socket.on('play', ({ x, y, z }) => {
    if (gameOver) return;

    const player = players[socket.id];
    // Validar que sea jugador activo y su turno
    if (player !== 1 && player !== 2) return;
    if (player !== currentPlayer) return;

    if (board[z][y][x] !== 0) return;

    // Marcar tablero
    board[z][y][x] = player === 1 ? -1 : 1;

    // Verificar ganador
    const winLine = getWinningLine(player);
    
    if (winLine) {
      gameOver = true;
      // Enviamos el update final
      io.emit('update', {
        board,
        currentPlayer,
        gameOver,
        lastMove: {x,y,z} 
      });
      // Enviamos evento de fin con la línea ganadora
      io.emit('gameOver', { winner: player, winLine: winLine });
      return;
    }

    // Cambiar turno
    currentPlayer = currentPlayer === 1 ? 2 : 1;

    io.emit('update', {
      board,
      currentPlayer,
      gameOver,
      lastMove: { x, y, z }
    });
  });

  // ------------------
  // RESET
  // ------------------
  socket.on('reset', () => {
    console.log(`Reset solicitado por ${socket.id} (Jugador ${players[socket.id]})`);
    resetGame();
    
    // Enviar estado a todos
    io.sockets.sockets.forEach(clientSocket => {
      const playerIdentity = players[clientSocket.id] || 0; 
      clientSocket.emit('boardState', {
        board,
        currentPlayer,
        gameOver,
        yourPlayer: playerIdentity
      });
    });
  });

  // ------------------
  // DESCONEXIÓN
  // ------------------
  socket.on('disconnect', () => {
    console.log('Cliente desconectado:', socket.id);
    const pNum = players[socket.id];
    delete players[socket.id];

    // Si se fue un jugador activo, avisar para reiniciar
    if (pNum === 1 || pNum === 2) {
      console.log(`Jugador ${pNum} se desconectó. Reiniciando lógica...`);
      resetGame();
      // Avisar a los clientes restantes
      io.emit('opponentLeft', { leaver: pNum });
      
      // Reenviar estado limpio
      io.sockets.sockets.forEach(clientSocket => {
        const playerIdentity = players[clientSocket.id] || 0; 
        clientSocket.emit('boardState', {
          board,
          currentPlayer,
          gameOver,
          yourPlayer: playerIdentity
        });
      });
    }
  });
});

// ----------------------
server.listen(PORT, () => {
  console.log(`Servidor TicTacToe 3D corriendo en puerto ${PORT}`);
});