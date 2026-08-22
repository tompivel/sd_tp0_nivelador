import sys
import textwrap


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_compose.py <number_of_clients>")
        sys.exit(1)

    try:
        num_clients = int(sys.argv[1])
    except ValueError:
        print("Error: The number of clients must be an integer.")
        sys.exit(1)

    if num_clients <= 0:
        print("Error: The number of clients must be greater than 0.")
        sys.exit(1)

    compose_content = textwrap.dedent("""\
        services:
          server:
            build:
              context: ./services/server
              dockerfile: Dockerfile
            container_name: server
            environment:
              - PYTHONUNBUFFERED=1
              - SERVER_HOST=server
              - SERVER_PORT=5678
    """)

    client_template = textwrap.indent(
        textwrap.dedent("""\
        client_{id}:
          build:
            context: ./services/client
            dockerfile: Dockerfile
          container_name: client_{id}
          depends_on:
            - server
          environment:
            - AGENCY_ID={id}
            - SERVER_HOST=server
            - SERVER_PORT=5678
    """),
        "  ",
    )

    for i in range(num_clients):
        compose_content += client_template.format(id=i)

    with open("docker-compose.yaml", "w") as f:
        f.write(compose_content)

    print(f"Successfully generated docker-compose.yaml with {num_clients} clients.")


if __name__ == "__main__":
    main()
