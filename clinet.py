import socket
import struct
import sys
import os

def recv_exactly(sock, n):
    """Читает ровно n байт из сокета. Блокирует, пока не получит все."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("Сервер закрыл соединение")
        buf += chunk
    return buf

### Функция для отправки одного файла
# Это просто вынесенная логика из старой функции send_rinex.
# Теперь её можно вызывать дважды, если нужно отправить два файла.
def send_single_file(sock, filepath):
    """Отправляет один файл на сервер через уже открытый сокет."""
    if not os.path.isfile(filepath):
        print(f"Ошибка: файл не найден — {filepath}")
        # Возвращаем False, чтобы вызывающий код знал, что ошибка.
        return False

    with open(filepath, 'rb') as f:
        file_data = f.read()
    filename = os.path.basename(filepath)

    # Отправляем имя файла (длина 4 байта + само имя)
    sock.sendall(struct.pack('>I', len(filename)))
    sock.sendall(filename.encode('utf-8'))

    # Отправляем размер файла (8 байт)
    sock.sendall(struct.pack('>Q', len(file_data)))

    # Отправляем содержимое файла
    sock.sendall(file_data)
    # Успешно отправлен
    return True
###

def send_rinex(host: str, port: int, filepath1: str, filepath2: str = None):
    ### Проверка наличия файлов
    # Просто проверяем, существуют ли файлы перед подключением.
    if not os.path.isfile(filepath1):
        print(f"Ошибка: первый файл не найден — {filepath1}")
        return
    if filepath2 and not os.path.isfile(filepath2):
        print(f"Ошибка: второй файл не найден — {filepath2}")
        return
    ###

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))

        ### Отправка первого файла 
        # Вызываем нашу новую функцию для первого файла.
        success = send_single_file(s, filepath1)
        if not success:
            # Если ошибка при отправке первого файла, выходим.
            return
        ###

        ### Отправка второго файла, если он есть 
        # Если filepath2 не None, вызываем функцию снова.
        if filepath2:
            success = send_single_file(s, filepath2)
            if not success:
                # Если ошибка при отправке второго файла, выходим.
                return
        ###

        ### Приём ответа (без изменений) 
        # Код получения и вывода ответа от сервера остаётся как был.
        prefix = recv_exactly(s, 4)
        if prefix == b"OK::":
            size_bytes = recv_exactly(s, 8)
            result_size = struct.unpack('>Q', size_bytes)[0]
            result = recv_exactly(s, result_size)
            print("\n=== Результат обработки ===")
            print(result.decode('utf-8'))
        elif prefix.startswith(b"ERR"):
            rest = s.recv(1024)
            full_error = (prefix + rest).decode('utf-8', errors='replace')
            print("Сервер вернул ошибку:", full_error)
        else:
            print("Некорректный ответ от сервера:", repr(prefix))

if __name__ == '__main__':
    ### Обновление аргументов командной строки 
    # Теперь программа принимает 1 или 2 аргумента.
    if len(sys.argv) not in [2, 3]:
        print("Использование:")
        print("  python client.py <файл1.obs>              # для абсолютного метода")
        print("  python client.py <файл1.obs> <файл2.obs>  # для относительного метода")
        sys.exit(1)

    filepath1 = sys.argv[1]
    # filepath2 будет равен sys.argv[2], если он есть, иначе None.
    filepath2 = sys.argv[2] if len(sys.argv) == 3 else None

    # Передаём оба пути в функцию.
    send_rinex('localhost', 9999, filepath1, filepath2)