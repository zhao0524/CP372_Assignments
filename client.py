import socket
import os
import sys

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9372
BUFFER_SIZE = 4096


def recv_line(sock):
    """Read one '\n'-terminated line from the socket."""
    data = b""
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("Server closed the connection.")
        if byte == b"\n":
            return data.decode("utf-8")
        data += byte


def send_line(sock, text):
    sock.sendall((text + "\n").encode("utf-8"))


def send_file(sock, filepath):
    """Send FILE command followed by filename, size, and raw bytes."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        print(f"[DEBUG] Python is looking in: {os.getcwd()}")
        return False

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)

    # Send header lines
    send_line(sock, f"FILE {filename}")
    send_line(sock, str(file_size))

    # Send raw bytes in chunks
    sent = 0
    with open(filepath, "rb") as f:
        while sent < file_size:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)

    print(f"[*] Sent '{filename}' ({file_size} bytes)")
    return True


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"[+] Connected to {host}:{port}")
        print("Commands: LOGIN <user>  |  MSG <text>  |  FILE <path>  |  QUIT\n")
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to {host}:{port}. Is the server running?")
        sys.exit(1)

    try:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[*] Interrupted. Sending QUIT...")
                send_line(sock, "QUIT")
                try:
                    print(recv_line(sock))
                except Exception:
                    pass
                break

            if not user_input:
                continue

            parts = user_input.split(" ", 1)
            command = parts[0].upper()
            argument = parts[1] if len(parts) > 1 else ""

            if command == "FILE":
                filepath = argument.strip()
                if not send_file(sock, filepath):
                    continue  # error already printed, no server round-trip
            elif command in ("LOGIN", "MSG", "QUIT"):
                send_line(sock, user_input)
            else:
                # forward any unknown command (server will reject it)
                send_line(sock, user_input)

            # Wait for server response (stop-and-wait)
            try:
                response = recv_line(sock)
                print(f"[Server] {response}")
            except ConnectionError as e:
                print(f"[ERROR] {e}")
                break

            if command == "QUIT":
                break

    finally:
        sock.close()
        print("[*] Disconnected.")


if __name__ == "__main__":
    main()