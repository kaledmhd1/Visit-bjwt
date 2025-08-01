#!/usr/bin/env python3
import socket
import select
import threading
import os
from datetime import datetime

def decode_varint(data: bytes, pos: int):
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise Exception("Truncated varint")
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos

def format_protobuf(data: bytes, indent: int = 0) -> str:
    pos = 0
    lines = []
    indent_str = "  " * indent
    while pos < len(data):
        field_start = pos
        try:
            tag, pos = decode_varint(data, pos)
        except Exception:
            lines.append(indent_str + f"(raw: \"{data[pos:].hex()}\")")
            break
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:
            try:
                value, pos = decode_varint(data, pos)
                lines.append(indent_str + f"{field_number}: {value}")
            except Exception:
                raw_field = data[field_start:pos].hex()
                lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
        elif wire_type == 1:
            if pos + 8 > len(data):
                raw_field = data[field_start:len(data)].hex()
                lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
                pos = len(data)
            else:
                raw = data[pos:pos+8]
                pos += 8
                value = int.from_bytes(raw, byteorder='little')
                lines.append(indent_str + f"{field_number}: {value}")
        elif wire_type == 5:
            if pos + 4 > len(data):
                raw_field = data[field_start:len(data)].hex()
                lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
                pos = len(data)
            else:
                raw = data[pos:pos+4]
                pos += 4
                value = int.from_bytes(raw, byteorder='little')
                lines.append(indent_str + f"{field_number}: {value}")
        elif wire_type == 2:
            try:
                length, pos = decode_varint(data, pos)
            except Exception:
                raw_field = data[field_start:pos].hex()
                lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
                break
            if pos + length > len(data):
                raw_field = data[field_start:len(data)].hex()
                lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
                pos = len(data)
            else:
                value_bytes = data[pos:pos+length]
                pos += length
                if length == 0:
                    lines.append(indent_str + f"{field_number}: \"\"")
                else:
                    try:
                        value_str = value_bytes.decode("utf-8")
                        if all(c.isprintable() for c in value_str):
                            lines.append(indent_str + f"{field_number}: \"{value_str}\"")
                        else:
                            raise ValueError()
                    except Exception:
                        nested = format_protobuf(value_bytes, indent+1)
                        if nested.strip():
                            lines.append(indent_str + f"{field_number} {{")
                            lines.append(nested)
                            lines.append(indent_str + "}")
                        else:
                            lines.append(indent_str + f"{field_number}: \"{value_bytes.hex()}\"")
        else:
            raw_field = data[field_start:pos].hex()
            lines.append(indent_str + f"{field_number}: \"{raw_field}\"")
    return "\n".join(lines)

def print_protobuf_data(data: bytes):
    parsed_output = format_protobuf(data)
    print("=" * 60)
    print("=== Decoded RAW Protobuf Message ===")
    print(f"Timestamp: {datetime.now()}")
    print("Parsed Output:")
    print(parsed_output)
    print("=" * 60, "\n")

def extract_api_id(nested_data: bytes):
    pos = 0
    while pos < len(nested_data):
        try:
            tag, pos = decode_varint(nested_data, pos)
        except Exception:
            break
        field_number = tag >> 3
        wire_type = tag & 0x07
        if field_number == 1 and wire_type == 0:
            try:
                value, pos = decode_varint(nested_data, pos)
                return value
            except Exception:
                break
        else:
            if wire_type == 0:
                try:
                    _, pos = decode_varint(nested_data, pos)
                except Exception:
                    break
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            elif wire_type == 2:
                try:
                    length, pos = decode_varint(nested_data, pos)
                except Exception:
                    break
                pos += length
            else:
                break
    return None

def save_protos_by_api(data: bytes, output_directory: str = "."):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    pos = 0
    while pos < len(data):
        try:
            tag, pos = decode_varint(data, pos)
        except Exception:
            break
        field_number = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            try:
                _, pos = decode_varint(data, pos)
            except Exception:
                break
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        elif wire_type == 2:
            try:
                length, pos = decode_varint(data, pos)
            except Exception:
                break
            if pos + length > len(data):
                break
            value_bytes = data[pos:pos+length]
            pos += length
            if field_number == 3:
                api_id = extract_api_id(value_bytes)
                if api_id is not None:
                    formatted = format_protobuf(value_bytes)
                    filename = os.path.join(output_directory, f"api_{api_id}.txt")
                    with open(filename, "a", encoding="utf-8") as f:
                        f.write(formatted + "\n\n")
        else:
            break

