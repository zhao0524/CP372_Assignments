# CP372 - Assignment 1: TCP File Transfer & Messaging System

A TCP-based client-server application written in Python implementing the stop-and-wait protocol with user authentication, messaging, and file transfer.

## Requirements

- Python 3.x
- Standard library only (`socket`, `os`, `sys`) — no external packages needed

## Project Structure

```
.
├── client.py
├── server.py
├── users.txt
└── received_files/
```

- `users.txt` — list of valid usernames (one per line)
- `received_files/` — directory where uploaded files are saved

## Setup

Add usernames to `users.txt`, one per line:

```
Alice
Bob
Charlie
```

## Running

**Start the server** in one terminal:

```bash
python server.py
```

**Start the client** in a second terminal:

```bash
python client.py
# or with custom host/port:
python client.py <host> <port>
```

Defaults: host `127.0.0.1`, port `9372`.

## Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| `LOGIN` | `LOGIN <username>` | Authenticate with the server — required before other commands |
| `MSG` | `MSG <message>` | Send a text message to the server |
| `FILE` | `FILE <filepath>` | Upload a file to the server (max 100 MB) |
| `QUIT` | `QUIT` | Disconnect from the server |

## Example Session

```
> LOGIN Alice
[Server] 200 OK Welcome, Alice

> MSG Hello
[Server] 200 OK Message received: Hello

> FILE test.txt
[Server] 200 OK File 'test.txt' received (45 bytes)

> QUIT
[Server] 200 OK Goodbye
```

## Notes

- The server handles one client at a time (single-threaded)
- Filenames are sanitized with `os.path.basename()` to prevent directory traversal
- No encryption — plain TCP connection
- Authentication is username-only (no password)
