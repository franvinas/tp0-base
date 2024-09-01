import sys


def generate_client(client_id):
    return f"""client{client_id}:
    container_name: client{client_id}
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID={client_id}
    volumes:
      - ./client/config.yaml:/config.yaml
    networks:
      - testing_net
    depends_on:
      - server"""


def generate_docker_compose(n_clients):
    clients = '\n\n  '.join([generate_client(i + 1) for i in range(n_clients)])
    d = f"""name: tp0
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./server/config.ini:/config.ini
    networks:
      - testing_net

  {clients}

networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24
"""
    return d


def main():
    if len(sys.argv) != 3:
        print('Please provide two arguments.')
        sys.exit(1)

    output_file = sys.argv[1]
    try:
        n_clients = int(sys.argv[2])
    except ValueError:
        print('Invalid number of clients.')
        sys.exit(1)

    docker_compose = generate_docker_compose(n_clients)
    with open(output_file, 'w') as f:
        f.write(docker_compose)


if __name__ == '__main__':
    main()
