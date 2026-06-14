import socket
import os

HOST = "0.0.0.0"
PORT = 9372
USERS_FILE = "users.txt"
RECV_DIR = "received_files"
BUFFER_SIZE = 4096


def load_users(path):
    if not os.path.exists(path):
        print(f"[WARN] Users file '{path}' not found. No logins will be allowed.")
        return set()
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}


def recv_line(conn):
    """Read bytes from conn until '\n', return decoded string (no trailing newline)."""
    data = b""
    while True:
        chunk = conn.recv(1)
        if not chunk:
            raise ConnectionError("Client disconnected mid-message.")
        if chunk == b"\n":
            return data.decode("utf-8")
        data += chunk


def recv_bytes(conn, n):
    """Read exactly n raw bytes from conn."""
    data = b""
    while len(data) < n:
        chunk = conn.recv(min(BUFFER_SIZE, n - len(data)))
        if not chunk:
            raise ConnectionError("Client disconnected during file transfer.")
        data += chunk
    return data


def send(conn, msg):
    """Send a UTF-8 line with a trailing newline."""
    conn.sendall((msg + "\n").encode("utf-8"))


def handle_client(conn, addr, valid_users):
    print(f"[+] Client connected: {addr}")
    logged_in_user = None

    try:
        while True:
            try:
                line = recv_line(conn)
            except ConnectionError:
                break

            if not line:
                send(conn, "400 ERROR Empty command")
                continue

            parts = line.split(" ", 1)
            command = parts[0].upper()
            argument = parts[1] if len(parts) > 1 else ""

            # LOGIN
            if command == "LOGIN":
                username = argument.strip()
                if not username:
                    send(conn, "400 ERROR Missing username")
                elif username not in valid_users:
                    print(f"[AUTH] Failed login attempt: '{username}'")
                    send(conn, "401 UNAUTHORIZED Invalid username")
                elif logged_in_user is not None:
                    send(conn, "400 ERROR Already logged in as " + logged_in_user)
                else:
                    logged_in_user = username
                    print(f"[AUTH] User logged in: {logged_in_user}")
                    send(conn, f"200 OK Welcome, {logged_in_user}")

            # MSG
            elif command == "MSG":
                if logged_in_user is None:
                    send(conn, "403 FORBIDDEN Please login first")
                    continue
                text = argument
                if not text:
                    send(conn, "400 ERROR Empty message")
                else:
                    print(f"[MSG] {logged_in_user}: {text}")
                    send(conn, f"200 OK Message received: {text}")

            # FILE
            elif command == "FILE":
                if logged_in_user is None:
                    send(conn, "403 FORBIDDEN Please login first")
                    continue
                filename = argument.strip()
                if not filename:
                    send(conn, "400 ERROR Missing filename")
                    continue

                # Next line: file size
                try:
                    size_line = recv_line(conn)
                    file_size = int(size_line.strip())
                except (ConnectionError, ValueError):
                    send(conn, "400 ERROR Invalid file size")
                    continue

                if file_size < 0 or file_size > 100 * 1024 * 1024:  # 100 MB cap
                    send(conn, "400 ERROR File size out of acceptable range")
                    continue

                # Receive raw file bytes
                try:
                    file_data = recv_bytes(conn, file_size)
                except ConnectionError as e:
                    send(conn, f"400 ERROR {e}")
                    continue

                os.makedirs(RECV_DIR, exist_ok=True)
                safe_name = os.path.basename(filename)
                save_path = os.path.join(RECV_DIR, safe_name)
                with open(save_path, "wb") as f:
                    f.write(file_data)

                print(f"[FILE] Received '{safe_name}' ({file_size} bytes) from {logged_in_user}")
                send(conn, f"200 OK File '{safe_name}' received ({file_size} bytes)")

            # QUIT
            elif command == "QUIT":
                print(f"[-] Client disconnected gracefully: {addr} (user: {logged_in_user})")
                send(conn, "200 OK Goodbye")
                break

            # Unknown
            else:
                send(conn, f"400 ERROR Unknown command '{command}'")

    except Exception as e:
        print(f"[ERROR] Unexpected error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[~] Connection closed: {addr}")


def main():
    valid_users = load_users(USERS_FILE)
    print(f"[*] Loaded {len(valid_users)} user(s) from '{USERS_FILE}'")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)
        print(f"[*] Server listening on {HOST}:{PORT}")

        while True:
            print("[*] Waiting for a client connection...")
            try:
                conn, addr = server_sock.accept()
            except KeyboardInterrupt:
                print("\n[*] Server shutting down.")
                break
            handle_client(conn, addr, valid_users)


if __name__ == "__main__":
    main()