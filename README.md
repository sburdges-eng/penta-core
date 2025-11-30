# penta-core

A simple HTTP server application.

## Team Documentation

Check out the [team documentation](docs/README.md) to get up to speed on:

- [Swift SDKs Development](docs/swift-sdks.md)
- [C++ Programming](docs/cpp-programming.md)
- [Rust DAW Backend](docs/rust-daw-backend.md) ⭐ NEW - 150 things to know about building a Rust DAW
- [DAW Programs](docs/daw-programs.md)
- [Audio Software/Hardware Interfaces](docs/audio-interfaces.md)
- [Media Production](docs/media-production.md)

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python server.py
   ```

## Configuration

Configure the server using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| HOST | 0.0.0.0 | Server host address |
| PORT | 8000 | Server port |

## Endpoints

- `GET /health` - Health check endpoint (returns `{"status": "healthy"}`)

## License

MIT License - see [LICENSE](LICENSE) for details.