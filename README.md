# 🎵 MusiCat 🐱

Um bot de música completo para Discord feito em Python, com suporte a filas, controle de reprodução, loop, volume e muito mais — tudo de forma simples e intuitiva.

---

## 📌 Funcionalidades

* ▶️ Reprodução de músicas via nome ou URL (YouTube)
* 📜 Sistema de fila por servidor
* ⏯️ Controles completos (pausar, pular, parar)
* 🔁 Loop da música atual
* 🔊 Controle de volume
* 🧠 Estado independente para cada servidor (guild)
* 📊 Embeds bonitos com informações da música
* 💤 Desconexão automática por inatividade
* ☁️ Hospedado no Railway (24h online)

---

## ⚙️ Como funciona

O bot utiliza:

* **discord.py** → para interagir com o Discord
* **yt-dlp** → para buscar e extrair áudio de vídeos
* **FFmpeg** → para reprodução de áudio
* **asyncio** → para execução assíncrona

### 🔄 Fluxo básico:

1. Usuário digita `!play`
2. O bot:

   * Entra no canal de voz
   * Busca a música (nome ou link)
   * Adiciona na fila
3. Se nada estiver tocando:

   * Começa a reprodução automaticamente
4. Quando a música termina:

   * A próxima da fila toca automaticamente

Cada servidor tem sua própria fila e configurações.

---

## 📁 Estrutura do projeto

```id="6rq4y8"
projeto/
│
├── bot.py
├── .env                # Token do bot
└── discord.log         # Logs do bot
```

---

## 🤖 Adicionar o bot ao seu servidor

Clique no link abaixo para adicionar o bot diretamente ao seu Discord:

👉 https://discord.com/oauth2/authorize?client_id=1481000513934725171&permissions=2252126503169088&integration_type=0&scope=bot

---

## 🎮 Comandos disponíveis

### ▶️ Reprodução

* `!play <nome ou URL>` (ou `!p`)

  * Toca uma música ou adiciona à fila
  * Aceita nome ou link do YouTube

---

### ⏯️ Controle de música

* `!pause` → Pausa a música
* `!resume` → Retoma a música
* `!skip` → Pula a música atual
* `!stop` → Para tudo e desconecta o bot

---

### 📜 Fila

* `!queue` (ou `!q`) → Mostra a fila
* `!remove <número>` → Remove música da fila

---

### ℹ️ Informações

* `!nowplaying` (ou `!np`) → Mostra a música atual
* `!help_bot` → Lista todos os comandos

---

### ⚙️ Configurações

* `!loop` → Ativa/desativa loop da música atual
* `!volume <0-100>` → Ajusta o volume

---

## 📊 Exemplo de uso

```id="p6s2k1"
!play Gorillaz Fell Good Inc.
!play https://youtube.com/...
!queue
!skip
```

---

## 🧠 Sistema de fila

* Cada servidor tem sua própria fila
* A fila é gerenciada com `deque` (rápida e eficiente)
* O bot mantém:

  * Música atual
  * Lista de próximas músicas
  * Estado de loop

---

## 💤 Sistema de inatividade

* Se o bot ficar **sozinho no canal de voz**:

  * Aguarda 60 segundos
  * Sai automaticamente
  * Limpa a fila
  * Envia mensagem de aviso

---

## ⚠️ Observações importantes

* O bot fica **online 24 horas por dia** utilizando hospedagem no Railway
* Precisa de permissões para:

  * Conectar em canais de voz
  * Falar
  * Enviar mensagens
* Playlists não são suportadas (apenas uma música por vez)

---

## 🔧 Possíveis melhorias

* Suporte a playlists
* Sistema de votos para skip
* Slash commands (/play)
* Dashboard web
* Cache de músicas

---
