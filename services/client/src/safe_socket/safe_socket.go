package safe_socket

import "io"


func SendAll(socket io.Writer, bytes []byte) error {
	totalSent := 0
	for totalSent < len(bytes) {
		sent, err := socket.Write(bytes[totalSent:])
		if err != nil {
			return err
		}
		totalSent += sent
	}
	return nil
}

func RecvAll(socket io.Reader, size int) ([]byte, error) {
	buff := make([]byte, size)
	totalRead := 0
	for totalRead < size {
		read, err := socket.Read(buff[totalRead:])
		if err != nil {
			return nil, err
		}

		if read == 0 {
			return buff, io.EOF
		}
		totalRead += read
	}
	return buff, nil
}