def save_raw_protobuf_by_port(data: bytes, port: int, base_directory: str = "raw"):
    port_directory = os.path.join(base_directory, str(port))
    if not os.path.exists(port_directory):
        os.makedirs(port_directory)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".bin"
    file_path = os.path.join(port_directory, filename)
    with open(file_path, "wb") as f:
        f.write(data)

SOCKS_VERSION = 5
USERNAME = "bot"
PASSWORD = "bot"

def handle_client(client_socket: socket.socket):
    try:
        version, nmethods = client_socket.recv(2)
        methods = [client_socket.recv(1)[0] for _ in range(nmethods)]
        if 2 not in methods:
            client_socket.close()
            return
        client_socket.sendall(bytes([SOCKS_VERSION, 2]))
        sub_version = client_socket.recv(1)[0]
        uname_len = client_socket.recv(1)[0]
        username_received = client_socket.recv(uname_len).decode("utf-8")
        passwd_len = client_socket.recv(1)[0]
        password_received = client_socket.recv(passwd_len).decode("utf-8")
        if username_received != USERNAME or password_received != PASSWORD:
            client_socket.sendall(bytes([sub_version, 0xFF]))
            client_socket.close()
            return
        client_socket.sendall(bytes([sub_version, 0]))
        ver, cmd, rsv, addr_type = client_socket.recv(4)
        if addr_type == 1:
            target_addr = socket.inet_ntoa(client_socket.recv(4))
        elif addr_type == 3:
            domain_length = client_socket.recv(1)[0]
            target_addr = client_socket.recv(domain_length).decode("utf-8")
        elif addr_type == 4:
            target_addr = socket.inet_ntop(socket.AF_INET6, client_socket.recv(16))
        else:
            client_socket.close()
            return
        target_port = int.from_bytes(client_socket.recv(2), byteorder="big")
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((target_addr, target_port))
        local_addr, local_port = remote_socket.getsockname()
        response = b"".join([
            bytes([SOCKS_VERSION, 0, 0, 1]),
            socket.inet_aton(local_addr),
            local_port.to_bytes(2, byteorder="big")
        ])
        client_socket.sendall(response)
        relay_data(client_socket, remote_socket)
    except Exception as ex:
        print(f"[Error] Exception in handle_client: {ex}")
    finally:
        client_socket.close()

def relay_data(client_socket: socket.socket, remote_socket: socket.socket):
    try:
        while True:
            ready_sockets, _, _ = select.select([client_socket, remote_socket], [], [])
            if client_socket in ready_sockets:
                data_from_client = client_socket.recv(4096)
                if not data_from_client:
                    break
                remote_socket.sendall(data_from_client)
            if remote_socket in ready_sockets:
                data_from_server = remote_socket.recv(4096)
                if not data_from_server:
                    break
                print_protobuf_data(data_from_server)
                save_protos_by_api(data_from_server, output_directory="bytrick")
                # Save raw protobuf in a folder named after the remote port.
                remote_port = remote_socket.getpeername()[1]
                save_raw_protobuf_by_port(data_from_server, remote_port, base_directory="raw")
                client_socket.sendall(data_from_server)
    except Exception as ex:
        print(f"[Error] Exception in relay_data: {ex}")
    finally:
        remote_socket.close()
        client_socket.close()

def start_proxy(listen_addr: str, listen_port: int):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((listen_addr, listen_port))
    server_socket.listen()
    print(f"[Proxy] Proxy started on {listen_addr}:{listen_port}")
    try:
        while True:
            client_conn, client_addr = server_socket.accept()
            print(f"[Proxy] Connection received from {client_addr}")
            client_thread = threading.Thread(target=handle_client, args=(client_conn,))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("[Proxy] Shutting down proxy...")
    except Exception as ex:
        print(f"[Error] Exception in start_proxy: {ex}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_proxy("127.0.0.1", 1080)
