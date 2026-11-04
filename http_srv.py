import argparse
import socket
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

HOST = "127.0.0.1"
PORT = 8000
END_OF_REQUEST = b"\r\n\r\n"

STATUS_PHRASES = {
    status.value: status.phrase
    for status in HTTPStatus
}


def get_status(query):
    params = parse_qs(query, keep_blank_values=True)

    if "status" not in params:
        return 200, "OK"

    raw_status = params["status"][0]

    if not raw_status.isdigit():
        return 200, "OK"

    code = int(raw_status)

    if code not in STATUS_PHRASES:
        return 200, "OK"

    return code, STATUS_PHRASES[code]


def parse_request(data):
    head = data.partition(END_OF_REQUEST)[0]
    lines = head.decode().split("\r\n")

    request_line = lines[0]
    request_parts = request_line.split(" ")
    method = request_parts[0]
    target = request_parts[1]

    query = urlsplit(target).query

    headers = []
    for line in lines[1:]:
        header_parts = line.partition(":")
        name = header_parts[0].strip()
        value = header_parts[2].strip()
        headers.append((name, value))

    return method, headers, query


def build_response(method, source, headers, query):
    code, phrase = get_status(query)

    body_lines = [
        f"Request Method: {method}",
        f"Request Source: {source}",
        f"Response Status: {code} {phrase}",
    ]

    for name, value in headers:
        body_lines.append(f"{name}: {value}")

    body = ("\r\n".join(body_lines) + "\r\n").encode()
    head = (
        f"HTTP/1.1 {code} {phrase}\r\n"
        f"Content-Type: text/plain; charset=UTF-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode()
    return head + body


def handle_client(connection):
    with connection:
        request = b""

        while END_OF_REQUEST not in request:
            data = connection.recv(1024)

            if not data:
                break

            request += data

        if not request:
            return

        method, headers, query = parse_request(request)
        source = connection.getpeername()

        connection.sendall(build_response(method, source, headers, query))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    with socket.socket() as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((args.host, args.port))
        server_socket.listen()

        print(f"Serving on http://{args.host}:{args.port}")

        while True:
            connection, _ = server_socket.accept()
            handle_client(connection)


if __name__ == "__main__":
    main()